"""Metodos expostos para a interface (ui/app.js) via
pywebview.api.<metodo>(...). Cada metodo publico aqui vira uma funcao
chamavel do JavaScript.
"""

import json
import os
import subprocess
import sys

import webview

from automation import generic
from config.operations import GROUP_BY_OPTIONS, OPERATIONS
import history_store
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
            "status": "success" if result.get("success") else "error",
            "duration_seconds": result.get("duration_seconds"),
            "file_path": result.get("file_path"),
            "message": result.get("message"),
        })

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
        self._record_history(operation_key, result)
        return result

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

        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"
        base_dir = settings_store.get_sharepoint_folder()
        total = len(operation_keys)
        succeeded = 0

        for index, operation_key in enumerate(operation_keys):
            label = OPERATIONS[operation_key]["label"]

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
            self._record_history(operation_key, result)

            ok = bool(result.get("success"))
            if ok:
                succeeded += 1
            self._emit_js("updateMultiProgress", {
                "index": index,
                "total": total,
                "operation_label": label,
                "step": result.get("message", ""),
                "status": "success" if ok else "error",
            })

        failed = total - succeeded
        if failed:
            message = f"{succeeded} de {total} extracoes concluidas, {failed} com falha."
        else:
            message = f"{succeeded} de {total} extracoes concluidas."
        return {
            "success": failed == 0,
            "message": message,
            "succeeded": succeeded,
            "failed": failed,
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

    # ---------------- Historico ----------------

    def get_report_history(self):
        return history_store.get_history()
