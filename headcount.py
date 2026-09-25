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
    arquivo = headcount_store.arquivo(dados)
    lancamentos = arquivo["faltas"] if arquivo else []

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
        "arquivo": _resumo_do_arquivo(arquivo, periodos, visualizacao, periodo_id),
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

    janela = cobertura_do_arquivo(arquivo)
    return {
        "nome": arquivo["nome"],
        "tamanho": arquivo["tamanho"],
        "importado_em": arquivo["importado_em"],
        "resumo": arquivo["resumo"],
        "cobertura": cobertura,
        "cobre_de": janela[0].isoformat() if janela else None,
        "cobre_ate": janela[1].isoformat() if janela else None,
        "previa": lancamentos[:5],
    }


# ---------------------------------------------------------------
# Presenteismo de qualquer intervalo, para a aba Inicio
# ---------------------------------------------------------------
# A aba Inicio nao le um valor gravado: ela calcula o presenteismo na
# hora, a partir do quadro e das faltas. Assim qualquer mudanca — um
# arquivo novo, um HC corrigido, um gestor ou uma funcao a mais — ja
# aparece la sem precisar clicar em nada, e nao sobra numero antigo
# preso no indicador.

# Quanto depois do dia 13 a primeira linha do arquivo pode cair e ainda
# assim o arquivo ser tratado como "desde o inicio da folha".
FOLGA_INICIO_DA_FOLHA = 7


def cobertura_do_arquivo(arquivo):
    """(inicio, fim) do periodo que a planilha cobre, ou None.

    O arquivo so tem linha em dia com ausencia, entao a cobertura e
    deduzida:

    - **inicio**: a planilha e tirada "do inicio da folha ate agora".
      Se a primeira data cai ate uma semana depois de um dia 13, o
      arquivo e tratado como comecando nesse dia 13 — ninguem ter
      faltado nos primeiros dias nao quer dizer que eles ficaram de
      fora. Mais longe que isso, vale a primeira data mesmo: melhor um
      periodo sem numero do que um 100% inventado.
    - **fim**: o dia em que o arquivo foi importado (ou a ultima data,
      se for depois).
    """
    if not arquivo:
        return None
    resumo = arquivo.get("resumo") or {}
    primeira = resumo.get("data_inicio")
    ultima = resumo.get("data_fim")
    if not primeira:
        datas = [f["data"] for f in arquivo.get("faltas", []) if f.get("data")]
        if not datas:
            return None
        primeira, ultima = min(datas), max(datas)

    primeira = datetime.date.fromisoformat(primeira)
    ciclo = datetime.date.fromisoformat(presenteismo.ciclo_de(primeira.isoformat()))
    inicio = ciclo if (primeira - ciclo).days <= FOLGA_INICIO_DA_FOLHA else primeira

    importado = datetime.date.fromisoformat(arquivo["importado_em"][:10])
    fim = max(importado, datetime.date.fromisoformat(ultima)) if ultima else importado
    return inicio, fim


def presenteismo_do_intervalo(operacao, inicio, fim, hoje=None, dados=None):
    """Presenteismo de uma operacao entre duas datas, ou None.

    None quando nao da pra afirmar nada: sem gestor com HC, sem arquivo,
    ou com dia util do intervalo fora do que a planilha cobre. Um
    periodo que ainda esta correndo e calculado ate onde ha dado — igual
    ao ciclo "Em aberto" da tela de Headcount.
    """
    hoje = hoje or datetime.date.today()
    dados = dados or headcount_store.ler()
    arquivo = headcount_store.arquivo(dados)
    janela = cobertura_do_arquivo(arquivo)
    if not janela:
        return None
    cobre_de, cobre_ate = janela

    if isinstance(inicio, str):
        inicio = datetime.date.fromisoformat(inicio)
    if isinstance(fim, str):
        fim = datetime.date.fromisoformat(fim)

    # Dia util antes do que a planilha cobre: falta pode ter acontecido
    # ali sem aparecer. Nao da pra fechar o periodo.
    if inicio < cobre_de and presenteismo.dias_uteis(inicio, cobre_de - datetime.timedelta(days=1)) > 0:
        return None

    em_andamento = inicio <= hoje <= fim
    ate = min(fim, hoje, cobre_ate)
    if ate < inicio:
        return None
    # Periodo ja encerrado precisa estar coberto ate o fim.
    if not em_andamento and ate < fim and             presenteismo.dias_uteis(ate + datetime.timedelta(days=1), min(fim, hoje)) > 0:
        return None

    dias = presenteismo.dias_uteis(max(inicio, cobre_de), ate)
    if dias <= 0:
        return None

    gestores = [g for g in dados["gestores"]
                if g["operacao"] == operacao and (g.get("hc") or 0) > 0]
    if not gestores:
        return None

    de, ate_iso = max(inicio, cobre_de).isoformat(), ate.isoformat()
    disponiveis = perdidas = 0.0
    for gestor in gestores:
        horas_dia = float(gestor.get("horas_dia") or dados["config"]["horas_dia"])
        faltas = _faltas_do_gestor(arquivo["faltas"], gestor["nome"], de, ate_iso)
        disponiveis += int(gestor["hc"]) * dias * horas_dia
        perdidas += faltas * horas_dia

    if disponiveis <= 0:
        return None
    return round(1 - perdidas / disponiveis, 6)


def presenteismo_por_periodo(operacao, hoje=None):
    """Tudo que da pra afirmar para uma operacao, nos periodos da aba
    Inicio: {"week": {segunda: {...}}, "month": {"2026-09": {...}}}.

    - Semana: segunda a domingo, a mesma semana do Summary, chave na
      segunda-feira. Nao e a semana cortada no mes da tela de Headcount.
    - Mes: o ciclo da folha ponto que comeca no dia 13 desse mes.
    """
    hoje = hoje or datetime.date.today()
    dados = headcount_store.ler()
    arquivo = headcount_store.arquivo(dados)
    janela = cobertura_do_arquivo(arquivo)
    resultado = {"week": {}, "month": {}}
    if not janela:
        return resultado
    cobre_de, cobre_ate = janela
    limite = min(cobre_ate, hoje)

    segunda = cobre_de - datetime.timedelta(days=cobre_de.weekday())
    while segunda <= limite:
        domingo = segunda + datetime.timedelta(days=6)
        valor = presenteismo_do_intervalo(operacao, segunda, domingo, hoje=hoje, dados=dados)
        if valor is not None:
            resultado["week"][segunda.isoformat()] = {
                "presenteismo": valor,
                "parcial": segunda <= hoje <= domingo,
            }
        segunda += datetime.timedelta(days=7)

    for ciclo in presenteismo.ciclos_folha(hoje=hoje, anteriores=24):
        inicio = datetime.date.fromisoformat(ciclo["inicio"])
        fim = datetime.date.fromisoformat(ciclo["fim"])
        if fim < cobre_de or inicio > limite:
            continue
        valor = presenteismo_do_intervalo(operacao, inicio, fim, hoje=hoje, dados=dados)
        if valor is not None:
            resultado["month"][ciclo["mes_referencia"]] = {
                "presenteismo": valor,
                "de": ciclo["inicio"],
                "ate": ciclo["fim"],
                "em_aberto": ciclo["status"] == "Em aberto",
            }
    return resultado
