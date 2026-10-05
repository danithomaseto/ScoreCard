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
    "presenteismo": "PRESENTEÍSMO",
    "dispersao": "DISPERSÃO",
    "coverage": "COVERAGE",
}

# O texto que aparece embaixo do nome do indicador na tela.
METAS = {
    "cubo": "meta 85,00%",
    "efetividade": "meta 90,00% a 110,00%",
    "hora_direta": "meta 85,00%",
    "presenteismo": "meta 98,00%",
    "dispersao": "meta 70,00%",
    "coverage": "meta 92,00%",
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

# Grafico de distribuicao da dispersao (aba Inicio): a meta de pessoas
# em cada faixa de Var, sobre o total de pessoas que contam na
# dispersao. A faixa verde (-10 a +10) e a meta da propria dispersao
# (70%); cada faixa amarela, 15%; as vermelhas, nenhuma pessoa. Mesmas
# formulas da planilha de referencia (=$R$17*0,7 e =$R$17*0,15).
META_DAS_FAIXAS_DA_DISPERSAO = {
    "abaixo_15": 0.0,
    "abaixo_10": 0.15,
    "dentro": FAIXAS["dispersao"]["minimo"],
    "acima_10": 0.15,
    "acima_15": 0.0,
}

# Horas indiretas (aba Horas Indiretas): acima deste percentual das
# horas totais da semana ja e ruim e fica vermelho.
LIMITE_INDIRETAS = 0.15

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
    """Percentual como a tela mostra e como a copia entrega: sempre duas
    casas decimais e virgula, no padrao brasileiro (96,40%). Sem numero
    vira string vazia, nunca zero."""
    if valor is None:
        return ""
    return f"{valor * 100:.2f}".replace(".", ",") + "%"
