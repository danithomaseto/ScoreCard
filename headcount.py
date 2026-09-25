"""Monta a tela de Headcount: filtros, cards, linhas e memoria.

Tudo o que e regra — quais periodos existem, que faltas caem em cada
um, quando uma linha esta abaixo da meta — fica aqui, no Python. O
JavaScript so desenha o que recebe.
"""

import datetime

from config.operations import OPERATIONS
import headcount_store
from indicators import presenteismo

TODAS = "todas"


def _iniciais(nome):
    partes = [p for p in (nome or "").split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


def _rotulo_mes(chave):
    ano, mes = chave.split("-")
    return f"{presenteismo.MESES[int(mes) - 1]}/{ano}"


def _meses_disponiveis(hoje, quantidade=3):
    meses = []
    ano, mes = hoje.year, hoje.month
    for _ in range(quantidade):
        chave = f"{ano:04d}-{mes:02d}"
        meses.append({"id": chave, "rotulo": _rotulo_mes(chave)})
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return meses


def _periodos(visualizacao, mes, hoje):
    """Os periodos da visualizacao escolhida, ja com dias uteis."""
    if visualizacao == "mes":
        return presenteismo.ciclos_folha(hoje=hoje)
    ano, numero = int(mes[:4]), int(mes[5:7])
    return presenteismo.semanas_do_mes(ano, numero, hoje=hoje)


def _periodo_selecionado(periodos, periodo_id):
    for periodo in periodos:
        if periodo["id"] == periodo_id:
            return periodo
    return None


def _intervalo(periodos, periodo_id):
    """(inicio, fim) do periodo escolhido, ou do conjunto todo quando a
    escolha e "todas as semanas"."""
    if periodo_id == TODAS or not periodo_id:
        if not periodos:
            return None, None
        return min(p["inicio"] for p in periodos), max(p["fim"] for p in periodos)
    periodo = _periodo_selecionado(periodos, periodo_id)
    if not periodo:
        return None, None
    return periodo["inicio"], periodo["fim"]


def _dias_do_periodo(periodos, periodo_id):
    if periodo_id == TODAS or not periodo_id:
        return sum(p["dias_uteis"] for p in periodos)
    periodo = _periodo_selecionado(periodos, periodo_id)
    return periodo["dias_uteis"] if periodo else 0


def _rotulo_periodo(visualizacao, periodos, periodo_id):
    if periodo_id == TODAS or not periodo_id:
        return "Todas as semanas do mes"
    periodo = _periodo_selecionado(periodos, periodo_id)
    if not periodo:
        return ""
    if visualizacao == "mes":
        return f"Folha ponto · {periodo['rotulo']}"
    return periodo["rotulo"]


def _plural(numero, singular, plural):
    return f"{numero} {singular if numero == 1 else plural}"


def _card_periodo(visualizacao, mes, periodos, periodo_id, dias):
    """Titulo curto e nota do card de periodo.

    O rotulo completo ("Folha ponto · 13/09/2026 → 12/10/2026") quebrava
    em tres linhas no card e esticava os cinco cards juntos; aqui ele e
    dividido entre o valor e a linha de nota.
    """
    uteis = _plural(dias, "dia util", "dias uteis")
    if visualizacao == "mes":
        periodo = _periodo_selecionado(periodos, periodo_id)
        if not periodo:
            return "-", ""
        return periodo["rotulo_curto"], f"Folha ponto · {periodo['status']} · {uteis}"
    if periodo_id == TODAS or not periodo_id:
        return _rotulo_mes(mes), f"Todas as semanas · {uteis}"
    periodo = _periodo_selecionado(periodos, periodo_id)
    if not periodo:
        return "-", ""
    inicio = datetime.date.fromisoformat(periodo["inicio"]).strftime("%d/%m")
    fim = datetime.date.fromisoformat(periodo["fim"]).strftime("%d/%m")
    return f"{inicio} a {fim}", f"S{periodo['numero']} · {uteis}"


def _usuarios_do_gestor(lancamentos, nome):
    return len({f["usuario"] for f in lancamentos
                if f["gestor"].casefold() == nome.casefold() and f["usuario"]})


def _faltas_do_gestor(lancamentos, nome, inicio, fim):
    return sum(
        f.get("dias", 1) for f in lancamentos
        if f["gestor"].casefold() == nome.casefold()
        and (not inicio or f["data"] >= inicio)
        and (not fim or f["data"] <= fim)
    )


def montar(operacao=TODAS, visualizacao="semanal", mes=None, periodo_id=None, hoje=None):
    """O estado inteiro da tela, pronto pra desenhar."""
    hoje = hoje or datetime.date.today()
    dados = headcount_store.ler()
    config = dados["config"]
    meta = config["meta"]
    lancamentos = (dados.get("arquivo") or {}).get("faltas", [])

    meses = _meses_disponiveis(hoje)
    mes = mes or meses[0]["id"]
    periodos = _periodos(visualizacao, mes, hoje)

    if visualizacao == "mes":
        padrao = next((p["id"] for p in periodos if p["status"] == "Em aberto"),
                      periodos[0]["id"] if periodos else None)
    else:
        padrao = TODAS
    if not periodo_id or not (periodo_id == TODAS
                              or _periodo_selecionado(periodos, periodo_id)):
        periodo_id = padrao

    inicio, fim = _intervalo(periodos, periodo_id)
    dias_periodo = _dias_do_periodo(periodos, periodo_id)
    rotulo = _rotulo_periodo(visualizacao, periodos, periodo_id)
    periodo_titulo, periodo_nota = _card_periodo(
        visualizacao, mes, periodos, periodo_id, dias_periodo)

    gestores = [g for g in dados["gestores"]
                if operacao in (TODAS, None) or g["operacao"] == operacao]

    linhas = []
    hc_total = faltas_total = 0
    horas_disponiveis = horas_perdidas = 0.0

    for gestor in sorted(gestores, key=lambda g: g["nome"].casefold()):
        hc = int(gestor.get("hc") or 0)
        dias = gestor.get("dias_uteis")
        dias = int(dias) if dias is not None else dias_periodo
        horas_dia = float(gestor.get("horas_dia") or config["horas_dia"])
        faltas = _faltas_do_gestor(lancamentos, gestor["nome"], inicio, fim)
        valor = presenteismo.calcular(hc, dias, horas_dia, faltas)

        hc_total += hc
        faltas_total += faltas
        horas_disponiveis += hc * dias * horas_dia
        horas_perdidas += faltas * horas_dia

        linhas.append({
            "id": gestor["id"],
            "gestor": gestor["nome"],
            "iniciais": _iniciais(gestor["nome"]),
            "usuarios": _usuarios_do_gestor(lancamentos, gestor["nome"]),
            "operacao": OPERATIONS.get(gestor["operacao"], {}).get(
                "label", gestor["operacao"]),
            "operacao_key": gestor["operacao"],
            "periodo": rotulo,
            "hc": hc,
            "dias_uteis": dias,
            "dias_do_periodo": dias_periodo,
            "horas_dia": horas_dia,
            "faltas": faltas,
            "presenteismo": valor,
            "abaixo_da_meta": valor is not None and valor < meta,
        })

    total = presenteismo.calcular(
        hc_total, dias_periodo, config["horas_dia"], faltas_total)
    if horas_disponiveis > 0:
        # Com gestores em jornadas diferentes, a conta do total e feita
        # por horas e nao pela media dos percentuais.
        total = round(1 - (horas_perdidas / horas_disponiveis), 6)

    return {
        "operacoes": ([{"key": TODAS, "label": "Todas as Operacoes"}]
                      + [{"key": k, "label": v["label"]} for k, v in OPERATIONS.items()]),
        "operacao": operacao or TODAS,
        "visualizacao": visualizacao,
        "meses": meses,
        "mes": mes,
        "periodos": ([{"id": TODAS, "rotulo": "Todas as semanas", "dias_uteis": dias_periodo}]
                     + periodos) if visualizacao == "semanal" else periodos,
        "periodo_id": periodo_id,
        "periodo_rotulo": rotulo,
        "cards": {
            "operacao": next((o["label"] for o in
                              [{"key": TODAS, "label": "Todas as Operacoes"}]
                              + [{"key": k, "label": v["label"]} for k, v in OPERATIONS.items()]
                              if o["key"] == (operacao or TODAS)), ""),
            "periodo": periodo_titulo,
            "periodo_nota": periodo_nota,
            "hc_total": hc_total,
            "faltas": faltas_total,
            "horas_perdidas": round(horas_perdidas, 2),
            "presenteismo": total,
            "dentro_da_meta": total is not None and total >= meta,
        },
        "linhas": linhas,
        "total": {
            "gestores": len(linhas),
            "hc": hc_total,
            "dias_uteis": dias_periodo,
            "horas_dia": config["horas_dia"],
            "faltas": faltas_total,
            "presenteismo": total,
        },
        "memoria": {
            "horas_disponiveis": round(horas_disponiveis, 2),
            "horas_perdidas": round(horas_perdidas, 2),
            "horas_efetivas": round(horas_disponiveis - horas_perdidas, 2),
            "presenteismo": total,
            "meta": meta,
        },
        "arquivo": _resumo_do_arquivo(dados.get("arquivo"), periodos, visualizacao, periodo_id),
        "funcoes": dados["funcoes"],
        "config": config,
        "meta": meta,
    }


def _resumo_do_arquivo(arquivo, periodos, visualizacao, periodo_id):
    """O card do arquivo importado, com os periodos que ele alimenta.

    Um arquivo so costuma cobrir varios periodos; mostrar quais evita a
    duvida de "sera que esse arquivo tem a semana que eu preciso?".
    """
    if not arquivo:
        return None

    lancamentos = arquivo.get("faltas", [])
    cobertura = []
    for periodo in periodos:
        dentro = [f for f in lancamentos
                  if periodo["inicio"] <= f["data"] <= periodo["fim"]]
        if not dentro and periodo["id"] != periodo_id:
            continue
        cobertura.append({
            "id": periodo["id"],
            "rotulo": periodo["rotulo"],
            "status": periodo.get("status", ""),
            "linhas": len(dentro),
            "dias": sum(f.get("dias", 1) for f in dentro),
            "selecionado": periodo["id"] == periodo_id,
        })

    return {
        "nome": arquivo["nome"],
        "tamanho": arquivo["tamanho"],
        "importado_em": arquivo["importado_em"],
        "resumo": arquivo["resumo"],
        "cobertura": cobertura,
        "previa": lancamentos[:5],
    }
