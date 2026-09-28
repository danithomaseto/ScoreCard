"""Monta a tela de Headcount: filtros, cards, linhas e memoria.

Tudo o que e regra — quais periodos existem, que faltas caem em cada
um, quando uma linha esta abaixo da meta — fica aqui, no Python. O
JavaScript so desenha o que recebe.
"""

import datetime

from config.operations import OPERATIONS, escala_espanhola
import headcount_store
from indicators import periodos as rotulos
from indicators import presenteismo

TODAS = "todas"

# De onde vem as faltas. A planilha de ausencias (ABS) fica desligada
# por enquanto — melhoria futura —, e as faltas sao digitadas na tela,
# por gestor e por periodo (semana do mes ou ciclo da folha). O codigo
# da planilha continua aqui: ligar de novo e trocar para True.
FALTAS_DA_PLANILHA = False


def _faltas_lancadas(gestor, periodo_ids):
    """Soma das faltas digitadas para um gestor nos periodos pedidos.
    Periodo sem lancamento conta como zero falta, igual a tela mostra."""
    quadro = gestor.get("quadro") or {}
    return sum(int(quadro.get(p, {}).get("faltas", 0)) for p in periodo_ids)


def _mesmo_tipo(a, b):
    """Semana do mes ("2026-09-S2") ou ciclo da folha ("2026-09-13")."""
    return ("-S" in a) == ("-S" in b)


def _herdado(gestor, periodo_id, campo):
    """(valor, de onde veio) do ultimo periodo anterior, do mesmo tipo,
    com esse campo digitado."""
    quadro = gestor.get("quadro") or {}
    anteriores = sorted(p for p, v in quadro.items()
                        if p < periodo_id and _mesmo_tipo(p, periodo_id) and campo in v)
    if anteriores:
        return quadro[anteriores[-1]][campo], anteriores[-1]
    return None, None


def quadro_do_periodo(gestor, periodo_id, dias_do_calendario, config):
    """HC, dias uteis, horas/dia e faltas de um gestor numa semana ou num
    ciclo, e a origem de cada um.

    - HC e horas/dia: o digitado no periodo; senao o ultimo digitado numa
      semana (ou ciclo) anterior; senao o do cadastro do gestor.
    - Dias uteis: o digitado; senao o do calendario do periodo.
    - Faltas: o digitado; senao zero.
    """
    proprio = (gestor.get("quadro") or {}).get(periodo_id, {})

    def herdavel(campo, cadastro):
        if campo in proprio:
            return proprio[campo], "digitado", None
        valor, origem = _herdado(gestor, periodo_id, campo)
        if valor is not None:
            return valor, "herdado", origem
        return cadastro, "cadastro", None

    hc, hc_origem, hc_de = herdavel("hc", int(gestor.get("hc") or 0))
    horas, horas_origem, horas_de = herdavel(
        "horas_dia", float(gestor.get("horas_dia") or config["horas_dia"]))
    if "dias_uteis" in proprio:
        dias, dias_origem = proprio["dias_uteis"], "digitado"
    else:
        dias, dias_origem = dias_do_calendario, "calendario"
    return {
        "hc": int(hc), "hc_origem": hc_origem, "hc_de": hc_de,
        "dias_uteis": int(dias), "dias_origem": dias_origem,
        "horas_dia": float(horas), "horas_origem": horas_origem, "horas_de": horas_de,
        "faltas": int(proprio.get("faltas", 0)),
    }


def _rotulo_semana_do_mes(semana):
    """"Week 37 · 07/09 a 13/09": o numero e o da semana do Summary (a da
    aba Inicio) que contem essa semana do mes."""
    inicio = datetime.date.fromisoformat(semana["inicio"])
    segunda = inicio - datetime.timedelta(days=inicio.weekday())
    fim = datetime.date.fromisoformat(semana["fim"])
    return (f"Week {rotulos.numero_da_semana(segunda.isoformat())} · "
            f"{inicio.strftime('%d/%m')} a {fim.strftime('%d/%m')}")


def _semana_padrao(periodos, hoje):
    """A ultima semana ja encerrada do mes; se nenhuma encerrou ainda, a
    que esta correndo; senao a primeira."""
    encerradas = [p for p in periodos if p["fim"] < hoje.isoformat()]
    if encerradas:
        return encerradas[-1]["id"]
    correndo = [p for p in periodos if p["inicio"] <= hoje.isoformat() <= p["fim"]]
    return (correndo or periodos)[0]["id"] if periodos else None


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


def _periodos(visualizacao, mes, hoje, escala=False):
    """Os periodos da visualizacao escolhida, ja com dias uteis (na
    escala espanhola, contando os dois ultimos sabados do mes)."""
    if visualizacao == "mes":
        return presenteismo.ciclos_folha(hoje=hoje, escala_espanhola=escala)
    ano, numero = int(mes[:4]), int(mes[5:7])
    semanas = presenteismo.semanas_do_mes(ano, numero, hoje=hoje, escala_espanhola=escala)
    for semana in semanas:
        semana["rotulo"] = _rotulo_semana_do_mes(semana)
    return semanas


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
    return f"{inicio} a {fim}", f"{periodo['rotulo'].split(' · ')[0]} · {uteis}"


def _por_gestor(lancamentos):
    """As faltas agrupadas pelo nome do gestor (sem diferenciar
    maiusculas), feito uma vez: sem isso cada gestor varria a planilha
    inteira, e com dezenas de gestores e milhares de linhas a tela
    demorava."""
    indice = {}
    for falta in lancamentos:
        indice.setdefault(falta["gestor"].casefold(), []).append(falta)
    return indice


def _do_gestor(lancamentos, nome):
    if isinstance(lancamentos, dict):
        return lancamentos.get(nome.casefold(), [])
    return [f for f in lancamentos if f["gestor"].casefold() == nome.casefold()]


def _usuarios_do_gestor(lancamentos, nome):
    return len({f["usuario"] for f in _do_gestor(lancamentos, nome) if f["usuario"]})


def _faltas_do_gestor(lancamentos, nome, inicio, fim):
    return sum(
        f.get("dias", 1) for f in _do_gestor(lancamentos, nome)
        if (not inicio or f["data"] >= inicio)
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
    faltas_por_gestor = _por_gestor(lancamentos)

    meses = _meses_disponiveis(hoje)
    mes = mes or meses[0]["id"]
    # A tela mostra os dias uteis da escala da operacao filtrada. Com
    # "Todas as Operacoes" as escalas se misturam: a tela mostra a
    # normal, e cada gestor usa a da operacao dele (logo abaixo).
    escala_da_tela = escala_espanhola(operacao)
    periodos = _periodos(visualizacao, mes, hoje, escala_da_tela)

    if visualizacao == "mes":
        padrao = next((p["id"] for p in periodos if p["status"] == "Em aberto"),
                      periodos[0]["id"] if periodos else None)
    else:
        padrao = _semana_padrao(periodos, hoje)
    # "Todas as semanas" so existe no caminho da planilha: com o quadro
    # digitado por semana, a tela sempre mostra uma semana.
    aceita_todas = FALTAS_DA_PLANILHA and visualizacao == "semanal"
    if not periodo_id or not ((periodo_id == TODAS and aceita_todas)
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

    dias_por_escala = {escala_da_tela: dias_periodo}

    def dias_da_escala(escala):
        if escala not in dias_por_escala:
            dias_por_escala[escala] = _dias_do_periodo(
                _periodos(visualizacao, mes, hoje, escala), periodo_id)
        return dias_por_escala[escala]

    # Com "Todas as semanas", as faltas de cada gestor sao a soma das
    # semanas; digitar so da com uma semana (ou um ciclo) escolhido.
    ids_do_periodo = ([p["id"] for p in periodos] if periodo_id == TODAS or not periodo_id
                      else [periodo_id])

    for gestor in sorted(gestores, key=lambda g: g["nome"].casefold()):
        dias_do_gestor = dias_da_escala(escala_espanhola(gestor["operacao"]))
        # Os numeros sao os do periodo escolhido (com "todas as semanas",
        # so no caminho da planilha, valem os da ultima semana).
        quadro = quadro_do_periodo(gestor, ids_do_periodo[-1], dias_do_gestor, config)
        if len(ids_do_periodo) > 1:
            quadro.update(dias_uteis=dias_do_gestor, dias_origem="calendario")
        hc, dias, horas_dia = quadro["hc"], quadro["dias_uteis"], quadro["horas_dia"]
        if FALTAS_DA_PLANILHA:
            faltas = _faltas_do_gestor(faltas_por_gestor, gestor["nome"], inicio, fim)
        else:
            faltas = quadro["faltas"]
        valor = presenteismo.calcular(hc, dias, horas_dia, faltas)

        hc_total += hc
        faltas_total += faltas
        horas_disponiveis += hc * dias * horas_dia
        horas_perdidas += faltas * horas_dia

        linhas.append({
            "id": gestor["id"],
            "gestor": gestor["nome"],
            "iniciais": _iniciais(gestor["nome"]),
            "usuarios": _usuarios_do_gestor(faltas_por_gestor, gestor["nome"]),
            "operacao": OPERATIONS.get(gestor["operacao"], {}).get(
                "label", gestor["operacao"]),
            "operacao_key": gestor["operacao"],
            "periodo": rotulo,
            "periodo_id": ids_do_periodo[-1],
            "hc": hc,
            "hc_origem": quadro["hc_origem"],
            "hc_de": _rotulo_de(quadro["hc_de"], periodos),
            "dias_uteis": dias,
            "dias_origem": quadro["dias_origem"],
            "dias_do_periodo": dias_do_gestor,
            "horas_dia": horas_dia,
            "horas_origem": quadro["horas_origem"],
            "horas_de": _rotulo_de(quadro["horas_de"], periodos),
            "faltas": faltas,
            "editavel": len(ids_do_periodo) == 1,
            "faltas_editavel": not FALTAS_DA_PLANILHA and len(ids_do_periodo) == 1,
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
                     + periodos) if aceita_todas else periodos,
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
        "funcoes": [
            {**f, "operacao_label": OPERATIONS.get(f["operacao"], {}).get("label", "Todas")}
            for f in headcount_store.listar_funcoes(operacao)
        ],
        "config": config,
        "meta": meta,
        "faltas_manuais": not FALTAS_DA_PLANILHA,
    }


def _rotulo_de(periodo_id, periodos):
    """Nome legivel do periodo de onde um valor foi herdado."""
    if not periodo_id:
        return None
    for periodo in periodos:
        if periodo["id"] == periodo_id:
            return periodo["rotulo"].split(" · ")[0] if "-S" in periodo_id else periodo["rotulo_curto"]
    if "-S" in periodo_id:
        ano, mes, semana = periodo_id[:4], int(periodo_id[5:7]), int(periodo_id.split("-S")[1])
        for p in presenteismo.semanas_do_mes(int(ano), mes):
            if p["numero"] == semana:
                return _rotulo_semana_do_mes(p).split(" · ")[0]
    return "ciclo de " + datetime.date.fromisoformat(periodo_id).strftime("%d/%m")


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


def presenteismo_do_intervalo(operacao, inicio, fim, hoje=None, dados=None, arquivo=None):
    """Presenteismo de uma operacao entre duas datas, ou None.

    None quando nao da pra afirmar nada: sem gestor com HC, sem arquivo,
    ou com dia util do intervalo fora do que a planilha cobre. Um
    periodo que ainda esta correndo e calculado ate onde ha dado — igual
    ao ciclo "Em aberto" da tela de Headcount.

    arquivo e o headcount_store.arquivo(dados) ja filtrado: quem calcula
    varios periodos seguidos filtra a planilha uma vez so e repassa.
    """
    hoje = hoje or datetime.date.today()
    dados = dados or headcount_store.ler()
    if arquivo is None:
        arquivo = headcount_store.arquivo(dados)
    janela = cobertura_do_arquivo(arquivo)
    if not janela:
        return None
    cobre_de, cobre_ate = janela

    if isinstance(inicio, str):
        inicio = datetime.date.fromisoformat(inicio)
    if isinstance(fim, str):
        fim = datetime.date.fromisoformat(fim)
    escala = escala_espanhola(operacao)

    # Dia util antes do que a planilha cobre: falta pode ter acontecido
    # ali sem aparecer. Nao da pra fechar o periodo.
    if inicio < cobre_de and presenteismo.dias_uteis(
            inicio, cobre_de - datetime.timedelta(days=1), escala) > 0:
        return None

    em_andamento = inicio <= hoje <= fim
    ate = min(fim, hoje, cobre_ate)
    if ate < inicio:
        return None
    # Periodo ja encerrado precisa estar coberto ate o fim.
    if not em_andamento and ate < fim and presenteismo.dias_uteis(
            ate + datetime.timedelta(days=1), min(fim, hoje), escala) > 0:
        return None

    dias = presenteismo.dias_uteis(max(inicio, cobre_de), ate, escala)
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


def presenteismo_por_periodo(operacao, hoje=None, semanas=None, meses=None):
    """Tudo que da pra afirmar para uma operacao, nos periodos da aba
    Inicio: {"week": {segunda: {...}}, "month": {"2026-09": {...}}}.

    - Semana: segunda a domingo, a mesma semana do Summary, chave na
      segunda-feira. Nao e a semana cortada no mes da tela de Headcount.
    - Mes: o ciclo da folha ponto que comeca no dia 13 desse mes.

    semanas e meses sao as chaves que a aba Inicio vai mostrar (as que
    vieram do Summary); sem elas, calcula os periodos recentes.
    """
    hoje = hoje or datetime.date.today()
    if not FALTAS_DA_PLANILHA:
        return _presenteismo_das_faltas_lancadas(operacao, hoje, semanas, meses)

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
        valor = presenteismo_do_intervalo(operacao, segunda, domingo, hoje=hoje, dados=dados,
                                          arquivo=arquivo)
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
        valor = presenteismo_do_intervalo(operacao, inicio, fim, hoje=hoje, dados=dados,
                                          arquivo=arquivo)
        if valor is not None:
            resultado["month"][ciclo["mes_referencia"]] = {
                "presenteismo": valor,
                "de": ciclo["inicio"],
                "ate": ciclo["fim"],
                "em_aberto": ciclo["status"] == "Em aberto",
            }
    return resultado


# ---------------------------------------------------------------
# Presenteismo das faltas digitadas, para a aba Inicio
# ---------------------------------------------------------------
# E a mesma conta da tela de Headcount: o numero que aparece la para uma
# semana ou um ciclo e o que vai para o Inicio e para o cubo.

def _agregar(gestores, pedacos, config):
    """Presenteismo de um conjunto de periodos (uma semana do Summary pode
    ter dois pedacos, um de cada mes), cada um com os numeros dele."""
    disponiveis = perdidas = 0.0
    for gestor in gestores:
        for periodo in pedacos:
            q = quadro_do_periodo(gestor, periodo["id"], periodo["dias_uteis"], config)
            disponiveis += q["hc"] * q["dias_uteis"] * q["horas_dia"]
            perdidas += q["faltas"] * q["horas_dia"]
    if disponiveis <= 0:
        return None
    return round(1 - perdidas / disponiveis, 6)


def _pedacos_da_semana(segunda, hoje, escala):
    """As semanas da tela de Headcount (cortadas no mes) que formam uma
    semana do Summary. Quase sempre e uma so; na virada do mes sao duas
    (31/08 a 06/09 = S6 de agosto + S1 de setembro)."""
    domingo = segunda + datetime.timedelta(days=6)
    meses = sorted({(segunda.year, segunda.month), (domingo.year, domingo.month)})
    pedacos = []
    for ano, mes in meses:
        for semana in presenteismo.semanas_do_mes(ano, mes, hoje=hoje, escala_espanhola=escala):
            if semana["inicio"] >= segunda.isoformat() and semana["fim"] <= domingo.isoformat():
                pedacos.append(semana)
    return pedacos


def _presenteismo_das_faltas_lancadas(operacao, hoje, semanas, meses):
    dados = headcount_store.ler()
    config = dados["config"]
    escala = escala_espanhola(operacao)
    resultado = {"week": {}, "month": {}}
    gestores = [g for g in dados["gestores"] if g["operacao"] == operacao]
    if not gestores:
        return resultado

    if semanas is None:
        esta = hoje - datetime.timedelta(days=hoje.weekday())
        semanas = [(esta - datetime.timedelta(weeks=n)).isoformat() for n in range(26)]
    for chave in semanas:
        segunda = datetime.date.fromisoformat(chave)
        if segunda > hoje:
            continue  # semana que nem comecou
        valor = _agregar(gestores, _pedacos_da_semana(segunda, hoje, escala), config)
        if valor is not None:
            resultado["week"][chave] = {
                "presenteismo": valor,
                "parcial": segunda <= hoje <= segunda + datetime.timedelta(days=6),
            }

    ciclos = {c["mes_referencia"]: c
              for c in presenteismo.ciclos_folha(hoje=hoje, anteriores=24, escala_espanhola=escala)}
    for chave in (meses if meses is not None else list(ciclos)):
        ciclo = ciclos.get(chave)
        if not ciclo or ciclo["dias_uteis"] <= 0:
            continue  # ciclo que ainda nao abriu, ou antigo demais
        valor = _agregar(gestores, [ciclo], config)
        if valor is not None:
            resultado["month"][chave] = {
                "presenteismo": valor,
                "de": ciclo["inicio"],
                "ate": ciclo["fim"],
                "em_aberto": ciclo["status"] == "Em aberto",
            }
    return resultado
