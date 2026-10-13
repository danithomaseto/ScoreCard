"""Conserta semanas gravadas com o dia e o mes trocados.

Ate a V.01.1 a data da semana em texto era lida sempre como dia/mes.
Nas operacoes em que o Summary entrega a data no formato americano
(mes/dia, ex.: "9/6/26" = 6 de setembro), a semana 06/09 foi gravada
como 09/06 (junho) e a 04/10 como 10/04 (abril) — e esses meses
apareciam no filtro. Hoje o leitor entende as duas ordens
(indicators/datas.py); este reparo acerta o que ja estava gravado.

Como reconhecer uma semana trocada: o Summary comeca a semana no
domingo ou na segunda. Uma chave que cai em outro dia, e que com dia e
mes trocados cai no dia em que as outras semanas da operacao comecam,
foi lida ao contrario. Se a semana certa ja existe (extraida de novo
depois), fica a certa e a trocada sai.

Roda na abertura do app e so grava quando acha algo para consertar.
Semanas que eram dia > 12 em formato americano ("9/13/26") nao foram
gravadas na epoca: para elas, so extraindo o periodo de novo.
"""

import datetime
import logging

import arquivo_seguro
import coverage_store
import grupos_store
import indicators_store
import indiretas_store
from indicators.datas import INICIOS_DE_SEMANA

log = logging.getLogger("scorecard.reparo")


def _data(chave):
    try:
        return datetime.date.fromisoformat(chave)
    except (TypeError, ValueError):
        return None


def _destrocar(data):
    try:
        return datetime.date(data.year, data.day, data.month)
    except ValueError:
        return None


def consertar(periodos, prefixo=""):
    """Acerta as chaves de semana de um dicionario {prefixo + data: ...}
    no lugar. Devolve quantas chaves foram consertadas."""
    if not isinstance(periodos, dict):
        return 0
    datas = {chave: _data(chave[len(prefixo):]) for chave in periodos if chave.startswith(prefixo)}
    datas = {chave: data for chave, data in datas.items() if data}
    # O dia em que as semanas desta operacao comecam (domingo ou segunda).
    dias = {data.weekday() for data in datas.values() if data.weekday() in INICIOS_DE_SEMANA}
    alvo = dias or set(INICIOS_DE_SEMANA)

    consertadas = 0
    for chave, data in datas.items():
        if data.weekday() in INICIOS_DE_SEMANA:
            continue
        certa = _destrocar(data)
        if not certa or certa.weekday() not in alvo:
            continue
        valor = periodos.pop(chave)
        periodos.setdefault(prefixo + certa.isoformat(), valor)
        consertadas += 1
    return consertadas


def _indicadores():
    dados = indicators_store._ler()
    n = sum(consertar(por_periodo.get("week")) for por_periodo in dados.values()
            if isinstance(por_periodo, dict))
    if n:
        arquivo_seguro.gravar_json(indicators_store._store_path(), dados, compacto=True)
    return n


def _grupos():
    dados = grupos_store.ler()
    n = sum(consertar(periodos, "week:") for dimensao in grupos_store.DIMENSOES
            for periodos in dados.get(dimensao, {}).values())
    if n:
        arquivo_seguro.gravar_json(grupos_store._caminho(), dados, compacto=True)
    return n


def _coverage():
    dados = coverage_store.ler()
    n = sum(consertar(periodos, "week:") for parte in ("extracoes", "manuais", "sinergia")
            for periodos in dados.get(parte, {}).values())
    if n:
        arquivo_seguro.gravar_json(coverage_store._caminho(), dados, compacto=True)
    return n


def _indiretas():
    dados = indiretas_store.ler()
    n = sum(consertar(semanas) for semanas in dados.values())
    if n:
        arquivo_seguro.gravar_json(indiretas_store._caminho(), dados, compacto=True)
    return n


def reparar():
    """Conserta todos os arquivos. Nunca derruba a abertura do app."""
    total = 0
    for nome, passo in (("indicadores", _indicadores), ("grupos", _grupos),
                        ("coverage", _coverage), ("indiretas", _indiretas)):
        try:
            n = passo()
        except Exception:  # noqa: BLE001 - reparo e opcional; o app abre igual
            log.exception("não consegui conferir as semanas de %s", nome)
            continue
        if n:
            log.info("%d semana(s) com dia e mês trocados consertada(s) em %s", n, nome)
        total += n
    return total
