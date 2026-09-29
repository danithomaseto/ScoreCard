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
import subprocess
import sys
import tempfile
import threading

import webview

from config.operations import (
    DEFAULT_DATE_RANGE, GROUP_BY_OPTIONS, OPERATIONS, PASTAS_DO_PERIODO, escala_espanhola,
)
import conexao
import coverage_store
import coverage_tela
import diagnostico
import headcount
import headcount_store
import history_store
from indicators import faltas as faltas_reader
from indicators import coverage, limits, periodos, pico, reader, weekly
import indicators_store
import registro
import settings_store
import versao

log = logging.getLogger("scorecard.api")


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
        # Modo apresentacao (tela cheia). A janela abre maximizada
        # (main.py); os eventos abaixo acompanham se o usuario mudou isso,
        # para a saida da tela cheia voltar do jeito que estava.
        self._tela_cheia = False
        self._maximizada = True

    def set_window(self, window):
        self._window = window
        try:
            window.events.maximized += self._ficou_maximizada
            window.events.restored += self._ficou_restaurada
        except Exception:  # noqa: BLE001 - so perde o "voltar maximizada"
            log.debug("sem eventos de maximizar/restaurar nesta janela")

    def _ficou_maximizada(self):
        if not self._tela_cheia:
            self._maximizada = True

    def _ficou_restaurada(self):
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

    def is_logged_in(self):
        return bool(self._username and self._password)

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
        """Le o arquivo recem-baixado, calcula e grava os indicadores.

        Roda aqui, na hora da extracao, e nao na tela: o proximo
        download apaga este arquivo, entao quem nao calcular agora nao
        calcula mais.
        """
        if not result.get("success") or not result.get("file_path"):
            return

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

        if result.get("period_type") == "Dias de Pico":
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
        elif result.get("period_type") == "Month":
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
                operation_key, "month", {chave: coverage.por_usuario(lido["linhas"])}, de, ate)
        else:
            if not lido["tem_semana"]:
                result["indicators_message"] = (
                    "Relatório salvo, mas veio sem a coluna de semana: "
                    "não deu pra separar por semana."
                )
                return
            resultados = weekly.por_semana(lido["linhas"], nivel_detalhe=nivel_detalhe)
            for chave, totais in resultados.items():
                totais["parcial"] = periodos.semana_parcial(chave, de, ate)
            periodo = "week"
            # Coverage: as horas de cada usuario (segundo nivel do semanal).
            coverage_store.salvar_extracao(
                operation_key, "week", coverage.por_semana_e_usuario(lido["linhas"]), de, ate)

        indicators_store.salvar_extracao(operation_key, periodo, resultados, meta=meta)
        result["indicators"] = len(resultados)

    def _check_extraction_params(self, group_by, period):
        """Validacoes comuns as duas abas de extracao. Devolve None quando
        esta tudo certo, ou um dict de erro pra devolver pra tela."""
        if not self.is_logged_in():
            return {"success": False, "message": "Faça login antes de executar."}

        if group_by and group_by not in GROUP_BY_OPTIONS:
            return {"success": False, "message": "Opção de 'Group By 1' inválida."}

        if period and period not in ("week", "month", "peak"):
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
        self._record_history(operation_key, result)
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
            rotulo = DEFAULT_DATE_RANGE["week" if tipo == "week" else "month"]
        mensagem = conexao.mensagem(config["login_url"])
        log.warning("extração %s barrada: %s", operation_key, mensagem)
        return {
            "operation": operation_key,
            "operation_label": config["label"],
            "period_label": rotulo,
            "period_type": PASTAS_DO_PERIODO[tipo],
            "group_by": "Report Date" if tipo == "peak" else (group_by or config["group_by_option"]),
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
        with self._extraindo():
            return self._executar_fila(operation_keys, date_range, group_by, period)

    def _executar_fila(self, operation_keys, date_range, group_by, period):
        """Roda a mesma extracao para varias operacoes, uma depois da
        outra. Uma falha nao interrompe a fila: as demais continuam e o
        resumo no final diz quantas deram certo."""
        operation_keys = [key for key in (operation_keys or []) if key in OPERATIONS]
        if not operation_keys:
            return {"success": False, "message": "Selecione pelo menos uma operação."}

        error = self._check_extraction_params(group_by, period)
        if error:
            return error

        self._cancel_multi.clear()
        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"
        base_dir = settings_store.get_sharepoint_folder()
        total = len(operation_keys)
        succeeded = 0
        cancelled = 0
        sem_indicador = 0

        # Um navegador so para a fila inteira; cada operacao abre uma
        # sessao propria nele (ver automation.base.Navegador). O login
        # continua sendo um por operacao: cada uma e um servidor/site
        # diferente do BlueYonder.
        from automation import generic
        from automation.base import Navegador

        log.info("fila de %s operações (%s)", total, period or "week")
        navegador = None
        servidores_fora = set()  # sem VPN, nao tenta de novo o mesmo servidor
        try:
            for index, operation_key in enumerate(operation_keys):
                label = OPERATIONS[operation_key]["label"]

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
                self._record_history(operation_key, result)

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
        log.info("fila encerrada: %s", message)
        return {
            "success": failed == 0 and cancelled == 0,
            "message": message + ".",
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

    def gerar_diagnostico(self):
        """Zip com log, versao e ambiente, sem credenciais nem dados das
        pessoas, na pasta Downloads — pra mandar a quem da suporte."""
        try:
            caminho = diagnostico.gerar()
        except OSError as exc:
            log.exception("não deu pra gerar o diagnóstico")
            return {"success": False, "message": f"Não deu pra gerar o diagnóstico: {exc}"}
        log.info("diagnóstico gerado em %s", caminho)
        if sys.platform == "win32":
            try:  # abre o Explorer ja com o zip selecionado
                subprocess.Popen(["explorer", "/select,", caminho])
            except OSError:
                pass
        else:
            self._open_path(os.path.dirname(caminho), "Pasta do diagnóstico")
        return {"success": True, "caminho": caminho,
                "message": f"Diagnóstico salvo em {caminho}"}

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
        # entra nele e o do ciclo da folha ponto que comeca no dia 13.
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
                celulas.append({
                    "texto": limits.formatar(valor),
                    "cor": limits.cor(indicador, valor),
                })
            linhas.append({
                "chave": indicador,
                "rotulo": limits.ROTULOS[indicador],
                "meta": limits.METAS[indicador],
                "celulas": celulas,
            })

        for coluna in colunas:
            coluna.pop("_entrada")
            coluna.pop("sem", None)

        return {
            "operacao": OPERATIONS[operation_key]["label"],
            "colunas": colunas,
            "linhas": linhas,
            "mes": mes,
            "meses": [{"id": m, "rotulo": periodos.rotulo_mes_ano(m)}
                      for m in sorted(set(meses_com_dado) | {atual}, reverse=True)],
        }

    def _coluna_pico(self, chave, entrada_pico, entrada_mes, vivo):
        """O pico usa efetividade, dispersao e presenteismo do mes; so a
        hora direta e dos dias de pico — e o cubo muda com ela. Sem a
        extracao mensal, fica so a hora direta, e o cubo sem numero."""
        entrada = {campo: entrada_mes.get(campo) for campo in ("efetividade", "dispersao")}
        entrada["hora_direta"] = entrada_pico.get("hora_direta")
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
        valor = coverage_tela.total_do_periodo(operation_key, periodo, chave)
        if valor is not None:
            entrada["coverage"] = valor
        return entrada

    @staticmethod
    def _com_presenteismo(entrada, vivo):
        """Poe o presenteismo calculado na hora e refaz o CUBO com ele."""
        entrada["presenteismo"] = vivo["presenteismo"] if vivo else None
        entrada["cubo"] = weekly.calcular_cubo(
            entrada.get("efetividade"),
            entrada.get("hora_direta"),
            entrada["presenteismo"],
        )
        return entrada

    # ---------------- Headcount / presenteismo ----------------

    def get_headcount(self, operacao=None, visualizacao="semanal", mes=None, periodo_id=None):
        """O estado inteiro da tela de Headcount, pronto pra desenhar."""
        return headcount.montar(
            operacao=operacao or headcount.TODAS,
            visualizacao=visualizacao or "semanal",
            mes=mes,
            periodo_id=periodo_id,
        )

    def add_gestor(self, nome, operacao):
        """A operacao e escolhida na faixa de cadastro. Sem ela, nao
        cadastra: antes, com o filtro em "todas", o gestor caia calado
        na primeira operacao da lista e o HC dele somava no lugar
        errado."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha a operação do gestor."}
        try:
            gestor = headcount_store.adicionar_gestor(nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "gestor": gestor}

    def update_gestor(self, gestor_id, campos):
        try:
            headcount_store.atualizar_gestor(gestor_id, campos or {})
        except (ValueError, TypeError) as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    # ---------------- Coverage ----------------

    def get_coverage(self, operacao=None, visualizacao="semanal", mes=None, periodo_id=None):
        return coverage_tela.montar(operacao or "todas", visualizacao, mes, periodo_id)

    def set_coverage(self, operacao, chave_periodo, usuario, campo, valor):
        """Dias, horas ou sinergia (cedida/recebida) de um usuario."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Operação inválida."}
        try:
            coverage_store.definir(operacao, chave_periodo, [usuario], campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_coverage_sinergia(self, operacao, chave_periodo, campo, valor):
        """Sinergia cedida ou recebida da operacao no periodo (linha TOTAL)."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha uma operação para lançar a sinergia."}
        try:
            coverage_store.definir_sinergia(operacao, chave_periodo, campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_coverage_todos(self, operacao, visualizacao, mes, periodo_id, campo, valor):
        """O mesmo valor de dias ou horas para todos os usuarios da tela
        (semana de feriado, por exemplo)."""
        if campo not in ("dias", "horas"):
            return {"success": False, "message": "Só dias e horas valem para todos."}
        tela = coverage_tela.montar(operacao or "todas", visualizacao, mes, periodo_id)
        grupos = {}
        for linha in tela["linhas"]:
            grupos.setdefault((linha["operacao_key"], linha["chave_periodo"]), []).append(linha["usuario"])
        try:
            for (op, chave_periodo), usuarios in grupos.items():
                coverage_store.definir(op, chave_periodo, usuarios, campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "usuarios": len(tela["linhas"])}

    def set_quadro(self, gestor_id, periodo_id, campo, valor):
        """HC, dias uteis, horas/dia ou faltas de um gestor numa semana (ou
        ciclo da folha). Cada periodo tem os seus numeros."""
        try:
            headcount_store.definir_quadro(gestor_id, periodo_id, campo, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def set_faltas(self, gestor_id, periodo_id, valor):
        """Faltas em dias digitadas na tela de Headcount, por gestor e por
        semana (ou ciclo da folha). Valem na hora na aba Inicio."""
        try:
            headcount_store.lancar_faltas(gestor_id, periodo_id, valor)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True}

    def edit_gestor(self, gestor_id, nome, operacao):
        """Corrige o nome ou muda a operacao de um gestor. O quadro
        digitado (HC, dias, horas) fica como estava."""
        if operacao not in OPERATIONS:
            return {"success": False, "message": "Escolha a operação do gestor."}
        try:
            gestor = headcount_store.editar_gestor(gestor_id, nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        # So o id: nome de gestor nao vai para o log (o diagnostico leva o
        # log, e ele nao pode levar dados das pessoas).
        log.info("gestor %s editado", gestor_id)
        return {"success": True, "gestor": gestor}

    def remove_gestor(self, gestor_id):
        removido = headcount_store.remover_gestor(gestor_id)
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
            funcoes = headcount_store.adicionar_funcao(nome, operacao)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "funcoes": funcoes, **self._resumo_atual()}

    def remove_funcao(self, nome, operacao=None):
        funcoes = headcount_store.remover_funcao(nome, operacao)
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
