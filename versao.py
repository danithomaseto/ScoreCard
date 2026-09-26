"""Versao do app mostrada no rodape e no diagnostico.

O build grava versao.json (data e hora do build e o commit) junto do
app; rodando do codigo-fonte ele nao existe e a versao aparece como
"desenvolvimento". E o que responde "qual exe voce esta usando?" quando
alguem reporta um problema.
"""

import json
import os
import sys

ARQUIVO = "versao.json"


def _pasta_do_app():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def info():
    """{"versao": "2026.09.26", "build": "26/09/2026 14:30", "commit": "a1b2c3d"}."""
    try:
        with open(os.path.join(_pasta_do_app(), ARQUIVO), encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, ValueError):
        return {"versao": "desenvolvimento", "build": "", "commit": ""}
    return {
        "versao": dados.get("versao") or "?",
        "build": dados.get("build") or "",
        "commit": dados.get("commit") or "",
    }


def gerar(destino, agora=None, commit=""):
    """Chamado pelo build.spec: grava o versao.json que vai no pacote."""
    from datetime import datetime

    agora = agora or datetime.now()
    dados = {
        "versao": agora.strftime("%Y.%m.%d"),
        "build": agora.strftime("%d/%m/%Y %H:%M"),
        "commit": commit,
    }
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False)
    return dados
