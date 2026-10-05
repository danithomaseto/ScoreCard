"""Horas indiretas guardadas, em %APPDATA%\\ScoreCard\\indiretas.json.

{operacao: {"2026-09-06": {horas_totais, horas_indiretas, percentual,
atividades, parcial, de, ate, extraido_em}}}

Uma extracao substitui as semanas que trouxe e mantem as outras: da para
extrair o mes aos poucos, semana a semana, sem perder o que ja estava.
"""

import json
import os
from datetime import datetime

import arquivo_seguro

APP_NAME = "ScoreCard"


def _caminho():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta = os.path.join(base, APP_NAME)
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "indiretas.json")


def ler():
    if not os.path.isfile(_caminho()):
        return {}
    try:
        with open(_caminho(), encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) else {}


def salvar(operacao, semanas, de=None, ate=None):
    """semanas e {chave da semana: indicators.indiretas.da_semana(...)},
    cada uma com "parcial" ja marcado."""
    dados = ler()
    da_operacao = dados.setdefault(operacao, {})
    agora = datetime.now().isoformat(timespec="seconds")
    for chave, semana in semanas.items():
        da_operacao[chave] = {**semana, "de": de, "ate": ate, "extraido_em": agora}
    arquivo_seguro.gravar_json(_caminho(), dados, compacto=True)


def da_operacao(operacao):
    return ler().get(operacao, {})
