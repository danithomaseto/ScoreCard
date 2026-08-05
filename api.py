"""Metodos expostos para a interface (ui/app.js) via
pywebview.api.<metodo>(...). Cada metodo publico aqui vira uma funcao
chamavel do JavaScript.
"""

import json
import os

import webview

from automation import generic
from config.operations import OPERATIONS
import settings_store


class Api:
    def __init__(self):
        self._window = None
        self._username = None
        self._password = None

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

    def run_extraction(self, operation_key):
        if not self.is_logged_in():
            return {"success": False, "message": "Faca login antes de executar."}

        if operation_key not in OPERATIONS:
            return {"success": False, "message": "Operacao invalida."}

        folder_check = self.validate_sharepoint_folder()
        if not folder_check["valid"]:
            return {"success": False, "message": folder_check["message"]}

        # SCORECARD_HEADLESS=0 mostra o navegador de verdade, fazendo a
        # automacao na tela — util pra descobrir em qual etapa exata algo
        # trava ou demora, ja que o .exe empacotado nao mostra log nenhum.
        headless = os.environ.get("SCORECARD_HEADLESS", "1") != "0"

        def on_progress(step):
            if not self._window:
                return
            # json.dumps escapa a string com seguranca pra virar um
            # literal valido de JS (aspas, barras, acentos, etc.)
            js_text = json.dumps(step)
            self._window.evaluate_js(
                f"window.updateProgress && window.updateProgress({js_text})"
            )

        result = generic.run(
            operation_key,
            base_dir=folder_check["folder"],
            headless=headless,
            username=self._username,
            password=self._password,
            on_progress=on_progress,
        )
        return result
