"""Leitura do export do Summary (.xlsx) para o calculo dos indicadores.

O mapeamento e sempre pelo **titulo** da coluna, nunca pela letra. Nao
e preciosismo: o mesmo relatorio muda o layout conforme o agrupamento.
Sem o "Medium Level Group" (que e o caso do mensal, onde o unico nivel
e o User ID), todas as colunas andam uma posicao pra esquerda. Lendo
por letra, o mensal calcularia a efetividade com a coluna errada e
entregaria um numero plausivel e falso.

Ver docs/INDICADORES.md, secao 10.1.
"""

import datetime
import unicodedata

import openpyxl

# Titulo normalizado no export -> nome usado no resto do codigo.
COLUNAS = {
    "medium level group": "semana",
    "detail level group": "detalhe",
    "var": "var",
    "goal": "goal",
    "measured direct": "measured_direct",
    "unmeasured signon direct": "signon_direct",
    "unmeasured insert direct": "insert_direct",
    "pd brk": "pd_brk",
    "total": "total",
}

# Sem estas nao da pra calcular nada, entao a falta delas e erro de
# leitura e nao linha ruim.
OBRIGATORIAS = ("goal", "measured_direct", "total", "pd_brk")

NUMERICAS = ("var", "goal", "measured_direct", "signon_direct", "insert_direct",
             "pd_brk", "total")

# Linhas de fechamento que alguns exports colocam no fim. Entram na
# soma se ninguem descartar, e o resultado dobra.
TOTALIZADORAS = {"total", "totals", "grand total", "subtotal", "sum"}


def normalizar(texto):
    """Minusculo, sem acento, sem quebra de linha e sem espaco
    duplicado: "Measured\\nDirect" e "measured direct" viram a mesma
    coisa."""
    if texto is None:
        return ""
    texto = str(texto)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.lower().split())


def _para_numero(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace("%", "")
    # Export em portugues pode vir com virgula decimal e ponto de
    # milhar ("1.407,65").
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _para_data(valor):
    """Devolve a data no formato ISO (2026-08-30), que e a chave da
    semana no arquivo guardado."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date().isoformat()
    if isinstance(valor, datetime.date):
        return valor.isoformat()

    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y"):
        try:
            return datetime.datetime.strptime(texto, formato).date().isoformat()
        except ValueError:
            continue
    return None


def _achar_cabecalho(linhas):
    """Acha a linha dos titulos. Normalmente e a primeira, mas alguns
    exports trazem um bloco de identificacao antes dela, entao
    procuramos a primeira linha que tenha as colunas que interessam."""
    for indice, linha in enumerate(linhas[:20]):
        titulos = {normalizar(c) for c in linha}
        if "goal" in titulos and "total" in titulos:
            return indice
    return None


def ler(caminho):
    """Le o export e devolve {"linhas": [...], "tem_semana": bool}.

    Cada linha e um dicionario com os nomes internos das colunas.
    tem_semana diz qual dos dois formatos veio: com coluna de semana
    (export semanal) ou sem nenhuma coluna de data (mensal, ja
    consolidado).
    """
    livro = openpyxl.load_workbook(caminho, data_only=True, read_only=True)
    try:
        aba = livro.worksheets[0]
        cruas = [list(linha) for linha in aba.iter_rows(values_only=True)]
    finally:
        livro.close()

    indice = _achar_cabecalho(cruas)
    if indice is None:
        raise ValueError(
            "Nao encontrei a linha de titulos no arquivo "
            f"({caminho}). O export precisa ter as colunas do Summary."
        )

    posicoes = {}
    for coluna, titulo in enumerate(cruas[indice]):
        nome = COLUNAS.get(normalizar(titulo))
        if nome and nome not in posicoes:
            posicoes[nome] = coluna

    faltando = [c for c in OBRIGATORIAS if c not in posicoes]
    if faltando:
        raise ValueError(
            "O arquivo nao parece ser o relatorio do Summary: faltam as "
            f"colunas {', '.join(faltando)}."
        )

    linhas = []
    for crua in cruas[indice + 1:]:
        registro = {}
        for nome, coluna in posicoes.items():
            valor = crua[coluna] if coluna < len(crua) else None
            if nome == "semana":
                registro[nome] = _para_data(valor)
            elif nome == "detalhe":
                registro[nome] = None if valor is None else str(valor).strip()
            else:
                registro[nome] = _para_numero(valor)

        if normalizar(registro.get("detalhe")) in TOTALIZADORAS:
            continue  # linha de fechamento: somaria tudo de novo
        if all(registro.get(campo) is None for campo in NUMERICAS):
            continue  # linha vazia no fim da planilha

        linhas.append(registro)

    return {"linhas": linhas, "tem_semana": "semana" in posicoes}
