"""Metodos expostos para a interface (ui/app.js) via
pywebview.api.<metodo>(...). Cada metodo publico aqui vira uma funcao
chamavel do JavaScript.
"""

import base64
import contextlib
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading

import webview

from config.operations import (
    DEFAULT_DATE_RANGE, GROUP_BY_OPTIONS, OPERATIONS, PASTAS_DO_PERIODO, POR_GRUPO,
    ROTULOS_DO_PERIODO, agrupamento, e_semanal, escala_espanhola,
)
import arquivos_sharepoint
import atualizacao
import backup
import cache_de_telas
import conexao
import coverage_store
import coverage_tela
import diagnostico
import explicacoes
import exportar_imagem
import grupos_store
import grupos_tela
import headcount
import headcount_store
import history_store
import indiretas_store
import indiretas_tela
from indicators import faltas as faltas_reader
from indicators import coverage, grupos, indiretas, limits, periodos, pico, reader, weekly
import indicators_store
import lancamentos
import migracoes
import navegadores
import novidades
import observador_de_pasta
import registro
import resumo_inicio
import settings_store
import versao

log = logging.getLogger("scorecard.api")

# Lancamento digitado vai para a pasta do SharePoint este tanto depois do
# ultimo (varias celulas digitadas seguidas vao numa gravacao so).
ESPERA_PARA_PUBLICAR = 3.0

# Na segunda senha recusada seguida o app para de tentar.
LIMITE_DE_SENHA_RECUSADA = 2
MENSAGEM_SENHA_RECUSADA = (
    "O Summary recusou a senha 2 vezes seguidas. Para não bloquear o seu usuário, "
    "o app parou de tentar: clique em Sair, confira a senha entrando no próprio "
    "Summary e faça login de novo aqui."
)


def _senha_recusada(result):
    """A automacao clicou em Sign In e continuou na tela de login."""
    return "continua sendo a de login" in (result.get("message") or "")


class Api:
    def __init__(self):
        self._window = None
        self._username = None
        self._password = None
        # Guardados aqui (em vez de trafegar caminhos pelo JS) pra tela
        # poder abrir a pasta do ultimo arquivo salvo e o print da
        # ultima falha.
        self._last_folder = None
        self._last_screenshot = None
        # A fila roda na thread do js_api e o pedido de parada chega por
        # outra, entao um Event faz a ponte entre as duas.
        self._cancel_multi = threading.Event()
        # Extracoes em andamento: enquanto houver uma, fechar a janela
        # pede confirmacao (ver _extraindo).
        self._extracoes_em_andamento = 0
        self._trava_extracoes = threading.Lock()
        # O calculo grava os arquivos de dados; a extracao e a leitura da
        # pasta do SharePoint podem calcular ao mesmo tempo (threads do
        # js_api), e duas gravacoes cruzadas perderiam uma delas. Os
        # lancamentos digitados (Headcount, Coverage) e a juncao deles com
        # a pasta passam pela mesma trava.
        self._trava_dados = threading.RLock()
        # Lancamentos: a gravacao na pasta espera um pouco (ver
        # _lancamento_mudou); o que chegou de outras pessoas nessa
        # gravacao fica guardado ate a tela perguntar.
        self._publicacao = None
        self._trava_publicacao = threading.Lock()
        self._lancamentos_de_fora = set()
        self._lancamentos_estado = {"quando": None, "erros": []}
        # Observa a pasta do SharePoint e avisa a tela quando algo muda
        # (observador_de_pasta.py); trocar de pasta troca o observador.
        self._observador = None
        self._trava_observador = threading.Lock()
        # Senha recusada pelo Summary seguidas vezes: na segunda, o app
        # para de tentar ate um novo login (senao a fila tentaria a senha
        # errada em todas as operacoes e bloquearia o usuario).
        self._senhas_recusadas = 0
        # Modo apresentacao (tela cheia). A janela abre maximizada
        # (main.py); os eventos abaixo acompanham se o usuario mudou isso,
        # para a saida da tela cheia voltar do jeito que estava.
        self._tela_cheia = False
        self._maximizada = True
        self._minimizada = False

    def set_window(self, window):
        self._window = window
        try:
            window.events.maximized += self._ficou_maximizada
            window.events.restored += self._ficou_restaurada
            window.events.minimized += self._ficou_minimizada
        except Exception:  # noqa: BLE001 - so perde o "voltar maximizada"
            log.debug("sem eventos de maximizar/restaurar nesta janela")

    def _ficou_maximizada(self):
        if not self._tela_cheia:
            self._maximizada = True

    def _ficou_minimizada(self):
        # Minimizada, a tela pausa as animacoes e as leituras periodicas.
        self._minimizada = True
        self._emit_js("janelaMinimizada", True)

    def _ficou_restaurada(self):
        if self._minimizada:
            # Voltou da barra de tarefas: nao e "deixou de estar maximizada".
            self._minimizada = False
            self._emit_js("janelaMinimizada", False)
            return
        if not self._tela_cheia:
            self._maximizada = False

    def tela_cheia(self, ligar):
        """Modo apresentacao da aba Inicio: a janela ocupa a tela toda,
        sem barra de titulo nem barra de tarefas. Ao sair, volta
        maximizada se estava maximizada."""
        ligar = bool(ligar)
        if self._window is None or ligar == self._tela_cheia:
            return {"success": True}
        estava_maximizada = self._maximizada
        try:
            self._tela_cheia = ligar
            self._window.toggle_fullscreen()
            if not ligar and estava_maximizada:
                self._window.maximize()
        except Exception:  # noqa: BLE001 - a apresentacao segue sem tela cheia
            log.exception("não consegui alternar a tela cheia")
            return {"success": False}
        return {"success": True}

    @contextlib.contextmanager
    def _extraindo(self):
        """Liga o "tem certeza?" ao fechar a janela enquanto uma extracao
        roda: fechar no meio deixa o download pela metade. O pywebview le
        o confirm_close na hora do clique no X, entao basta ligar aqui e
        desligar no fim (a mensagem fica em main.py)."""
        with self._trava_extracoes:
            self._extracoes_em_andamento += 1
            self._confirmar_ao_fechar(True)
        try:
            yield
        finally:
            with self._trava_extracoes:
                self._extracoes_em_andamento -= 1
                self._confirmar_ao_fechar(self._extracoes_em_andamento > 0)

    def _confirmar_ao_fechar(self, ligado):
        if self._window is not None:
            try:
                self._window.confirm_close = ligado
            except Exception:  # noqa: BLE001 - so perde o aviso ao fechar
                log.exception("não consegui ajustar a confirmação ao fechar")

    # ---------------- Login ----------------

    def login(self, username, password):
        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            return {"success": False, "message": "Informe usuário e senha."}
        self._username = username
        self._password = password
        self._senhas_recusadas = 0
        # So em memoria, para o filtro do log trocar por *** se algum
        # dia aparecerem numa mensagem de erro. Nunca vao para arquivo.
        registro.esconder(username, password)
        log.info("login informado na tela")
        return {"success": True}

    def logout(self):
        self._username = None
        self._password = None
        registro.esquecer()
        log.info("logout")
        return {"success": True}

    @staticmethod
    def _servidores():
        """[{"servidor", "operacoes", "ok"}]: cada servidor das operacoes,
        conferido ao mesmo tempo (conexao rapida na porta dele)."""
        from concurrent.futures import ThreadPoolExecutor

        destinos = {}
        for config in OPERATIONS.values():
            alvo = conexao.destino(config.get("login_url"))
            if alvo:
                item = destinos.setdefault(alvo, {"url": config["login_url"], "operacoes": []})
                item["operacoes"].append(config["label"])
        if not destinos:
            return []
        with ThreadPoolExecutor(max_workers=min(8, len(destinos))) as grupo:
            respostas = list(grupo.map(lambda item: conexao.alcancavel(item["url"], tempo_limite=2),
                                       destinos.values()))
        return [{"servidor": alvo[0], "operacoes": item["operacoes"], "ok": ok}
                for (alvo, item), ok in zip(destinos.items(), respostas)]

    def verificar_vpn(self):
        """Para a tela de login: da para chegar nos servidores das
        operacoes?"""
        servidores = self._servidores()
        alcancaveis = sum(s["ok"] for s in servidores)
        if not servidores or alcancaveis == len(servidores):
            estado = "ok"
        else:
            estado = "parcial" if alcancaveis else "fora"
        return {"estado": estado, "alcancaveis": alcancaveis, "total": len(servidores)}

    def is_logged_in(self):
        return bool(self._username and self._password)

    def get_usuario(self):
        """O usuario que entrou, para o selo da barra amarela (so o nome;
        a senha nunca sai daqui)."""
        return {"usuario": self._username} if self.is_logged_in() else {"usuario": None}

    # ---------------- Operacoes ----------------

    def get_operations(self):
        return [{"key": key, "label": cfg["label"]} for key, cfg in OPERATIONS.items()]

    def get_group_by_options(self):
        return GROUP_BY_OPTIONS

    # ---------------- Pasta do SharePoint ----------------

    def get_sharepoint_folder(self):
        return settings_store.get_sharepoint_folder()

    def choose_sharepoint_folder(self):
        if not self._window:
            return {"success": False, "message": "Janela não inicializada."}

        current = settings_store.get_sharepoint_folder()
        result = self._window.create_file_dialog(
            webview.FOLDER_DIALOG,
            directory=current if current and os.path.isdir(current) else "",
        )
        if not result:
            return {"success": False, "message": "Nenhuma pasta selecionada."}

        folder = result[0]
        settings_store.set_sharepoint_folder(folder)
        return {"success": True, "folder": folder}

    def validate_sharepoint_folder(self):
        folder = settings_store.get_sharepoint_folder()
        if not folder:
            return {"valid": False, "message": "Nenhuma pasta configurada ainda."}
        if not os.path.isdir(folder):
            return {"valid": False, "message": f"A pasta configurada não existe mais: {folder}"}
        return {"valid": True, "folder": folder}

    # ---------------- Extracao ----------------

    def _emit_js(self, function_name, payload):
        if not self._window:
            return
        # json.dumps escapa o conteudo com seguranca pra virar um literal
        # valido de JS (aspas, barras, acentos, etc.)
        js_payload = json.dumps(payload)
        self._window.evaluate_js(
            f"window.{function_name} && window.{function_name}({js_payload})"
        )

    def _record_history(self, operation_key, result):
        log.info(
            "extração %s: %s em %ss - %s%s",
            operation_key, self._status_da_extracao(result),
            result.get("duration_seconds"), result.get("message"),
            f" | {result['indicators_message']}" if result.get("indicators_message") else "",
        )
        if result.get("file_path"):
            self._last_folder = os.path.dirname(result["file_path"])
        if result.get("screenshot"):
            self._last_screenshot = result["screenshot"]
        history_store.add_entry({
            "operation": result.get("operation_label", OPERATIONS[operation_key]["label"]),
            "period_label": result.get("period_label"),
            "group_by": result.get("group_by"),
            "agrupamento": result.get("agrupamento"),
            "period_type": result.get("period_type"),
            # Tres estados, nao dois: "warning" e a extracao que salvou o
            # arquivo mas nao gerou indicador. Tratar isso como sucesso
            # foi o que escondeu o problema do .xls ate a primeira
            # extracao real.
            "status": self._status_da_extracao(result),
            "duration_seconds": result.get("duration_seconds"),
            "file_path": result.get("file_path"),
            "message": result.get("message"),
            "indicators_message": result.get("indicators_message"),
        })

    @staticmethod
    def _status_da_extracao(result):
        if not result.get("success"):
            return "error"
        if result.get("indicators_message"):
            return "warning"
        return "success"

    def _calcular_indicadores(self, operation_key, result):
        """Le o arquivo recem-baixado (ou da pasta do SharePoint), calcula
        e grava os indicadores.

        Roda na hora da extracao, e nao na tela: o arquivo pode ser
        substituido por uma extracao seguinte. Os arquivos que outras
        pessoas extrairam chegam pela leitura da pasta
        (arquivos_sharepoint.sincronizar), pelo mesmo caminho.
        """
        if not result.get("success") or not result.get("file_path"):
            return
        with self._trava_dados:
            self._calcular(operation_key, result)

    def _calcular(self, operation_key, result):
        quando = result.get("extraido_em")  # a data do arquivo, se veio da pasta

        try:
            lido = reader.ler(result["file_path"])
        except Exception as exc:  # noqa: BLE001 - arquivo fora do esperado
            log.exception("não deu pra ler %s", result["file_path"])
            result["indicators_message"] = f"Relatório salvo, mas não deu pra calcular: {exc}"
            return

        nivel_detalhe = result.get("group_by")
        de, ate = result.get("date_from"), result.get("date_to")
        meta = {
            "group_by": nivel_detalhe,
            "origem": result.get("origem"),
            "de": de,
            "ate": ate,
        }

        tipo = result.get("tipo") or "week"
        if tipo == "indiretas":
            if not lido["tem_semana"]:
                result["indicators_message"] = (
                    "Relatório salvo, mas veio sem a coluna de semana: "
                    "não deu pra separar as horas indiretas por semana."
                )
                return
            semanas = indiretas.por_semana(lido["linhas"])
            for chave, semana in semanas.items():
                semana["parcial"] = periodos.semana_parcial(chave, de, ate)
            indiretas_store.salvar(operation_key, semanas, de, ate, quando=quando)
            result["indicators"] = len(semanas)
            return

        if tipo in POR_GRUPO:
            self._calcular_por_grupo(operation_key, tipo, lido, result, quando)
            return

        if tipo == "peak":
            chave = result.get("month_key")
            if not chave:
                result["indicators_message"] = (
                    "Relatório salvo, mas não deu pra identificar de que mês "
                    "ele é: informe o período na tela e extraia de novo."
                )
                return
            calculado = pico.calcular(lido["linhas"], chave,
                                      escala_espanhola=escala_espanhola(operation_key))
            if calculado["hora_direta"] is None:
                result["indicators_message"] = (
                    "Relatório salvo, mas nenhum dia válido do mês veio com "
                    "horas: confira se o Group By 1 saiu como Report Date."
                )
                return
            calculado["parcial"] = periodos.mes_parcial(chave, de, ate)
            resultados = {chave: calculado}
            periodo = "peak"
        elif tipo == "month":
            chave = result.get("month_key")
            if not chave:
                result["indicators_message"] = (
                    "Relatório salvo, mas não deu pra identificar de que mês "
                    "ele é: informe o período na tela e extraia de novo."
                )
                return
            resultados = {chave: weekly.totais(lido["linhas"], nivel_detalhe=nivel_detalhe)}
            periodo = "month"
            # Coverage: as horas de cada usuario (primeiro nivel do mensal).
            coverage_store.salvar_extracao(
                operation_key, "month", {chave: coverage.por_usuario(lido["linhas"])}, de, ate, quando=quando)
        else:
            if not lido["tem_semana"]:
                result["indicators_message"] = (
                    "Relatório salvo, mas veio sem a coluna de semana: "
                    "não deu pra separar por semana."
                )
                return
            # Com o Supervisor no meio, quem teve dois supervisores na
            # semana vem em duas linhas; a operacao conta a pessoa uma vez.
            resultados = weekly.por_semana(weekly.juntar_por_pessoa(lido["linhas"]),
                                           nivel_detalhe=nivel_detalhe)
            for chave, totais in resultados.items():
                totais["parcial"] = periodos.semana_parcial(chave, de, ate)
            periodo = "week"
            # Coverage: as horas e o gestor de cada usuario (ultimo nivel do semanal).
            coverage_store.salvar_extracao(
                operation_key, "week", coverage.por_semana_e_usuario(lido["linhas"]), de, ate, quando=quando)

        indicators_store.salvar_extracao(operation_key, periodo, resultados, meta=meta, quando=quando)
        result["indicators"] = len(resultados)

    def _contar_senha(self, result):
        """Conta as senhas recusadas seguidas; uma extracao que passou do
        login zera a conta. Devolve True quando chegou no limite."""
        if _senha_recusada(result):
            self._senhas_recusadas += 1
            log.warning("senha recusada pelo Summary (%d seguida[s])", self._senhas_recusadas)
        elif result.get("success"):
            self._senhas_recusadas = 0
        result["senhas_recusadas"] = self._senhas_recusadas
        return self._senhas_recusadas >= LIMITE_DE_SENHA_RECUSADA

    @staticmethod
    def _registrar_no_sharepoint(operation_key, result):
        """O arquivo que esta pessoa acabou de extrair ja foi calculado: a
        leitura da pasta nao precisa calcular de novo."""
        if not result.get("success"):
            return
        try:
            arquivos_sharepoint.registrar(settings_store.get_sharepoint_folder(), operation_key,
                                          result.get("tipo") or "week", result.get("file_path"))
        except Exception:  # noqa: BLE001 - so evita um calculo repetido
            log.exception("não consegui anotar %s como lido", result.get("file_path"))

    # ---------------- Pasta do SharePoint (compartilhada) ----------------

    def sincronizar_sharepoint(self):
        """Calcula os relatorios da pasta do SharePoint que esta pessoa
        ainda nao tem (extraidos por qualquer um) e junta os lancamentos
        de Headcount e Coverage com os da pasta. A tela chama ao entrar,
        ao trocar de aba e de tempos em tempos."""
        self._observar_a_pasta()
        if self._extracoes_em_andamento:
            return {"atualizados": [], "ignorados": [], "lancamentos": [], "ocupado": True,
                    "observando": self._observando()}
        try:
            resposta = arquivos_sharepoint.sincronizar(
                settings_store.get_sharepoint_folder(), self._calcular_indicadores)
        except Exception as exc:  # noqa: BLE001 - a tela segue com o que ja tem
            log.exception("falha ao ler a pasta do SharePoint")
            return {"atualizados": [], "ignorados": [], "lancamentos": [], "erro": str(exc)}
        for item in resposta.get("atualizados", []):
            item["operacao_rotulo"] = OPERATIONS[item["operacao"]]["label"]
            item["tipo_rotulo"] = ROTULOS_DO_PERIODO[item["tipo"]]
        resposta["lancamentos"] = [
            {"operacao": op, "operacao_rotulo": OPERATIONS[op]["label"]}
            for op in sorted(self._juntar_lancamentos(), key=list(OPERATIONS).index)
        ]
        resposta["observando"] = self._observando()
        return resposta

    def _observar_a_pasta(self):
        """Liga o observador da pasta configurada (uma vez; de novo so se a
        pasta mudar ou ele parar)."""
        base = settings_store.get_sharepoint_folder()
        with self._trava_observador:
            atual = self._observador
            if atual and atual.base == base and atual.ativo:
                return
            if atual:
                atual.parar()
            self._observador = None
            if base and os.path.isdir(base):
                self._observador = observador_de_pasta.Observador(
                    base, lambda: self._emit_js("pastaMudou", {})).iniciar()

    def _observando(self):
        return bool(self._observador and self._observador.ativo)

    # ---------------- Lancamentos compartilhados (Headcount, Coverage) ----------------

    def _juntar_lancamentos(self):
        """Junta os lancamentos desta maquina com os da pasta. Devolve as
        operacoes que mudaram aqui por causa de outra pessoa (inclusive
        numa gravacao feita em segundo plano desde a ultima pergunta)."""
        base = settings_store.get_sharepoint_folder()
        try:
            with self._trava_dados:
                resposta = lancamentos.sincronizar(base)
        except Exception:  # noqa: BLE001 - os lancamentos locais seguem valendo
            log.exception("falha ao juntar os lançamentos com a pasta")
            self._lancamentos_estado = {"quando": datetime.datetime.now(), "erros": ["todas"]}
            resposta = {"mudaram": [], "erros": []}
        else:
            if not resposta.get("sem_pasta"):
                self._lancamentos_estado = {"quando": datetime.datetime.now(), "erros": resposta["erros"]}
        with self._trava_publicacao:
            mudaram = self._lancamentos_de_fora | set(resposta["mudaram"])
            self._lancamentos_de_fora = set()
        return mudaram

    def _lancamento_mudou(self):
        """Depois de um lancamento digitado: leva para a pasta alguns
        segundos depois do ultimo."""
        with self._trava_publicacao:
            if self._publicacao:
                self._publicacao.cancel()
            self._publicacao = threading.Timer(ESPERA_PARA_PUBLICAR, self._publicar_lancamentos)
            self._publicacao.daemon = True
            self._publicacao.start()

    def _publicar_lancamentos(self):
        mudaram = self._juntar_lancamentos()
        if mudaram:
            # A juncao trouxe coisa de outra pessoa: a tela recebe na
            # proxima leitura da pasta.
            with self._trava_publicacao:
                self._lancamentos_de_fora |= mudaram

    def _lancar(self, funcao, *args):
        """Grava um lancamento (sob a mesma trava da juncao com a pasta) e
        agenda a ida dele para a pasta. Erro de validacao sobe sem agendar."""
        with self._trava_dados:
            resultado = funcao(*args)
        self._lancamento_mudou()
        return resultado

    def reler_sharepoint(self):
        """Configuracoes > Ler a pasta do zero: esquece o que ja foi lido e
        calcula todos os relatorios da pasta de novo."""
        if self._extracoes_em_andamento:
            return {"atualizados": [], "ignorados": [], "ocupado": True}
        resposta = arquivos_sharepoint.reler(settings_store.get_sharepoint_folder(), self._calcular_indicadores)
        for item in resposta.get("atualizados", []):
            item["operacao_rotulo"] = OPERATIONS[item["operacao"]]["label"]
            item["tipo_rotulo"] = ROTULOS_DO_PERIODO[item["tipo"]]
        return resposta

    # ---------------- Saude, versao e backup ----------------

    def get_saude(self):
        """Configuracoes > Saude do sistema: VPN por servidor, a pasta do
        SharePoint, a leitura dela, as versoes e o backup."""
        base = settings_store.get_sharepoint_folder()
        pasta = arquivos_sharepoint.estado_da_pasta(base)
        if pasta["mais_novo"]:
            novo = pasta["mais_novo"]
            pasta["mais_novo"] = {
                "texto": novo["quando"].strftime("%d/%m/%Y %H:%M"),
                "operacao": OPERATIONS[novo["operacao"]]["label"],
                "tipo": ROTULOS_DO_PERIODO[novo["tipo"]],
            }
        nao_lidos = [
            {**item, "operacao_rotulo": OPERATIONS.get(item["operacao"], {}).get("label", item["operacao"]),
             "tipo_rotulo": ROTULOS_DO_PERIODO.get(item["tipo"], item["tipo"])}
            for item in arquivos_sharepoint.nao_lidos(base)
        ]
        ultimo_backup = backup.ultimo()
        app = versao.info()
        compartilhados = lancamentos.resumo(base)
        navegador = navegadores.descricao()
        juncao = self._lancamentos_estado
        return {
            "servidores": self._servidores(),
            "pasta": {**pasta, "caminho": base},
            "leitura": {"lidos": arquivos_sharepoint.lidos(base), "nao_lidos": nao_lidos},
            "versao": {**app, **atualizacao.verificar(base, app["versao"])},
            "dados": {"versao": migracoes.versao_dos_dados(), "atual": migracoes.VERSAO_ATUAL},
            "navegador": ({"nome": navegador["nome"], "caminho": navegador["caminho"],
                           "reserva": [n["nome"] for n in navegadores.disponiveis()[1:]]}
                          if navegador else None),
            "lancamentos": {
                "operacoes": compartilhados["operacoes"],
                "gravado": (datetime.datetime.fromisoformat(compartilhados["atualizado_em"]).strftime("%d/%m/%Y %H:%M")
                            if compartilhados["atualizado_em"] else None),
                "juntado": juncao["quando"].strftime("%H:%M") if juncao["quando"] else None,
                "erros": [OPERATIONS.get(op, {}).get("label", op) for op in juncao["erros"]],
            },
            "backup": ({"texto": datetime.datetime.fromisoformat(ultimo_backup["quando"]).strftime("%d/%m/%Y %H:%M"),
                        "arquivos": ultimo_backup["arquivos"]} if ultimo_backup else None),
        }

    def verificar_versao(self):
        """Ha versao mais nova publicada na pasta do SharePoint?"""
        return atualizacao.verificar(settings_store.get_sharepoint_folder(), versao.info()["versao"])

    def abrir_pasta_da_versao(self):
        base = settings_store.get_sharepoint_folder()
        return self._open_path(atualizacao.pasta(base) if base else None, "Pasta da versão nova")

    def get_backups(self):
        return {"backups": [
            {"id": item["id"], "dia": datetime.date.fromisoformat(item["dia"]).strftime("%d/%m/%Y"),
             "hora": datetime.datetime.fromisoformat(item["quando"]).strftime("%H:%M"),
             "arquivos": item["arquivos"], "antes_de_restaurar": item["antes_de_restaurar"]}
            for item in backup.listar()]}

    def fazer_backup(self):
        try:
            caminho = backup.fazer(forcar=True)
        except OSError as exc:
            return {"success": False, "message": f"Não deu para fazer o backup: {exc}"}
        if not caminho:
            return {"success": False, "message": "Ainda não há dados para guardar."}
        return {"success": True, **self.get_backups()}

    def restaurar_backup(self, identificador):
        if self._extracoes_em_andamento:
            return {"success": False, "message": "Espere a extração terminar para restaurar."}
        try:
            with self._trava_dados:
                feito = backup.restaurar(identificador)
                # Backup de antes de uma mudanca no formato dos dados.
                migracoes.migrar()
                cache_de_telas.limpar()
        except (OSError, ValueError) as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, **feito, **self.get_backups()}

    def get_sharepoint_info(self, operacao):
        """O relatorio mais novo de cada tipo da operacao na pasta do
        SharePoint: {"tipos": {tipo: {"quando", "texto", "rotulo",
        "periodo", "nome"}}}. A data e a do nome do arquivo."""
        if operacao != "todas" and operacao not in OPERATIONS:
            return {"tipos": {}}
        base = settings_store.get_sharepoint_folder()
        # "todas" (Coverage e Horas Indiretas): o mais novo de cada tipo
        # entre todas as operacoes.
        mais_novos = {}
        for chave in (OPERATIONS if operacao == "todas" else [operacao]):
            for tipo, info in arquivos_sharepoint.ultimos(base, chave).items():
                if tipo not in mais_novos or info["quando"] > mais_novos[tipo]["quando"]:
                    mais_novos[tipo] = {**info, "operacao": OPERATIONS[chave]["label"]}
        tipos = {}
        for tipo, info in mais_novos.items():
            periodo = ""
            if info["de"] and info["ate"]:
                de = datetime.date.fromisoformat(info["de"])
                ate = datetime.date.fromisoformat(info["ate"])
                periodo = f"{de.strftime('%d/%m')} a {ate.strftime('%d/%m/%Y')}"
            tipos[tipo] = {
                "quando": info["quando"].isoformat(timespec="seconds"),
                "texto": info["quando"].strftime("%d/%m/%Y %H:%M"),
                "rotulo": ROTULOS_DO_PERIODO[tipo],
                "operacao": info["operacao"],
                "periodo": periodo,
                "nome": info["nome"],
            }
        return {"tipos": tipos, "pasta": bool(base and os.path.isdir(base))}

    @staticmethod
    def _calcular_por_grupo(operation_key, tipo, lido, result, quando=None):
        """Resultado Gestor e Resultado Turno: os indicadores de cada gestor
        (ou turno) por semana, ou do mes."""
        dimensao, periodo = POR_GRUPO[tipo]
        de, ate = result.get("date_from"), result.get("date_to")
        nome = "Supervisor" if dimensao == "gestor" else "Shift"
        if not lido.get("tem_grupo"):
            result["indicators_message"] = (
                f"Relatório salvo, mas veio sem a coluna de {nome}: "
                f"confira o agrupamento ({result.get('agrupamento')})."
            )
            return
        if periodo == "week":
            if not lido["tem_semana"]:
                result["indicators_message"] = (
                    "Relatório salvo, mas veio sem a coluna de semana: "
                    "não deu pra separar por semana."
                )
                return
            por_chave = grupos.por_semana_e_grupo(lido["linhas"])
            parciais = {chave: periodos.semana_parcial(chave, de, ate) for chave in por_chave}
        else:
            chave = result.get("month_key")
            if not chave:
                result["indicators_message"] = (
                    "Relatório salvo, mas não deu pra identificar de que mês "
                    "ele é: informe o período na tela e extraia de novo."
                )
                return
            por_chave = {chave: grupos.por_grupo(lido["linhas"])}
            parciais = {chave: periodos.mes_parcial(chave, de, ate)}
        grupos_store.salvar(dimensao, operation_key, periodo, por_chave, de, ate, parciais, quando=quando)
        result["indicators"] = len(por_chave)

    def _check_extraction_params(self, group_by, period):
        """Validacoes comuns as duas abas de extracao. Devolve None quando
        esta tudo certo, ou um dict de erro pra devolver pra tela."""
        if not self.is_logged_in():
            return {"success": False, "message": "Faça login antes de executar."}

        if self._senhas_recusadas >= LIMITE_DE_SENHA_RECUSADA:
            return {"success": False, "senhas_recusadas": self._senhas_recusadas,
                    "message": MENSAGEM_SENHA_RECUSADA}

        if group_by and group_by not in GROUP_BY_OPTIONS:
            return {"success": False, "message": "Opção de 'Group By 1' inválida."}

        if period and period not in PASTAS_DO_PERIODO:
            return {"success": False, "message": "Período do indicador inválido."}

        folder_check = self.validate_sharepoint_folder()
        if not folder_check["valid"]:
            return {"success": False, "message": folder_check["message"]}

        return None

    def run_extraction(self, operation_key, date_range=None, group_by=None, period=None):
        with self._extraindo():
            return self._executar_extracao(operation_key, date_range, group_by, period)

    def _executar_extracao(self, operation_key, date_range, group_by, period):
        if operation_key not in OPERATIONS:
            return {"success": False, "message": "Operação inválida."}

        error = self._check_extraction_params(group_by, period)
        if error:
            return error

        # SCORECARD_HEADLESS=0 mostra o navegador de verdade, fazendo a
        # automacao na tela — util pra descobrir em qual etapa exata algo
        # trava ou demora, ja que o .exe empacotado nao mostra log nenhum.
        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"

        # Sem VPN o login so falharia no timeout, com o navegador aberto.
        self._emit_js("updateProgress", "verificando a conexão com o servidor...")
        if not conexao.alcancavel(OPERATIONS[operation_key]["login_url"]):
            result = self._sem_conexao(operation_key, date_range, group_by, period)
            self._record_history(operation_key, result)
            result["status"] = "error"
            return result

        # Importado aqui e nao no topo: o Playwright leva uma fracao de
        # segundo pra carregar, e a abertura do app nao precisa dele.
        from automation import generic

        result = generic.run(
            operation_key,
            base_dir=settings_store.get_sharepoint_folder(),
            headless=headless,
            username=self._username,
            password=self._password,
            on_progress=lambda step: self._emit_js("updateProgress", step),
            date_range=date_range,
            group_by=group_by,
            period=period,
        )
        self._calcular_indicadores(operation_key, result)
        self._registrar_no_sharepoint(operation_key, result)
        self._record_history(operation_key, result)
        if self._contar_senha(result):
            result["message"] = MENSAGEM_SENHA_RECUSADA
        result["status"] = self._status_da_extracao(result)
        return result

    @staticmethod
    def _sem_conexao(operation_key, date_range, group_by, period):
        """Resultado de uma extracao barrada antes de abrir o navegador,
        no mesmo formato que a automacao devolve, para ir ao historico."""
        config = OPERATIONS[operation_key]
        tipo = period if period in PASTAS_DO_PERIODO else "week"
        if date_range:
            rotulo = " - ".join(
                datetime.date.fromisoformat(date_range[campo]).strftime("%d/%m/%Y")
                for campo in ("from_date", "to_date"))
        else:
            rotulo = DEFAULT_DATE_RANGE["week" if e_semanal(tipo) else "month"]
        niveis = agrupamento(tipo, group_by, config["group_by_option"])
        mensagem = conexao.mensagem(config["login_url"])
        log.warning("extração %s barrada: %s", operation_key, mensagem)
        return {
            "operation": operation_key,
            "operation_label": config["label"],
            "period_label": rotulo,
            "tipo": tipo,
            "period_type": ROTULOS_DO_PERIODO[tipo],
            "group_by": niveis[-1],
            "agrupamento": " › ".join(niveis),
            "success": False,
            "message": mensagem,
            "duration_seconds": 0.0,
        }

    def cancel_multi_extraction(self):
        """Pedido de parada vindo da tela. A operacao em andamento vai
        ate o fim (interromper o navegador no meio deixaria o download
        pela metade); a fila para antes da proxima."""
        self._cancel_multi.set()
        return {"success": True}

    def run_multi_extraction(self, operation_keys, date_range=None, group_by=None, period=None):
        """Varias operacoes, o mesmo tipo de extracao."""
        with self._extraindo():
            return self._executar_fila(operation_keys, date_range, group_by, period)

    def run_multi_filters(self, operation_key, periods, date_range=None, group_by=None):
        """Uma operacao, varios tipos de extracao (Week, Month, Gestor...)
        em sequencia, com as mesmas datas: o "Vários filtros" do Extrair
        Multiplos."""
        with self._extraindo():
            return self._executar_fila([operation_key], date_range, group_by, tipos=periods)

    def _executar_fila(self, operation_keys, date_range, group_by, period=None, tipos=None):
        """Roda as extracoes da fila, uma depois da outra: varias operacoes
        com o mesmo tipo (period), ou uma operacao com varios tipos
        (tipos). Uma falha nao interrompe a fila: as demais continuam e o
        resumo no final diz quantas deram certo."""
        operation_keys = [key for key in (operation_keys or []) if key in OPERATIONS]
        if tipos is not None:
            if not operation_keys:
                return {"success": False, "message": "Escolha a operação."}
            tipos = [t for t in PASTAS_DO_PERIODO if t in tipos]
            if not tipos:
                return {"success": False, "message": "Selecione pelo menos um tipo de extração."}
            error = self._check_extraction_params(group_by, None)
            trabalhos = [(operation_keys[0], t, ROTULOS_DO_PERIODO[t]) for t in tipos]
        else:
            if not operation_keys:
                return {"success": False, "message": "Selecione pelo menos uma operação."}
            error = self._check_extraction_params(group_by, period)
            trabalhos = [(key, period, OPERATIONS[key]["label"]) for key in operation_keys]
        if error:
            return error

        self._cancel_multi.clear()
        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"
        base_dir = settings_store.get_sharepoint_folder()
        total = len(trabalhos)
        succeeded = 0
        cancelled = 0
        sem_indicador = 0

        # Um navegador so para a fila inteira; cada extracao abre uma
        # sessao propria nele (ver automation.base.Navegador). O login
        # continua sendo um por extracao: cada operacao e um servidor/site
        # diferente do BlueYonder.
        from automation import generic
        from automation.base import Navegador

        log.info("fila de %s extrações (%s)", total, ", ".join(sorted({t[1] or "week" for t in trabalhos})))
        navegador = None
        servidores_fora = set()  # sem VPN, nao tenta de novo o mesmo servidor
        parada_por_senha = False
        try:
            for index, (operation_key, period, label) in enumerate(trabalhos):
                if self._cancel_multi.is_set():
                    cancelled += 1
                    self._emit_js("updateMultiProgress", {
                        "index": index,
                        "total": total,
                        "operation_label": label,
                        "step": "Cancelada",
                        "status": "cancelled",
                    })
                    continue

                def on_progress(step, _index=index, _label=label):
                    self._emit_js("updateMultiProgress", {
                        "index": _index,
                        "total": total,
                        "operation_label": _label,
                        "step": step,
                        "status": "running",
                    })

                url = OPERATIONS[operation_key]["login_url"]
                on_progress("verificando a conexão com o servidor...")
                if conexao.destino(url) in servidores_fora or not conexao.alcancavel(url):
                    servidores_fora.add(conexao.destino(url))
                    result = self._sem_conexao(operation_key, date_range, group_by, period)
                else:
                    if navegador is None or not navegador.ativo():
                        if navegador is not None:
                            navegador.fechar()  # caiu no meio da fila: abre outro
                        on_progress("abrindo o navegador...")
                        navegador = Navegador(headless=headless)

                    result = generic.run(
                        operation_key,
                        base_dir=base_dir,
                        headless=headless,
                        username=self._username,
                        password=self._password,
                        on_progress=on_progress,
                        date_range=date_range,
                        group_by=group_by,
                        period=period,
                        navegador=navegador,
                    )
                self._calcular_indicadores(operation_key, result)
                self._registrar_no_sharepoint(operation_key, result)
                self._record_history(operation_key, result)
                if self._contar_senha(result):
                    # A senha errada nao vai dar certo na proxima operacao.
                    parada_por_senha = True
                    self._cancel_multi.set()

                status = self._status_da_extracao(result)
                if status != "error":
                    succeeded += 1
                if status == "warning":
                    sem_indicador += 1
                self._emit_js("updateMultiProgress", {
                    "index": index,
                    "total": total,
                    "operation_label": label,
                    "step": result.get("indicators_message") or result.get("message", ""),
                    "status": status,
                })
        finally:
            if navegador is not None:
                navegador.fechar()

        failed = total - succeeded - cancelled
        message = f"{succeeded} de {total} extrações concluídas"
        if failed:
            message += f", {failed} com falha"
        if sem_indicador:
            message += f", {sem_indicador} sem indicador"
        if cancelled:
            message += f", {cancelled} cancelada(s)"
        message += "."
        if parada_por_senha:
            message += " " + MENSAGEM_SENHA_RECUSADA
        log.info("fila encerrada: %s", message)
        return {
            "success": failed == 0 and cancelled == 0,
            "senhas_recusadas": self._senhas_recusadas,
            "message": message,
            "succeeded": succeeded,
            "failed": failed,
            "cancelled": cancelled,
            "sem_indicador": sem_indicador,
        }

    # ---------------- Versao e diagnostico ----------------

    def log_erro_tela(self, origem, mensagem):
        """Erro de JavaScript da interface, para o log (o filtro do log
        tira usuario e senha, se aparecerem)."""
        log.error("erro na tela (%s): %s", origem, str(mensagem)[:4000])
        return {"success": True}

    def get_app_info(self):
        return versao.info()

    def get_novidades(self):
        """Novidades da versao e se a tela mostra o tour ou a janela
        "O que ha de novo" ao abrir (novidades.py)."""
        return novidades.estado()

    def marcar_visto(self, o_que):
        try:
            return {"success": True, **novidades.marcar(o_que)}
        except ValueError as exc:
            return {"success": False, "message": str(exc)}

    def gerar_diagnostico(self):
        """Zip com log, versao e ambiente, sem credenciais nem dados das
        pessoas, na pasta Downloads — pra mandar a quem da suporte."""
        try:
            caminho = diagnostico.gerar()
        except OSError as exc:
            log.exception("não deu pra gerar o diagnóstico")
            return {"success": False, "message": f"Não deu pra gerar o diagnóstico: {exc}"}
        log.info("diagnóstico gerado em %s", caminho)
        self._mostrar_arquivo(caminho, "Pasta do diagnóstico")
        return {"success": True, "caminho": caminho,
                "message": f"Diagnóstico salvo em {caminho}"}

    def salvar_imagem(self, nome, conteudo_base64):
        """PNG da tabela da Inicio na pasta Downloads (botao Imagem com
        Shift, ou quando a copia nao deu)."""
        try:
            caminho = exportar_imagem.salvar_png(nome, conteudo_base64)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        except OSError as exc:
            log.exception("não deu pra salvar a imagem")
            return {"success": False, "message": f"Não deu pra salvar a imagem: {exc}"}
        log.info("imagem da tabela salva em %s", caminho)
        self._mostrar_arquivo(caminho, "Pasta da imagem")
        return {"success": True, "caminho": caminho, "message": f"Imagem salva em {caminho}"}

    def _mostrar_arquivo(self, caminho, descricao):
        """Abre o Explorer ja com o arquivo selecionado."""
        if sys.platform == "win32":
            try:
                subprocess.Popen(["explorer", "/select,", caminho])
            except OSError:
                pass
        else:
            self._open_path(os.path.dirname(caminho), descricao)

    # ---------------- Abrir arquivos ----------------

    @staticmethod
    def _open_path(path, descricao):
        """Abre um arquivo ou pasta no gerenciador do sistema."""
        if not path or not os.path.exists(path):
            return {"success": False, "message": f"{descricao} não encontrada."}
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def open_last_folder(self):
        return self._open_path(self._last_folder, "Pasta do último relatório")

    def open_error_screenshot(self):
        return self._open_path(self._last_screenshot, "Imagem do erro")

    # ---------------- Indicadores ----------------

    @cache_de_telas.guardada
    def operacoes_com_dados(self, mes):
        """Operacoes com alguma coluna (semana, mes ou pico) no mes, na
        ordem do menu. A apresentacao automatica passa so por elas: antes
        ela carregava a tabela de cada operacao ate achar uma com dados,
        e com uma so operacao no mes dava a volta e parecia travada."""
        if not isinstance(mes, str) or not re.fullmatch(r"\d{4}-\d{2}", mes):
            return []
        com_dados = []
        for chave in OPERATIONS:
            do_mes = periodos.so_do_mes(indicators_store.get_indicators(chave), mes)
            if any(do_mes[tipo] for tipo in ("week", "month", "peak")):
                com_dados.append(chave)
        return com_dados

    @cache_de_telas.guardada
    def get_indicator_table(self, operation_key, mes=None):
        """Monta a tabela da aba Inicio ja pronta pra desenhar: os seis
        indicadores nas linhas, as semanas nas colunas e os meses no
        fim, com o texto e a cor de cada celula.

        As faixas de cor e a formatacao ficam aqui, no Python, e nao no
        JavaScript: sao regra de negocio, e regra de negocio repetida em
        dois lugares vira duas regras diferentes na primeira mudanca.
        """
        if operation_key not in OPERATIONS:
            return {"operacao": "", "colunas": [], "linhas": [], "meses": [], "mes": None}

        tudo = indicators_store.get_indicators(operation_key)
        # A aba Inicio mostra um mes so: as semanas que tem algum dia nele
        # (31/08 a 06/09 e de setembro), e o mes e o pico dele. Semana de
        # mes que ja passou nao entra. Abre no mes atual; o seletor deixa
        # olhar o anterior (no comeco do mes, e ali que esta o fechamento).
        meses_com_dado = periodos.meses_com_dados(tudo)
        atual = datetime.date.today().strftime("%Y-%m")
        mes = mes if mes in meses_com_dado or mes == atual else atual
        guardado = periodos.so_do_mes(tudo, mes)
        # Presenteismo calculado agora, do quadro e das faltas. Nao se usa
        # valor gravado: qualquer mudanca na aba Headcount ja vale aqui, e
        # nao sobra numero antigo preso no indicador.
        ao_vivo = headcount.presenteismo_por_periodo(
            operation_key,
            semanas=list(guardado.get("week", {})),
            meses=list(set(guardado.get("month", {})) | set(guardado.get("peak", {}))),
        )
        colunas = []

        # So entra na aba Inicio a semana ou o mes que veio do Summary: e
        # ele que define as colunas. O presenteismo preenche essas colunas,
        # nao cria outras. As faltas de uma semana que nao foi extraida
        # continuam contando no ciclo da folha ponto, calculado por dia.
        for chave in sorted(guardado.get("week", {})):
            entrada = dict(guardado["week"][chave])
            titulo, subtitulo = periodos.rotulo_semana(chave)
            colunas.append({
                "chave": chave,
                "periodo": "week",
                "titulo": titulo,
                "subtitulo": subtitulo,
                "parcial": bool(entrada.get("parcial")),
                "_entrada": self._com_coverage(
                    self._com_presenteismo(entrada, ao_vivo["week"].get(chave)),
                    operation_key, "week", chave),
            })

        # Mes: mesma regra, so o que veio do Summary. O presenteismo que
        # entra nele e o do ciclo da folha ponto que fecha no dia 12 desse
        # mes (outubro = 13/09 a 12/10).
        # Logo depois de cada mes vem o pico dele, se foi extraido.
        meses = guardado.get("month", {})
        picos = guardado.get("peak", {})
        for chave in sorted(set(meses) | set(picos)):
            entrada_mes = dict(meses.get(chave, {}))
            vivo = ao_vivo["month"].get(chave)
            if chave in meses:
                de = entrada_mes.get("de") or (vivo or {}).get("de")
                ate = entrada_mes.get("ate") or (vivo or {}).get("ate")
                titulo, subtitulo = periodos.rotulo_mes(chave, de, ate)
                colunas.append({
                    "chave": chave,
                    "periodo": "month",
                    "titulo": titulo,
                    "subtitulo": subtitulo,
                    "parcial": False,
                    "_entrada": self._com_coverage(
                        self._com_presenteismo(dict(entrada_mes), vivo),
                        operation_key, "month", chave),
                })
            if chave in picos:
                colunas.append(self._coluna_pico(chave, picos[chave], entrada_mes, vivo))

        linhas = []
        for indicador in limits.ORDEM:
            celulas = []
            for coluna in colunas:
                if indicador in coluna.get("sem", ()):
                    celulas.append({"texto": "", "cor": "", "nao_se_aplica": True})
                    continue
                valor = coluna["_entrada"].get(indicador)
                celula = {
                    "texto": limits.formatar(valor),
                    "cor": limits.cor(indicador, valor),
                }
                dica = explicacoes.explicar(indicador, coluna["_entrada"], coluna["periodo"])
                if dica:
                    celula["dica"] = dica
                celulas.append(celula)
            linhas.append({
                "chave": indicador,
                "rotulo": limits.ROTULOS[indicador],
                "meta": limits.METAS[indicador],
                "celulas": celulas,
            })

        resumo = self._resumo_da_inicio(operation_key, colunas, tudo)

        for coluna in colunas:
            coluna.pop("_entrada")
            coluna.pop("sem", None)

        # A extracao mais nova dos dados da operacao, de quem quer que tenha
        # extraido (os que vem da pasta do SharePoint guardam a data do
        # arquivo).
        ultima = max((entrada.get("extraido_em") or ""
                      for por_periodo in tudo.values() if isinstance(por_periodo, dict)
                      for entrada in por_periodo.values() if isinstance(entrada, dict)), default="")
        return {
            "operacao": OPERATIONS[operation_key]["label"],
            "ultima_extracao": ultima or None,
            "colunas": colunas,
            "linhas": linhas,
            "distribuicao": self._distribuicao_do_mes(meses.get(mes)),
            "resumo": resumo,
            "mes": mes,
            "meses": [{"id": m, "rotulo": periodos.rotulo_mes_ano(m)}
                      for m in sorted(set(meses_com_dado) | {atual}, reverse=True)],
        }

    def _resumo_da_inicio(self, operation_key, colunas, tudo):
        """O resumo do topo da Inicio (resumo_inicio.py). A coluna de
        referencia e o mes; sem ele, a ultima semana. O anterior e o mes
        de antes (da extracao Month dele) ou a semana de antes."""
        mensal = [c for c in colunas if c["periodo"] == "month"]
        semanas = [c for c in colunas if c["periodo"] == "week"]
        referencia = (mensal or semanas or [None])[-1]
        if referencia is None:
            return None

        def valores(entrada, sem=()):
            return {i: entrada.get(i) for i in limits.ORDEM if i not in sem}

        anterior = None
        if referencia["periodo"] == "month":
            chave = referencia["chave"]
            ano, numero = int(chave[:4]), int(chave[5:7])
            antes = f"{ano - 1}-12" if numero == 1 else f"{ano}-{numero - 1:02d}"
            entrada = (tudo.get("month") or {}).get(antes)
            if entrada:
                vivo = headcount.presenteismo_por_periodo(operation_key, semanas=[], meses=[antes])["month"].get(antes)
                entrada = self._com_coverage(self._com_presenteismo(dict(entrada), vivo), operation_key, "month", antes)
                anterior = {"rotulo": periodos.rotulo_mes_ano(antes), **resumo_inicio.contar(valores(entrada))}
        elif len(semanas) > 1:
            antes = semanas[-2]
            anterior = {"rotulo": antes["titulo"], **resumo_inicio.contar(valores(antes["_entrada"], antes.get("sem", ())))}
        return resumo_inicio.resumir(referencia["titulo"], referencia["periodo"],
                                     valores(referencia["_entrada"], referencia.get("sem", ())), anterior)

    @staticmethod
    def _distribuicao_do_mes(entrada_mes):
        """O grafico de distribuicao da dispersao do mes, da extracao
        Month. Mes extraido antes deste grafico existir nao tem a
        contagem por faixa guardada: a tela pede para extrair de novo."""
        if not entrada_mes:
            return {"estado": "sem_extracao"}
        if entrada_mes.get("faixas_dispersao") is None:
            # Sem User ID no agrupamento a contagem nao e de pessoas.
            if entrada_mes.get("group_by") not in (None, "User ID"):
                return {"estado": "sem_user_id"}
            return {"estado": "extrair_de_novo"}
        return {"estado": "ok", **weekly.distribuicao_da_dispersao(entrada_mes["faixas_dispersao"])}

    def _coluna_pico(self, chave, entrada_pico, entrada_mes, vivo):
        """O pico usa efetividade, dispersao e presenteismo do mes; so a
        hora direta e dos dias de pico — e o cubo muda com ela. Sem a
        extracao mensal, fica so a hora direta, e o cubo sem numero."""
        # Para a dica: as somas do mes (efetividade e dispersao) e os dias
        # de pico (hora direta).
        entrada = {campo: entrada_mes.get(campo) for campo in (
            "efetividade", "dispersao", "soma_goal", "soma_measured_direct", "dentro", "fora")}
        entrada["hora_direta"] = entrada_pico.get("hora_direta")
        entrada["_dias_pico"] = entrada_pico.get("dias") or []
        dias = [datetime.date.fromisoformat(d["data"]).strftime("%d/%m")
                for d in entrada_pico.get("dias", [])]
        titulo, _ = periodos.rotulo_mes(chave)
        return {
            "chave": f"pico-{chave}",
            "periodo": "peak",
            "titulo": "Pico",
            "subtitulo": f"{titulo} · {len(dias)} dias",
            "parcial": bool(entrada_pico.get("parcial")),
            "aviso": "mês em andamento",
            "dica": "Dias de pico: " + ", ".join(dias) if dias else "",
            # O pico vai do CUBO a DISPERSAO; coverage nao se aplica.
            "sem": ["coverage"],
            "_entrada": self._com_presenteismo(entrada, vivo),
        }

    @staticmethod
    def _com_coverage(entrada, operation_key, periodo, chave):
        """Poe o coverage total da aba Coverage, calculado agora (com os
        dias, horas e sinergias digitados la)."""
        total = coverage_tela.total_detalhado(operation_key, periodo, chave)
        if total is not None:
            entrada["coverage"] = total["coverage"]
            entrada["_coverage_partes"] = total
        return entrada

    @staticmethod
    def _com_presenteismo(entrada, vivo):
        """Poe o presenteismo calculado na hora e refaz o CUBO com ele."""
        entrada["presenteismo"] = vivo["presenteismo"] if vivo else None
        entrada["_presenteismo_partes"] = vivo or {}
        entrada["cubo"] = weekly.calcular_cubo(
            entrada.get("efetividade"),
            entrada.get("hora_direta"),
            entrada["presenteismo"],
        )
        return entrada

    # ---------------- Headcount / presenteismo ----------------

    @cache_de_telas.guardada
    def get_headcount(self, operacao=None, visualizacao="semanal", mes=None, periodo_id=None):
        """O estado inteiro da tela de Headcount, pronto pra desenhar.

        Cada gestor leva tambem se o nome dele bate com um supervisor do
        Summary ("summary": "ligado", "sem_par", ou None quando a operacao
        ainda nao tem extracao com o Supervisor)."""
        tela = headcount.montar(
            operacao=operacao or headcount.TODAS,
            visualizacao=visualizacao or "semanal",
            mes=mes,
            periodo_id=periodo_id,
        )
        conhecidos = {}
        for linha in tela["linhas"]:
            op = linha["operacao_key"]
            if op not in conhecidos:
                conhecidos[op] = {headcount.nome_comparavel(n) for n in grupos_tela.nomes_do_summary(op)}
            if not conhecidos[op]:
                linha["summary"] = None
            else:
                linha["summary"] = ("ligado" if headcount.nome_comparavel(linha["gestor"]) in conhecidos[op]
                                    else "sem_par")
        return tela

    def get_nomes_do_summary(self, operacao):
        """Supervisores do Summary da operacao, para sugerir no cadastro de
        gestor do Headcount."""
        if operacao not in OPERATIONS:
            return []
        return grupos_tela.nomes_do_summary(operacao)

    # ---------------- Preferencias de tela ----------------

    def get_preferencias(self):
        return settings_store.get_preferencias()

    def set_preferencia(self, chave, valor):
        try:
            return {"success": True, "preferencias": settings_store.set_preferencia(chave, valor)}
        except ValueError as exc:
            return {"success": False, "message": str(exc)}

    def add_gestor(self, nome, operacao):
        """A operacao e escolhida na faixa de cadastro. Sem ela, nao
        cadastra: antes, com o filtro em "todas", o gestor caia calado
        na primeira operacao da lista e o HC dele somava no lugar
        errado."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha a operação do gestor."}
        try:
            gestor = self._lancar(headcount_store.adicionar_gestor, nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "gestor": gestor}

    def update_gestor(self, gestor_id, campos):
        try:
            self._lancar(headcount_store.atualizar_gestor, gestor_id, campos or {})
        except (ValueError, TypeError) as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    # ---------------- Coverage ----------------

    @cache_de_telas.guardada
    def get_indiretas(self, operacao=None, mes=None, semana_id=None):
        """A aba Horas Indiretas montada (ver indiretas_tela.py)."""
        return indiretas_tela.montar(operacao, mes, semana_id)

    @cache_de_telas.guardada
    def get_coverage(self, operacao=None, visualizacao="semanal", mes=None, periodo_id=None, gestor=None):
        return coverage_tela.montar(operacao or "todas", visualizacao, mes, periodo_id, gestor=gestor)

    # ---------------- Resultado Gestor / Turno ----------------

    @cache_de_telas.guardada
    def get_resultado_grupo(self, dimensao, operacao=None, mes=None):
        """A aba Resultado Gestor ("gestor") ou Resultado Turno ("turno")
        montada (ver grupos_tela.py)."""
        if dimensao not in grupos_store.DIMENSOES:
            return {"success": False, "message": "Aba inválida."}
        return grupos_tela.montar(dimensao, operacao, mes)

    def set_grupos_visiveis(self, dimensao, operacao, da_tela, visiveis):
        """Quais gestores (ou turnos) aparecem na aba. Os nomes nao vao
        para o log: sao dados das pessoas."""
        try:
            grupos_tela.definir_visiveis(dimensao, operacao, da_tela, visiveis)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_coverage(self, operacao, chave_periodo, usuario, campo, valor):
        """Dias, horas ou sinergia (cedida/recebida) de um usuario."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Operação inválida."}
        try:
            self._lancar(coverage_store.definir, operacao, chave_periodo, [usuario], campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_coverage_sinergia(self, operacao, chave_periodo, campo, valor):
        """Sinergia cedida ou recebida da operacao no periodo (linha TOTAL)."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha uma operação para lançar a sinergia."}
        try:
            self._lancar(coverage_store.definir_sinergia, operacao, chave_periodo, campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_coverage_todos(self, operacao, visualizacao, mes, periodo_id, campo, valor, gestor=None):
        """O mesmo valor de dias ou horas para todos os usuarios da tela
        (semana de feriado, por exemplo). Com um gestor no filtro, so os
        usuarios dele."""
        if campo not in ("dias", "horas"):
            return {"success": False, "message": "Só dias e horas valem para todos."}
        tela = coverage_tela.montar(operacao or "todas", visualizacao, mes, periodo_id, gestor=gestor)
        grupos = {}
        for linha in tela["linhas"]:
            grupos.setdefault((linha["operacao_key"], linha["chave_periodo"]), []).append(linha["usuario"])
        def definir_todos():
            for (op, chave_periodo), usuarios in grupos.items():
                coverage_store.definir(op, chave_periodo, usuarios, campo, valor)
        try:
            self._lancar(definir_todos)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "usuarios": len(tela["linhas"])}

    def set_quadro(self, gestor_id, periodo_id, campo, valor):
        """HC, dias uteis, horas/dia ou faltas de um gestor numa semana (ou
        ciclo da folha). Cada periodo tem os seus numeros."""
        try:
            self._lancar(headcount_store.definir_quadro, gestor_id, periodo_id, campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_faltas(self, gestor_id, periodo_id, valor):
        """Faltas em dias digitadas na tela de Headcount, por gestor e por
        semana (ou ciclo da folha). Valem na hora na aba Inicio."""
        try:
            self._lancar(headcount_store.lancar_faltas, gestor_id, periodo_id, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def edit_gestor(self, gestor_id, nome, operacao):
        """Corrige o nome ou muda a operacao de um gestor. O quadro
        digitado (HC, dias, horas) fica como estava."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha a operação do gestor."}
        try:
            gestor = self._lancar(headcount_store.editar_gestor, gestor_id, nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        # So o id: nome de gestor nao vai para o log (o diagnostico leva o
        # log, e ele nao pode levar dados das pessoas).
        log.info("gestor %s editado", gestor_id)
        return {"success": True, "gestor": gestor}

    def remove_gestor(self, gestor_id):
        removido = self._lancar(headcount_store.remover_gestor, gestor_id)
        if not removido:
            return {"success": False, "message": "Gestor não encontrado."}
        log.info("gestor %s excluído", gestor_id)
        return {"success": True}

    def add_funcao(self, nome, operacao):
        """Uma funcao a mais que passa a contar como falta nos gestores da
        operacao escolhida. Vale na hora: o filtro roda toda vez que as
        faltas sao lidas, entao nao precisa reenviar a planilha."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha a operação da função."}
        try:
            funcoes = self._lancar(headcount_store.adicionar_funcao, nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "funcoes": funcoes, **self._resumo_atual()}

    def remove_funcao(self, nome, operacao=None):
        funcoes = self._lancar(headcount_store.remover_funcao, nome, operacao)
        return {"success": True, "funcoes": funcoes, **self._resumo_atual()}

    @staticmethod
    def _resumo_atual():
        arquivo = headcount_store.arquivo()
        return {"resumo": arquivo["resumo"]} if arquivo else {}

    def import_faltas(self, nome_arquivo, conteudo_base64):
        """Recebe a planilha da tela (arrastada ou escolhida) como
        conteudo, nao como caminho: dentro da janela do app o navegador
        nao entrega o caminho do arquivo arrastado."""
        try:
            bruto = base64.b64decode((conteudo_base64 or "").split(",")[-1])
        except Exception:  # noqa: BLE001 - conteudo invalido vindo da tela
            return {"success": False, "message": "Não consegui ler o arquivo enviado."}

        if len(bruto) > 10 * 1024 * 1024:
            return {"success": False, "message": "O arquivo passa de 10 MB."}

        extensao = os.path.splitext(nome_arquivo or "")[1] or ".xlsx"
        caminho = None
        try:
            with tempfile.NamedTemporaryFile(suffix=extensao, delete=False) as fh:
                fh.write(bruto)
                caminho = fh.name
            linhas = faltas_reader.ler_linhas(caminho)
        except ValueError as exc:
            log.warning("planilha de faltas %s recusada: %s", nome_arquivo, exc)
            return {"success": False, "message": str(exc)}
        except Exception as exc:  # noqa: BLE001 - arquivo fora do esperado
            log.exception("não deu pra ler a planilha de faltas %s", nome_arquivo)
            return {"success": False, "message": f"Não deu pra ler a planilha: {exc}"}
        finally:
            if caminho and os.path.exists(caminho):
                try:
                    os.remove(caminho)
                except OSError:
                    pass

        arquivo = headcount_store.salvar_faltas(nome_arquivo, len(bruto), linhas)
        log.info("planilha de faltas %s importada: %s linhas, %s consideradas",
                 nome_arquivo, arquivo["resumo"]["linhas"], arquivo["resumo"]["consideradas"])
        return {"success": True, "resumo": arquivo["resumo"]}

    def clear_faltas(self):
        headcount_store.limpar_faltas()
        return {"success": True}

    def save_headcount_config(self, campos):
        return {"success": True, "config": headcount_store.salvar_config(campos or {})}

    # ---------------- Historico ----------------

    def get_report_history(self):
        return history_store.get_history()
