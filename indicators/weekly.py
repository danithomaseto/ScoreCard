"""Calculo dos indicadores a partir das linhas do relatorio.

Nenhum I/O aqui: entra uma lista de dicionarios (o que o reader.py
devolve) e sai o resultado. E a parte que precisa ser conferida numero
por numero, entao nao pode depender de arquivo, de tela nem de rede.

Serve a semana e o mes sem diferenca de logica: o export semanal vem
com a data da semana em cada linha e e agrupado por ela; o mensal ja
vem consolidado e vira um grupo so. As formulas sao as mesmas (ver
docs/INDICADORES.md, secao 10.2).
"""

import math

from .limits import META_DAS_FAIXAS_DA_DISPERSAO, TOLERANCIA_VAR


def classificar(linha, tolerancia=TOLERANCIA_VAR):
    """DENTRO, FORA ou None (fora da conta da dispersao).

    Reproduz a coluna "Dispersao" da planilha:

        se Goal = 0 ou Measured Direct = 0  -> linha ignorada
        senao se |Var| > tolerancia          -> FORA
        senao                                -> DENTRO

    Quem cai na primeira regra sai **so** da dispersao: continua
    entrando normalmente nas somas dos outros indicadores.
    """
    goal = linha.get("goal")
    medido = linha.get("measured_direct")
    var = linha.get("var")

    if not goal or not medido:
        return None
    if var is None:
        return None
    return "fora" if abs(var) > tolerancia else "dentro"


# Faixas do grafico de distribuicao da dispersao, da esquerda para a
# direita, em pontos de "Var" (o mesmo numero da classificacao acima):
#   <-15 | >=-15 <-10 | >=-10 <=10 | >10 <=15 | >15
# A faixa do meio e exatamente o DENTRO da dispersao.
FAIXAS_DA_DISPERSAO = ("abaixo_15", "abaixo_10", "dentro", "acima_10", "acima_15")


def faixa_da_dispersao(linha, tolerancia=TOLERANCIA_VAR):
    """Em qual das cinco faixas a pessoa cai, ou None se ela esta fora
    da conta da dispersao (mesma regra de classificar)."""
    if classificar(linha, tolerancia) is None:
        return None
    var = linha["var"]
    if var < -15:
        return "abaixo_15"
    if var < -tolerancia:
        return "abaixo_10"
    if var <= tolerancia:
        return "dentro"
    if var <= 15:
        return "acima_10"
    return "acima_15"


def faixas_da_dispersao(linhas, tolerancia=TOLERANCIA_VAR):
    """Quantas pessoas em cada faixa: {"abaixo_15": 1, ..., "acima_15": 1}."""
    contagem = dict.fromkeys(FAIXAS_DA_DISPERSAO, 0)
    for linha in linhas:
        faixa = faixa_da_dispersao(linha, tolerancia)
        if faixa:
            contagem[faixa] += 1
    return contagem


ROTULOS_DAS_FAIXAS = {
    "abaixo_15": "<-15",
    "abaixo_10": ">=-15 <-10",
    "dentro": ">=-10 <=10",
    "acima_10": ">10 <=15",
    "acima_15": ">15",
}
CORES_DAS_FAIXAS = {
    "abaixo_15": "vermelho",
    "abaixo_10": "amarelo",
    "dentro": "verde",
    "acima_10": "amarelo",
    "acima_15": "vermelho",
}


def _meta_em_pessoas(chave, total):
    """A meta da faixa em pessoas inteiras.

    - Verde: o **minimo** de pessoas para chegar a 70%, entao arredonda
      para cima (2 pessoas: 1,4 -> 2; 9 pessoas: 6,3 -> 7). Arredondar
      para baixo daria uma meta que nao bate os 70% (1 de 2 = 50%).
    - Amarelas: o **maximo** aceito na faixa, entao arredonda para baixo
      (9 pessoas: 1,35 -> 1; 2 pessoas: 0,3 -> 0).
    - Vermelhas: zero.

    O 1e-9 segura erros de ponto flutuante (10 x 0,7 = 7,000000000001,
    que para cima viraria 8).
    """
    exato = total * META_DAS_FAIXAS_DA_DISPERSAO[chave]
    if chave == "dentro":
        return math.ceil(exato - 1e-9)
    return math.floor(exato + 1e-9)


def distribuicao_da_dispersao(faixas):
    """O grafico da aba Inicio: pessoas e meta de cada faixa.

    A meta de cada faixa e uma parte do total de pessoas (a soma das
    cinco faixas): 70% na verde e 15% em cada amarela, como na planilha
    (=$R$17*0,7 e =$R$17*0,15), em pessoas inteiras (ver
    _meta_em_pessoas). None se nao ha contagem guardada.
    """
    if not faixas:
        return None
    total = sum(faixas.get(chave, 0) for chave in FAIXAS_DA_DISPERSAO)
    return {
        "total": total,
        "faixas": [{
            "chave": chave,
            "rotulo": ROTULOS_DAS_FAIXAS[chave],
            "cor": CORES_DAS_FAIXAS[chave],
            "pessoas": faixas.get(chave, 0),
            "meta": _meta_em_pessoas(chave, total),
        } for chave in FAIXAS_DA_DISPERSAO],
    }


def calcular_cubo(efetividade, hora_direta, presenteismo):
    """CUBO = EFETIVIDADE x HORA DIRETA x PRESENTEISMO.

    Sem presenteismo nao ha cubo — o indicador fica vazio em vez de
    virar zero, que seria um numero ruim em vez de "ainda nao temos".
    """
    if efetividade is None or hora_direta is None or presenteismo is None:
        return None
    return round(efetividade * hora_direta * presenteismo, 6)


def _dividir(numerador, denominador):
    if not denominador:
        return None
    return round(numerador / denominador, 6)


def totais(linhas, nivel_detalhe=None, tolerancia=TOLERANCIA_VAR):
    """Somas e indicadores de um conjunto de linhas.

    nivel_detalhe e o "Group By" que gerou uma linha por pessoa. A
    DISPERSAO conta linhas, entao so faz sentido com User ID ali: com
    outro agrupamento a contagem seria de turnos ou areas, e o
    percentual perderia o significado (secao 7 do documento). Nesse
    caso dentro, fora e dispersao ficam vazios, e os outros continuam,
    porque sao somas de horas e nao dependem do agrupamento.
    """
    soma = {campo: 0.0 for campo in
            ("goal", "measured_direct", "signon_direct", "insert_direct", "total", "pd_brk")}
    dentro = 0
    fora = 0

    for linha in linhas:
        for campo in soma:
            soma[campo] += linha.get(campo) or 0.0
        classe = classificar(linha, tolerancia)
        if classe == "dentro":
            dentro += 1
        elif classe == "fora":
            fora += 1

    efetividade = _dividir(soma["goal"], soma["measured_direct"])
    horas_diretas = soma["measured_direct"] + soma["signon_direct"] + soma["insert_direct"]
    hora_direta = _dividir(horas_diretas, soma["total"] - soma["pd_brk"])
    dispersao = _dividir(dentro, dentro + fora)

    conta_pessoas = nivel_detalhe is None or nivel_detalhe == "User ID"
    faixas = faixas_da_dispersao(linhas, tolerancia) if conta_pessoas else None
    if not conta_pessoas:
        dentro = fora = dispersao = None

    return {
        "linhas": len(linhas),
        "soma_goal": round(soma["goal"], 2),
        "soma_measured_direct": round(soma["measured_direct"], 2),
        "soma_signon_direct": round(soma["signon_direct"], 2),
        "soma_insert_direct": round(soma["insert_direct"], 2),
        "soma_total": round(soma["total"], 2),
        "soma_pd_brk": round(soma["pd_brk"], 2),
        "dentro": dentro,
        "fora": fora,
        # Pessoas por faixa de Var, para o grafico de distribuicao da
        # dispersao do mes na aba Inicio.
        "faixas_dispersao": faixas,
        # Os seis, na ordem de limits.ORDEM. Presenteismo e coverage sao
        # digitados a mao depois; o cubo espera o presenteismo.
        "cubo": None,
        "efetividade": efetividade,
        "hora_direta": hora_direta,
        "presenteismo": None,
        "dispersao": dispersao,
        "coverage": None,
    }


# Colunas somadas quando uma pessoa aparece em mais de uma linha.
SOMAVEIS = ("goal", "measured_direct", "signon_direct", "insert_direct", "pd_brk", "total",
            "signon_indirect", "unpd_brk")


def var_de(goal, medido):
    """O "Var" do Summary: quanto a meta passa da hora medida, em pontos
    inteiros ((Goal / Measured Direct - 1) x 100). Conferido com a
    coluna do export; a diferenca de 1 ponto que aparece as vezes e do
    arredondamento das horas que o export mostra."""
    if not goal or not medido:
        return None
    return float(round((goal / medido - 1) * 100))


def juntar_por_pessoa(linhas):
    """Uma linha por pessoa em cada semana, como no export Week > User ID.

    Com o Supervisor no meio do agrupamento, quem trabalhou com dois
    supervisores na mesma semana vem em duas linhas, cada uma com uma
    parte das horas. Para as somas tanto faz, mas a DISPERSAO conta
    pessoas: sem juntar, essa pessoa contaria duas vezes, com dois Var
    diferentes. Juntas, as horas sao somadas e o Var e refeito com elas
    (var_de). Quem tem uma linha so fica exatamente como veio.
    """
    grupos = {}
    for linha in linhas:
        chave = (linha.get("semana"), linha.get("detalhe"))
        grupos.setdefault(chave, []).append(linha)
    juntas = []
    for partes in grupos.values():
        if len(partes) == 1:
            juntas.append(partes[0])
            continue
        junta = {k: v for k, v in partes[0].items() if k not in SOMAVEIS and k not in ("var", "grupo")}
        for campo in SOMAVEIS:
            valores = [p.get(campo) for p in partes if p.get(campo) is not None]
            junta[campo] = sum(valores) if valores else None
        junta["var"] = var_de(junta.get("goal"), junta.get("measured_direct"))
        juntas.append(junta)
    return juntas


def por_semana(linhas, nivel_detalhe=None, tolerancia=TOLERANCIA_VAR):
    """Agrupa pela data da semana e calcula cada grupo.

    Uma extracao pode conter varias semanas — a planilha de exemplo tem
    tres num arquivo so —, entao o resultado e um dicionario
    {"2026-08-30": {...}}, uma entrada por semana presente.
    Linha sem data de semana fica de fora.
    """
    grupos = {}
    for linha in linhas:
        semana = linha.get("semana")
        if not semana:
            continue
        grupos.setdefault(semana, []).append(linha)

    return {
        semana: totais(grupo, nivel_detalhe=nivel_detalhe, tolerancia=tolerancia)
        for semana, grupo in sorted(grupos.items())
    }
