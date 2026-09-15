"""Historico local dos relatorios extraidos (aba "Relatorios"). Guardado
na mesma pasta de dados do Windows (%APPDATA%) usada por settings_store,
um arquivo por usuario/maquina.
"""

import json
import os
from datetime import datetime

APP_NAME = "ScoreCard"
MAX_ENTRIES = 200


def _history_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _history_path():
    return os.path.join(_history_dir(), "history.json")


def get_history():
    """Retorna a lista de extracoes, mais recente primeiro."""
    path = _history_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def add_entry(operation_label, file_path):
    entries = get_history()
    entries.insert(0, {
        "operation": operation_label,
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    entries = entries[:MAX_ENTRIES]
    with open(_history_path(), "w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)
