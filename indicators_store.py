"""Indicadores calculados, guardados localmente.

Mesmo padrao do settings_store e do history_store: um arquivo por
usuario/maquina em %APPDATA%\\ScoreCard.

Por que guardar o resultado em vez de recalcular do arquivo: a extracao
apaga o relatorio anterior da mesma operacao (de proposito, pra pasta
do SharePoint nao acumular lixo). Lendo os arquivos da pasta, o
historico das semanas anteriores iria embora junto.

Formato: operacao -> periodo ("week"/"month"/"peak") -> chave -> resultado.
"peak" e a hora direta dos dias de pico, por mes (indicators/pico.py).
A chave da semana e a data que vem no arquivo ("2026-08-30"); a do mes
e o proprio mes ("2026-09"), que vem dos parametros da extracao porque
o export mensal nao traz coluna de data.
"""

import json
import os
from datetime import datetime

from indicators.limits import MANUAIS
from indicators.weekly import calcular_cubo

import arquivo_seguro

APP_NAME = "ScoreCard"


def _store_path():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return os.path.join(path, "indicators.json")


def _ler():
    path = _store_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            dados = json.load(fh)
            return dados if isinstance(dados, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _gravar(dados):
    arquivo_seguro.gravar_json(_store_path(), dados)


def get_indicators(operation_key=None):
    """Tudo o que esta guardado, ou so de uma operacao."""
    dados = _ler()
    if operation_key is None:
        return dados
    return dados.get(operation_key, {})


def salvar_extracao(operation_key, periodo, resultados, meta=None):
    """Grava o que veio de uma extracao.

    resultados e {chave: totais}. A substituicao e **parcial, por
    origem do dado**: reescreve o que sai do export e preserva o
    presenteismo e o coverage, que sao digitados a mao e nao estao no
    relatorio. Sem essa regra, reextrair uma semana pra corrigir um
    numero apagaria calado os dois e derrubaria o cubo junto.
    """
    dados = _ler()
    por_periodo = dados.setdefault(operation_key, {}).setdefault(periodo, {})
    agora = datetime.now().isoformat(timespec="seconds")

    for chave, totais in resultados.items():
        anterior = por_periodo.get(chave, {})
        entrada = {**anterior, **totais, **(meta or {})}

        for campo in MANUAIS:
            if anterior.get(campo) is not None:
                entrada[campo] = anterior[campo]

        entrada["cubo"] = calcular_cubo(
            entrada.get("efetividade"),
            entrada.get("hora_direta"),
            entrada.get("presenteismo"),
        )
        entrada["extraido_em"] = agora
        por_periodo[chave] = entrada

    _gravar(dados)
    return por_periodo


def salvar_manual(operation_key, periodo, chave, valores):
    """Grava os indicadores digitados a mao (presenteismo, coverage).

    Aceita uma chave que ainda nao existe: da pra preencher antes da
    extracao, e os calculados ficam vazios ate ela chegar. Os dois
    caminhos funcionam em qualquer ordem.
    """
    dados = _ler()
    por_periodo = dados.setdefault(operation_key, {}).setdefault(periodo, {})
    entrada = por_periodo.get(chave, {})

    for campo in MANUAIS:
        if campo in valores:
            entrada[campo] = valores[campo]

    entrada["cubo"] = calcular_cubo(
        entrada.get("efetividade"),
        entrada.get("hora_direta"),
        entrada.get("presenteismo"),
    )
    entrada["informado_em"] = datetime.now().isoformat(timespec="seconds")
    por_periodo[chave] = entrada

    _gravar(dados)
    return entrada
