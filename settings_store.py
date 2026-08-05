"""Configuracoes persistidas localmente (fora do codigo-fonte): hoje, so
o caminho da pasta do SharePoint/OneDrive onde os relatorios sao salvos.
Cada usuario que roda o aplicativo tem o seu proprio arquivo, guardado
na pasta de dados do Windows (%APPDATA%).
"""

import json
import os

APP_NAME = "ScoreCard"


def _settings_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _settings_path():
    return os.path.join(_settings_dir(), "settings.json")


def get_settings():
    path = _settings_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(data):
    with open(_settings_path(), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)


def get_sharepoint_folder():
    return get_settings().get("sharepoint_base_dir")


def set_sharepoint_folder(folder):
    settings = get_settings()
    settings["sharepoint_base_dir"] = folder
    save_settings(settings)
