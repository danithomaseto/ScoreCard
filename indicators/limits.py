"""Metas, faixas de cor e tolerancia dos indicadores.

Tudo o que e "regra de negocio numerica" mora aqui, separado do
calculo (weekly.py) e da tela: mudar uma meta nao pode exigir mexer em
nenhum dos dois.

As faixas sao iguais para as 12 operacoes.
"""

# Tolerancia da classificacao DENTRO/FORA, em pontos percentuais de
# "Var" (a coluna que o proprio relatorio ja calcula).
TOLERANCIA_VAR = 10

# Ordem dos indicadores na tela, no arquivo guardado e na copia. E a
# mesma em todo lugar de proposito: quem copia uma coluna cola numa
# apresentacao que segue esta ordem.
ORDEM = ["cubo", "efetividade", "hora_direta", "presenteismo", "dispersao", "coverage"]

ROTULOS = {
    "cubo": "CUBO",
    "efetividade": "EFETIVIDADE",
    "hora_direta": "HORA DIRETA",
    "presenteismo": "PRESENTEISMO",
    "dispersao": "DISPERSAO",
    "coverage": "COVERAGE",
}

# O texto que aparece embaixo do nome do indicador na tela.
METAS = {
    "cubo": "meta 85%",
    "efetividade": "meta 90% a 110%",
    "hora_direta": "meta 85%",
    "presenteismo": "meta 98%",
    "dispersao": "meta 70%",
    "coverage": "meta 92%",
}

# minimo = abaixo disso fica vermelho; teto = acima disso fica azul.
# teto None significa que nao existe faixa azul: passou do minimo, e
# verde, nao importa o quanto.
FAIXAS = {
    "cubo": {"minimo": 0.85, "teto": 1.00},
    "efetividade": {"minimo": 0.90, "teto": 1.10},
    "hora_direta": {"minimo": 0.85, "teto": None},
    "presenteismo": {"minimo": 0.98, "teto": None},
    "dispersao": {"minimo": 0.70, "teto": None},
    "coverage": {"minimo": 0.92, "teto": 1.10},
}

# Indicadores que nao saem do export do Summary: sao digitados a mao
# (ver docs/INDICADORES.md, secao 13). Uma regravacao vinda da extracao
# nunca pode sobrescrever esses campos.
MANUAIS = ("presenteismo", "coverage")


def cor(indicador, valor):
    """Devolve "verde", "vermelho", "azul" ou None (sem numero ainda).

    valor e a fracao (0,964 e 96,4%), no mesmo formato em que o
    indicador e calculado e guardado.
    """
    if valor is None:
        return None
    faixa = FAIXAS.get(indicador)
    if not faixa:
        return None
    if valor < faixa["minimo"]:
        return "vermelho"
    if faixa["teto"] is not None and valor > faixa["teto"]:
        return "azul"
    return "verde"


def formatar(valor):
    """Percentual como a tela mostra e como a copia entrega: uma casa
    decimal e virgula, no padrao brasileiro. Sem numero vira string
    vazia, nunca zero."""
    if valor is None:
        return ""
    return f"{valor * 100:.1f}".replace(".", ",") + "%"
