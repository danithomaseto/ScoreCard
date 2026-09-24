"""Calculo dos indicadores a partir das linhas do relatorio.

Nenhum I/O aqui: entra uma lista de dicionarios (o que o reader.py
devolve) e sai o resultado. E a parte que precisa ser conferida numero
por numero, entao nao pode depender de arquivo, de tela nem de rede.

Serve a semana e o mes sem diferenca de logica: o export semanal vem
com a data da semana em cada linha e e agrupado por ela; o mensal ja
vem consolidado e vira um grupo so. As formulas sao as mesmas (ver
docs/INDICADORES.md, secao 10.2).
"""

from .limits import TOLERANCIA_VAR


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
        # Os seis, na ordem de limits.ORDEM. Presenteismo e coverage sao
        # digitados a mao depois; o cubo espera o presenteismo.
        "cubo": None,
        "efetividade": efetividade,
        "hora_direta": hora_direta,
        "presenteismo": None,
        "dispersao": dispersao,
        "coverage": None,
    }


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
