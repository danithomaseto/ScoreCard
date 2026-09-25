"""Metodos expostos para a interface (ui/app.js) via
pywebview.api.<metodo>(...). Cada metodo publico aqui vira uma funcao
chamavel do JavaScript.
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import threading

import webview

from automation import generic
from config.operations import GROUP_BY_OPTIONS, OPERATIONS
import headcount
import headcount_store
import history_store
from indicators import faltas as faltas_reader
from indicators import limits, periodos, presenteismo, reader, weekly
import indicators_store
import settings_store


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

    def set_window(self, window):
        self._window = window

    # ---------------- Login ----------------

    def login(self, username, password):
        username = (username or "").strip()
        password = password or ""
        if not username or not password:
            return {"success": False, "message": "Informe usuario e senha."}
        self._username = username
        self._password = password
        return {"success": True}

    def logout(self):
        self._username = None
        self._password = None
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
            return {"success": False, "message": "Janela nao inicializada."}

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
            return {"valid": False, "message": f"A pasta configurada nao existe mais: {folder}"}
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
            result["indicators_message"] = f"Relatorio salvo, mas nao deu pra calcular: {exc}"
            return

        nivel_detalhe = result.get("group_by")
        de, ate = result.get("date_from"), result.get("date_to")
        meta = {
            "group_by": nivel_detalhe,
            "origem": result.get("origem"),
            "de": de,
            "ate": ate,
        }

        if result.get("period_type") == "Month":
            chave = result.get("month_key")
            if not chave:
                result["indicators_message"] = (
                    "Relatorio salvo, mas nao deu pra identificar de que mes "
                    "ele e: informe o periodo na tela e extraia de novo."
                )
                return
            resultados = {chave: weekly.totais(lido["linhas"], nivel_detalhe=nivel_detalhe)}
            periodo = "month"
        else:
            if not lido["tem_semana"]:
                result["indicators_message"] = (
                    "Relatorio salvo, mas veio sem a coluna de semana: "
                    "nao deu pra separar por semana."
                )
                return
            resultados = weekly.por_semana(lido["linhas"], nivel_detalhe=nivel_detalhe)
            for chave, totais in resultados.items():
                totais["parcial"] = periodos.semana_parcial(chave, de, ate)
            periodo = "week"

        indicators_store.salvar_extracao(operation_key, periodo, resultados, meta=meta)
        result["indicators"] = len(resultados)

    def _check_extraction_params(self, group_by, period):
        """Validacoes comuns as duas abas de extracao. Devolve None quando
        esta tudo certo, ou um dict de erro pra devolver pra tela."""
        if not self.is_logged_in():
            return {"success": False, "message": "Faca login antes de executar."}

        if group_by and group_by not in GROUP_BY_OPTIONS:
            return {"success": False, "message": "Opcao de 'Group By 1' invalida."}

        if period and period not in ("week", "month"):
            return {"success": False, "message": "Periodo do indicador invalido."}

        folder_check = self.validate_sharepoint_folder()
        if not folder_check["valid"]:
            return {"success": False, "message": folder_check["message"]}

        return None

    def run_extraction(self, operation_key, date_range=None, group_by=None, period=None):
        if operation_key not in OPERATIONS:
            return {"success": False, "message": "Operacao invalida."}

        error = self._check_extraction_params(group_by, period)
        if error:
            return error

        # SCORECARD_HEADLESS=0 mostra o navegador de verdade, fazendo a
        # automacao na tela — util pra descobrir em qual etapa exata algo
        # trava ou demora, ja que o .exe empacotado nao mostra log nenhum.
        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"

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

    def cancel_multi_extraction(self):
        """Pedido de parada vindo da tela. A operacao em andamento vai
        ate o fim (interromper o navegador no meio deixaria o download
        pela metade); a fila para antes da proxima."""
        self._cancel_multi.set()
        return {"success": True}

    def run_multi_extraction(self, operation_keys, date_range=None, group_by=None, period=None):
        """Roda a mesma extracao para varias operacoes, uma depois da
        outra. Uma falha nao interrompe a fila: as demais continuam e o
        resumo no final diz quantas deram certo."""
        operation_keys = [key for key in (operation_keys or []) if key in OPERATIONS]
        if not operation_keys:
            return {"success": False, "message": "Selecione pelo menos uma operacao."}

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

        failed = total - succeeded - cancelled
        message = f"{succeeded} de {total} extracoes concluidas"
        if failed:
            message += f", {failed} com falha"
        if sem_indicador:
            message += f", {sem_indicador} sem indicador"
        if cancelled:
            message += f", {cancelled} cancelada(s)"
        return {
            "success": failed == 0 and cancelled == 0,
            "message": message + ".",
            "succeeded": succeeded,
            "failed": failed,
            "cancelled": cancelled,
            "sem_indicador": sem_indicador,
        }

    # ---------------- Abrir arquivos ----------------

    @staticmethod
    def _open_path(path, descricao):
        """Abre um arquivo ou pasta no gerenciador do sistema."""
        if not path or not os.path.exists(path):
            return {"success": False, "message": f"{descricao} nao encontrada."}
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
        return self._open_path(self._last_folder, "Pasta do ultimo relatorio")

    def open_error_screenshot(self):
        return self._open_path(self._last_screenshot, "Imagem do erro")

    # ---------------- Indicadores ----------------

    def get_indicator_table(self, operation_key):
        """Monta a tabela da aba Inicio ja pronta pra desenhar: os seis
        indicadores nas linhas, as semanas nas colunas e os meses no
        fim, com o texto e a cor de cada celula.

        As faixas de cor e a formatacao ficam aqui, no Python, e nao no
        JavaScript: sao regra de negocio, e regra de negocio repetida em
        dois lugares vira duas regras diferentes na primeira mudanca.
        """
        if operation_key not in OPERATIONS:
            return {"operacao": "", "colunas": [], "linhas": []}

        guardado = indicators_store.get_indicators(operation_key)
        # Presenteismo calculado agora, do quadro e das faltas. Nao se usa
        # valor gravado: qualquer mudanca na aba Headcount ja vale aqui, e
        # nao sobra numero antigo preso no indicador.
        ao_vivo = headcount.presenteismo_por_periodo(operation_key)
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
                "_entrada": self._com_presenteismo(entrada, ao_vivo["week"].get(chave)),
            })

        # Mes: mesma regra, so o que veio do Summary. O presenteismo que
        # entra nele e o do ciclo da folha ponto que comeca no dia 13.
        for chave in sorted(guardado.get("month", {})):
            entrada = dict(guardado.get("month", {}).get(chave, {}))
            vivo = ao_vivo["month"].get(chave)
            de = entrada.get("de") or (vivo or {}).get("de")
            ate = entrada.get("ate") or (vivo or {}).get("ate")
            titulo, subtitulo = periodos.rotulo_mes(chave, de, ate)
            colunas.append({
                "chave": chave,
                "periodo": "month",
                "titulo": titulo,
                "subtitulo": subtitulo,
                "parcial": False,
                "_entrada": self._com_presenteismo(entrada, vivo),
            })

        linhas = []
        for indicador in limits.ORDEM:
            celulas = []
            for coluna in colunas:
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

        return {
            "operacao": OPERATIONS[operation_key]["label"],
            "colunas": colunas,
            "linhas": linhas,
        }

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
        """A operacao vem do filtro ativo; quando ele esta em "todas",
        cai na primeira da lista, porque um gestor precisa pertencer a
        alguma."""
        if operacao in (None, "", headcount.TODAS):
            operacao = next(iter(OPERATIONS))
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

    def remove_gestor(self, gestor_id):
        return {"success": headcount_store.remover_gestor(gestor_id)}

    def add_funcao(self, nome):
        """Uma funcao a mais que passa a contar como falta. Vale na hora:
        o filtro roda toda vez que as faltas sao lidas, entao nao precisa
        reenviar a planilha."""
        try:
            funcoes = headcount_store.adicionar_funcao(nome)
        except ValueError as exc:
            return {"success": False, "message": str(exc)}
        return {"success": True, "funcoes": funcoes, **self._resumo_atual()}

    def remove_funcao(self, nome):
        funcoes = headcount_store.remover_funcao(nome)
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
            return {"success": False, "message": "Nao consegui ler o arquivo enviado."}

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
            return {"success": False, "message": str(exc)}
        except Exception as exc:  # noqa: BLE001 - arquivo fora do esperado
            return {"success": False, "message": f"Nao deu pra ler a planilha: {exc}"}
        finally:
            if caminho and os.path.exists(caminho):
                try:
                    os.remove(caminho)
                except OSError:
                    pass

        arquivo = headcount_store.salvar_faltas(nome_arquivo, len(bruto), linhas)
        return {"success": True, "resumo": arquivo["resumo"]}

    def clear_faltas(self):
        headcount_store.limpar_faltas()
        return {"success": True}

    def save_headcount_config(self, campos):
        return {"success": True, "config": headcount_store.salvar_config(campos or {})}

    # ---------------- Historico ----------------

    def get_report_history(self):
        return history_store.get_history()
