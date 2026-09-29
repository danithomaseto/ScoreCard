"""Monta a aba Coverage: filtros, cards, uma linha por usuario e o total.

Os periodos sao os que vieram do Summary (a mesma regra da aba Inicio):
as semanas da extracao Week, na visao Semanal, e o mes da extracao
Month, no Resultado do Mes. Periodo sem extracao nao aparece.
"""

import datetime

import coverage_store
from config.operations import OPERATIONS, escala_espanhola
from indicators import coverage, limits, periodos, presenteismo

TODAS = "todas"


def _dias_uteis(operacao, periodo, chave_periodo, de=None, ate=None):
    """Dias uteis que o periodo deveria ter, dentro do que foi extraido:
    a semana (ou o mes) cortada nas datas da extracao, se ela foi parcial."""
    if periodo == "week":
        inicio = datetime.date.fromisoformat(chave_periodo)
        fim = inicio + datetime.timedelta(days=6)
    else:
        inicio, fim = periodos._limites_do_mes(chave_periodo)
    if de:
        inicio = max(inicio, datetime.date.fromisoformat(de))
    if ate:
        fim = min(fim, datetime.date.fromisoformat(ate))
    return presenteismo.dias_uteis(inicio, fim, escala_espanhola(operacao))


def _rotulo_operacao(chave):
    return OPERATIONS.get(chave, {}).get("label", chave)


def _linhas(operacao, periodo, chave_periodo, extracao):
    dias = _dias_uteis(operacao, periodo, chave_periodo, extracao.get("de"), extracao.get("ate"))
    digitados = coverage_store.manuais(operacao, coverage_store.chave(periodo, chave_periodo))
    linhas = []
    for usuario, horas in extracao["usuarios"].items():
        linha = coverage.linha(usuario, horas, digitados.get(usuario), dias)
        linha.update(operacao=_rotulo_operacao(operacao), operacao_key=operacao,
                     chave_periodo=coverage_store.chave(periodo, chave_periodo),
                     cor=limits.cor("coverage", linha["coverage"]))
        linhas.append(linha)
    return linhas


def total_do_periodo(operacao, periodo, chave_periodo):
    """Coverage total de uma operacao num periodo (para a aba Inicio), ou
    None se esse periodo nao tem extracao."""
    extracao = coverage_store.extracoes(operacao).get(operacao, {}).get(
        coverage_store.chave(periodo, chave_periodo))
    if not extracao:
        return None
    chave_guardada = coverage_store.chave(periodo, chave_periodo)
    return coverage.total(_linhas(operacao, periodo, chave_periodo, extracao),
                          coverage_store.sinergia(operacao, chave_guardada))["coverage"]


def _grupos_de_semanas(extracoes, mes):
    """As semanas extraidas que tem dia no mes, agrupadas pelo numero: a
    Week 39 de uma operacao que fecha no domingo (20/09) e a de outra que
    fecha na segunda (21/09) sao a mesma semana na tela."""
    grupos = {}
    for operacao, guardado in extracoes.items():
        for chave_guardada in guardado:
            tipo, chave_periodo = chave_guardada.split(":", 1)
            if tipo != "week" or not periodos.semana_no_mes(chave_periodo, mes):
                continue
            grupo = f"{chave_periodo[:4]}-W{periodos.numero_da_semana(chave_periodo):02d}"
            grupos.setdefault(grupo, []).append((operacao, chave_periodo))
    resultado = []
    for grupo, membros in grupos.items():
        primeira = min(c for _, c in membros)
        titulo, datas = periodos.rotulo_semana(primeira)
        resultado.append({"id": grupo, "rotulo": f"{titulo} · {datas}", "inicio": primeira,
                          "membros": membros})
    return sorted(resultado, key=lambda g: g["inicio"])


def _meses(extracoes, hoje):
    meses = {hoje.strftime("%Y-%m")}
    for guardado in extracoes.values():
        for chave_guardada in guardado:
            tipo, chave_periodo = chave_guardada.split(":", 1)
            meses |= periodos.meses_das_semanas(chave_periodo) if tipo == "week" else {chave_periodo}
    return [{"id": m, "rotulo": periodos.rotulo_mes_ano(m)} for m in sorted(meses, reverse=True)]


def montar(operacao=TODAS, visualizacao="semanal", mes=None, periodo_id=None, hoje=None):
    hoje = hoje or datetime.date.today()
    operacao = operacao or TODAS
    extracoes = coverage_store.extracoes(None if operacao == TODAS else operacao)
    meses = _meses(extracoes, hoje)
    mes = mes if mes in [m["id"] for m in meses] else hoje.strftime("%Y-%m")

    linhas = []
    if visualizacao == "mes":
        grupos = []
        periodo_id = mes
        for op, guardado in extracoes.items():
            extracao = guardado.get(coverage_store.chave("month", mes))
            if extracao:
                linhas += _linhas(op, "month", mes, extracao)
        titulo_periodo = periodos.rotulo_mes_ano(mes)
        de_ate = [e for g in extracoes.values() if (e := g.get(coverage_store.chave("month", mes)))]
        nota_periodo = "Extração Month"
        if de_ate and de_ate[0].get("de") and de_ate[0].get("ate"):
            de = datetime.date.fromisoformat(de_ate[0]["de"]).strftime("%d/%m")
            ate = datetime.date.fromisoformat(de_ate[0]["ate"]).strftime("%d/%m")
            nota_periodo = f"Extração Month · {de} a {ate}"
    else:
        grupos = _grupos_de_semanas(extracoes, mes)
        ids = [g["id"] for g in grupos]
        # Sem semana escolhida, a mais recente extraida do mes.
        if periodo_id not in ids:
            periodo_id = ids[-1] if ids else None
        grupo = next((g for g in grupos if g["id"] == periodo_id), None)
        for op, chave_periodo in (grupo["membros"] if grupo else []):
            linhas += _linhas(op, "week", chave_periodo, extracoes[op][coverage_store.chave("week", chave_periodo)])
        titulo_periodo = grupo["rotulo"].split(" · ")[1] if grupo else "-"
        nota_periodo = f"{grupo['rotulo'].split(' · ')[0]} · extração Week" if grupo else ""

    linhas.sort(key=lambda l: (l["operacao"].casefold(), l["usuario"].casefold()))
    # Sinergia da operacao: soma das operacoes na tela. So da pra digitar
    # com uma operacao so escolhida (a sinergia e de uma operacao).
    periodos_na_tela = sorted({(l["operacao_key"], l["chave_periodo"]) for l in linhas})
    sinergia_operacao = {"cedida": 0.0, "recebida": 0.0}
    for op, chave_guardada in periodos_na_tela:
        for campo, valor in coverage_store.sinergia(op, chave_guardada).items():
            sinergia_operacao[campo] += valor
    soma = coverage.total(linhas, sinergia_operacao)
    uma_operacao = operacao != TODAS and len(periodos_na_tela) == 1
    soma["sinergia_editavel"] = uma_operacao
    soma["chave_periodo"] = periodos_na_tela[0][1] if uma_operacao else None
    soma["cor"] = limits.cor("coverage", soma["coverage"])
    rotulo_operacao = "Todas as Operações" if operacao == TODAS else _rotulo_operacao(operacao)
    return {
        "operacoes": ([{"key": TODAS, "label": "Todas as Operações"}]
                      + [{"key": k, "label": v["label"]} for k, v in OPERATIONS.items()]),
        "operacao": operacao,
        "visualizacao": visualizacao,
        "meses": meses,
        "mes": mes,
        "periodos": [{"id": g["id"], "rotulo": g["rotulo"]} for g in grupos],
        "periodo_id": periodo_id,
        "linhas": linhas,
        "total": soma,
        "cards": {
            "operacao": rotulo_operacao,
            "periodo": titulo_periodo,
            "periodo_nota": nota_periodo,
            "lms": soma["lms"],
            "metrics": soma["metrics"],
            "coverage": soma["coverage"],
        },
        "horas_padrao": coverage.HORAS_PADRAO,
    }
