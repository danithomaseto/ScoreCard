"""Resumo no topo da aba Inicio: quantos indicadores estao na meta na
coluna de referencia (o mes, ou a ultima semana quando o mes ainda nao
foi extraido), o melhor e o pior, e a comparacao com o periodo anterior.

So le as faixas de limits.py: "na meta" e o verde da tabela (azul, acima
do teto, nao conta como na meta). Melhor e o verde com mais folga sobre o
minimo; pior, o vermelho mais longe dele.
"""

from indicators import limits

NOMES = {
    "cubo": "Cubo",
    "efetividade": "Efetividade",
    "hora_direta": "Hora direta",
    "presenteismo": "Presenteísmo",
    "dispersao": "Dispersão",
    "coverage": "Coverage",
}


def _pontos(folga):
    """0,1157 -> "+11,57 p.p."; negativo com o sinal de menos tipografico."""
    texto = f"{folga * 100:+.2f}".replace(".", ",").replace("-", "−")
    return f"{texto} p.p."


def contar(valores):
    """{"na_meta", "com_numero"} dos valores {indicador: fracao ou None}."""
    com_numero = [i for i in limits.ORDEM if valores.get(i) is not None]
    na_meta = sum(1 for i in com_numero if limits.cor(i, valores[i]) == "verde")
    return {"na_meta": na_meta, "com_numero": len(com_numero)}


def _item(achado):
    if not achado:
        return None
    folga, indicador, valor = achado
    return {"indicador": indicador, "nome": NOMES[indicador], "texto": limits.formatar(valor), "folga": _pontos(folga)}


def resumir(coluna, periodo, valores, anterior=None):
    """valores: {indicador: fracao ou None}, so os indicadores que existem
    na coluna (o coverage nao existe no pico, por exemplo). anterior: o
    contar() do periodo anterior, com "rotulo", ou None."""
    melhor = pior = None
    for indicador in limits.ORDEM:
        valor = valores.get(indicador)
        if valor is None:
            continue
        folga = valor - limits.FAIXAS[indicador]["minimo"]
        cor = limits.cor(indicador, valor)
        if cor == "verde" and (melhor is None or folga > melhor[0]):
            melhor = (folga, indicador, valor)
        elif cor == "vermelho" and (pior is None or folga < pior[0]):
            pior = (folga, indicador, valor)
    resumo = {
        "coluna": coluna,
        "periodo": periodo,
        "total": len([i for i in limits.ORDEM if i in valores]),
        **contar(valores),
        "melhor": _item(melhor),
        "pior": _item(pior),
        "anterior": None,
    }
    if anterior and anterior.get("com_numero"):
        resumo["anterior"] = {**anterior, "diferenca": resumo["na_meta"] - anterior["na_meta"]}
    return resumo
