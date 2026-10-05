"""Monta a aba Horas Indiretas: filtros, cards, um quadro por semana e a
tabela atividade x semana.

So existe a visao por semana (nao ha resultado do mes): o filtro de mes
escolhe quais semanas aparecem — as que tem algum dia nele, como na aba
Inicio. A semana escolhida no filtro e a dos cards e dos graficos.

Em "Todas as Operacoes", a mesma Week de operacoes que fecham a semana
no domingo e na segunda e somada numa coluna so (igual ao Coverage).
"""

import datetime

import indiretas_store
from config.operations import OPERATIONS
from indicators import indiretas, periodos
from indicators.limits import LIMITE_INDIRETAS

TODAS = "todas"


def _rotulo_operacao(chave):
    return OPERATIONS.get(chave, {}).get("label", chave)


def _somar(semanas):
    """Uma semana a partir de varias (Todas as Operacoes): soma as horas
    e refaz os percentuais."""
    total = sum(s["horas_totais"] for s in semanas)
    por_atividade = {}
    for semana in semanas:
        for atividade in semana["atividades"]:
            nome = atividade["atividade"]
            por_atividade[nome] = por_atividade.get(nome, 0.0) + atividade["horas"]
    indiretas_total = sum(por_atividade.values())

    def dividir(parte, todo):
        return round(parte / todo, 6) if todo else None

    return {
        "horas_totais": round(total, 2),
        "horas_indiretas": round(indiretas_total, 2),
        "percentual": dividir(indiretas_total, total),
        "atividades": [{
            "atividade": nome,
            "horas": round(horas, 2),
            "percentual": dividir(horas, total),
            "percentual_indiretas": dividir(horas, indiretas_total),
        } for nome, horas in sorted(por_atividade.items(), key=lambda item: (-item[1], item[0]))],
        "parcial": any(s.get("parcial") for s in semanas),
        "extraido_em": max((s.get("extraido_em") or "" for s in semanas), default=""),
    }


def _guardado(operacao):
    """{operacao: {semana: {...}}} das operacoes da tela."""
    dados = indiretas_store.ler()
    if operacao == TODAS:
        return {op: semanas for op, semanas in dados.items() if op in OPERATIONS}
    return {operacao: dados.get(operacao, {})}


def _meses(guardado, hoje):
    meses = {hoje.strftime("%Y-%m")}
    for semanas in guardado.values():
        for chave in semanas:
            meses |= periodos.meses_das_semanas(chave)
    return sorted(meses, reverse=True)


def _semanas_do_mes(guardado, mes):
    grupos = {}
    for semanas in guardado.values():
        for chave, semana in semanas.items():
            if not periodos.semana_no_mes(chave, mes):
                continue
            grupo = f"{chave[:4]}-W{periodos.numero_da_semana(chave):02d}"
            grupos.setdefault(grupo, []).append((chave, semana))
    resultado = []
    for grupo, membros in sorted(grupos.items(), key=lambda item: min(c for c, _ in item[1])):
        primeira = min(c for c, _ in membros)
        titulo, datas = periodos.rotulo_semana(primeira)
        somada = _somar([s for _, s in membros])
        maior = somada["atividades"][0]["atividade"] if somada["atividades"] else None
        for atividade in somada["atividades"]:
            atividade["maior"] = atividade["atividade"] == maior
        resultado.append({
            "id": grupo,
            "rotulo": titulo,
            "datas": datas,
            "cor": indiretas.cor(somada["percentual"]),
            **somada,
        })
    return resultado


def _tabela(semanas):
    """Atividades nas linhas (da que mais pesa no mes para a que menos),
    semanas nas colunas."""
    no_mes = {}
    for semana in semanas:
        for atividade in semana["atividades"]:
            no_mes[atividade["atividade"]] = no_mes.get(atividade["atividade"], 0.0) + atividade["horas"]
    linhas = []
    for nome in sorted(no_mes, key=lambda n: (-no_mes[n], n)):
        celulas = {}
        for semana in semanas:
            achada = next((a for a in semana["atividades"] if a["atividade"] == nome), None)
            celulas[semana["id"]] = ({"horas": achada["horas"], "percentual": achada["percentual"]}
                                     if achada else None)
        linhas.append({"atividade": nome, "celulas": celulas})
    return {
        "linhas": linhas,
        "totais": {s["id"]: {"horas": s["horas_indiretas"], "percentual": s["percentual"],
                             "cor": s["cor"]} for s in semanas},
    }


def _ultima_extracao(semanas):
    quando = max((s.get("extraido_em") or "" for s in semanas), default="")
    if not quando:
        return None
    data = datetime.datetime.fromisoformat(quando).strftime("%d/%m %H:%M")
    quantas = len(semanas)
    return f"Extração de {data} · {quantas} semana{'s' if quantas != 1 else ''}"


def montar(operacao=None, mes=None, semana_id=None, hoje=None):
    hoje = hoje or datetime.date.today()
    operacao = operacao if operacao in OPERATIONS else TODAS
    guardado = _guardado(operacao)
    meses = _meses(guardado, hoje)
    mes = mes if mes in meses else hoje.strftime("%Y-%m")

    semanas = _semanas_do_mes(guardado, mes)
    ids = [s["id"] for s in semanas]
    # Sem semana escolhida, a mais recente extraida do mes.
    if semana_id not in ids:
        semana_id = ids[-1] if ids else None
    semana = next((s for s in semanas if s["id"] == semana_id), None)

    rotulo_operacao = "Todas as Operações" if operacao == TODAS else _rotulo_operacao(operacao)
    anteriores = [m for m in meses if m < mes and _semanas_do_mes(guardado, m)]
    return {
        "operacoes": ([{"key": TODAS, "label": "Todas as Operações"}]
                      + [{"key": k, "label": v["label"]} for k, v in OPERATIONS.items()]),
        "operacao": operacao,
        "operacao_rotulo": rotulo_operacao,
        "meses": [{"id": m, "rotulo": periodos.rotulo_mes_ano(m)} for m in meses],
        "mes": mes,
        "mes_rotulo": periodos.rotulo_mes_ano(mes),
        "mes_anterior": ({"id": anteriores[0], "rotulo": periodos.rotulo_mes_ano(anteriores[0])}
                         if anteriores else None),
        "semanas": semanas,
        "semana_id": semana_id,
        "periodos": [{"id": s["id"], "rotulo": f"{s['rotulo']} · {s['datas']}"} for s in semanas],
        "cards": {
            "operacao": rotulo_operacao,
            "periodo": semana["datas"] if semana else None,
            "periodo_nota": (f"{semana['rotulo']}{' · semana incompleta' if semana['parcial'] else ''}"
                             if semana else None),
            "horas_totais": semana["horas_totais"] if semana else None,
            "horas_indiretas": semana["horas_indiretas"] if semana else None,
            "atividades": len(semana["atividades"]) if semana else 0,
            "percentual": semana["percentual"] if semana else None,
            "cor": semana["cor"] if semana else None,
        },
        "tabela": _tabela(semanas),
        "limite": LIMITE_INDIRETAS,
        "ultima_extracao": _ultima_extracao(semanas),
    }
