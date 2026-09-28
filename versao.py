"""Versao do app mostrada no rodape e no diagnostico.

O numero segue o formato V.01.0: a cada atualizacao sobe o ultimo
digito (V.01.1, V.01.2 ... V.01.9) e depois vira a dezena (V.02.0). Ele
mora no arquivo VERSAO, na raiz do projeto, e sobe com
`python tools/subir_versao.py`.

O build grava versao.json com esse numero, a data e hora do build e o
commit; o app le dali. Rodando do codigo-fonte, le direto o VERSAO.
"""

import json
import os
import re
import sys

ARQUIVO = "versao.json"
ARQUIVO_DO_NUMERO = "VERSAO"
FORMATO = re.compile(r"^V\.(\d{2})\.(\d)$")


def _pasta_do_app():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def numero(pasta=None):
    """O numero guardado no arquivo VERSAO (ex.: "V.01.0")."""
    caminho = os.path.join(pasta or os.path.dirname(os.path.abspath(__file__)), ARQUIVO_DO_NUMERO)
    try:
        with open(caminho, encoding="utf-8") as fh:
            texto = fh.read().strip()
    except OSError:
        return "V.00.0"
    return texto if FORMATO.match(texto) else "V.00.0"


def proxima(atual):
    """V.01.0 -> V.01.1 ... V.01.9 -> V.02.0."""
    casou = FORMATO.match(atual)
    if not casou:
        raise ValueError(f"Versao fora do formato V.01.0: {atual!r}")
    dezena, unidade = int(casou.group(1)), int(casou.group(2))
    if unidade < 9:
        unidade += 1
    else:
        dezena, unidade = dezena + 1, 0
    return f"V.{dezena:02d}.{unidade}"


def info():
    """{"versao": "V.01.0", "build": "26/09/2026 14:30", "commit": "a1b2c3d"}."""
    try:
        with open(os.path.join(_pasta_do_app(), ARQUIVO), encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, ValueError):
        return {"versao": numero(), "build": "", "commit": ""}
    return {
        "versao": dados.get("versao") or "?",
        "build": dados.get("build") or "",
        "commit": dados.get("commit") or "",
    }


def gerar(destino, agora=None, commit="", versao=None):
    """Chamado pelo build.spec: grava o versao.json que vai no pacote."""
    from datetime import datetime

    agora = agora or datetime.now()
    dados = {
        "versao": versao or numero(),
        "build": agora.strftime("%d/%m/%Y %H:%M"),
        "commit": commit,
    }
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False)
    return dados
