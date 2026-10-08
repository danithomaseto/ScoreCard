"""Resultados por gestor e por turno, em %APPDATA%\\ScoreCard\\grupos.json.

{"gestor": {operacao: {"week:2026-09-06": {"grupos": {nome: {...}},
de, ate, parcial, extraido_em}, "month:2026-09": {...}}}, "turno": {...}}

O nome de cada grupo e o da planilha (coluna B), sem mudar nada. Uma
extracao substitui os periodos que trouxe e mantem os outros, como nas
outras abas: da para extrair o mes aos poucos, semana a semana.
"""

import json
import os
from datetime import datetime

import arquivo_seguro

APP_NAME = "ScoreCard"
DIMENSOES = ("gestor", "turno")


def _caminho():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta = os.path.join(base, APP_NAME)
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "grupos.json")


def ler():
    dados = {}
    if os.path.isfile(_caminho()):
        try:
            with open(_caminho(), encoding="utf-8") as fh:
                lido = json.load(fh)
                dados = lido if isinstance(lido, dict) else {}
        except (OSError, ValueError):
            dados = {}
    for dimensao in DIMENSOES:
        dados.setdefault(dimensao, {})
    return dados


def chave(periodo, chave_periodo):
    """"week:2026-09-06" ou "month:2026-09" (o mesmo do Coverage)."""
    return f"{periodo}:{chave_periodo}"


def salvar(dimensao, operacao, periodo, por_chave, de=None, ate=None, parciais=None):
    """por_chave e {chave do periodo: {grupo: totais}}; parciais diz quais
    semanas foram cortadas pelas datas da extracao."""
    if dimensao not in DIMENSOES:
        raise ValueError("Dimensão inválida.")
    dados = ler()
    da_operacao = dados[dimensao].setdefault(operacao, {})
    agora = datetime.now().isoformat(timespec="seconds")
    for chave_periodo, grupos in por_chave.items():
        da_operacao[chave(periodo, chave_periodo)] = {
            "grupos": grupos,
            "de": de,
            "ate": ate,
            "parcial": bool((parciais or {}).get(chave_periodo)),
            "extraido_em": agora,
        }
    arquivo_seguro.gravar_json(_caminho(), dados, compacto=True)


def da_operacao(dimensao, operacao):
    """{"week:...": {...}, "month:...": {...}} de uma operacao."""
    return ler().get(dimensao, {}).get(operacao, {})
