"""Leitura do arquivo de faltas (ABS) que alimenta o presenteismo.

Uma linha do arquivo e **uma falta de um dia** de uma pessoa: nao existe
coluna de quantidade. Cinco pessoas faltando um dia sao cinco linhas.

Nem toda linha conta. O arquivo de referencia veio com as celulas
pintadas — azul o que entra, vermelho o que sai — e e dali que vem o
filtro. A cor nao e lida em tempo de execucao: ela foi o jeito de
combinar a regra, e a regra virou os valores abaixo. Arquivos futuros
chegam sem cor nenhuma.
"""

import datetime
import os
import re
import unicodedata

from .reader import _linhas_cruas, normalizar

# Titulo normalizado -> nome usado aqui.
COLUNAS = {
    "gestor_name": "gestor",
    "gestor_ldap": "gestor_ldap",
    "nome": "usuario",
    "re": "matricula",
    "funcao": "funcao",
    "motivo": "motivo",
    "contract": "contrato",
    "abs_date": "data",
    "setor": "setor",
    "turno": "turno",
}

OBRIGATORIAS = ("gestor", "motivo", "data")

# Ferias nao e falta: a pessoa esta fora com previsao, e a hora dela nao
# entra na conta de horas disponiveis.
MOTIVOS_IGNORADOS = ("ferias",)

# So o efetivo entra. Temporario nao compoe o quadro que o presenteismo
# mede.
CONTRATOS_ACEITOS = ("efetivo",)

# Funcoes que compoem o quadro: auxiliar logistico I e II e operador
# (de empilhadeira e afins). O nome exato varia entre operacoes, entao a
# regra e por padrao de texto e nao por lista fechada — uma funcao nova
# escrita de outro jeito nao pode sumir da conta em silencio.
FUNCOES_ACEITAS = (
    re.compile(r"\blog\w*\s+i{1,2}\b"),   # "AUXILIAR LOGISTICO I", "LOG II"
    re.compile(r"\boperador\b"),
)


def _funcao_conta(funcao):
    texto = normalizar(funcao)
    if not texto:
        return True  # sem funcao informada, nao da pra excluir
    return any(padrao.search(texto) for padrao in FUNCOES_ACEITAS)


def _data_iso(valor):
    if isinstance(valor, datetime.datetime):
        return valor.date().isoformat()
    if isinstance(valor, datetime.date):
        return valor.isoformat()
    texto = str(valor or "").strip()
    if not texto:
        return None
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(texto[:10], formato).date().isoformat()
        except ValueError:
            continue
    return None


def _linhas_do_csv(caminho):
    import csv

    for codificacao in ("utf-8-sig", "latin-1"):
        try:
            with open(caminho, "r", encoding=codificacao, newline="") as fh:
                amostra = fh.read(4096)
                fh.seek(0)
                try:
                    dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t")
                except csv.Error:
                    dialeto = csv.excel
                return [linha for linha in csv.reader(fh, dialeto)]
        except UnicodeDecodeError:
            continue
    raise ValueError("Nao consegui ler o arquivo de faltas como texto.")


def _cruas(caminho):
    if os.path.splitext(caminho)[1].lower() in (".csv", ".txt"):
        return _linhas_do_csv(caminho)
    return _linhas_cruas(caminho)


def _achar_cabecalho(linhas):
    for indice, linha in enumerate(linhas[:20]):
        titulos = {normalizar(c) for c in linha}
        if "gestor_name" in titulos and "abs_date" in titulos:
            return indice
        if "gestor" in titulos and ("data da falta" in titulos or "abs_date" in titulos):
            return indice
    return None


def ler(caminho):
    """Devolve {"faltas": [...], "resumo": {...}}.

    Cada falta e {"gestor", "usuario", "data", "funcao", "motivo",
    "contrato", "dias"}. O resumo conta o que entrou e o que ficou de
    fora, por motivo — sem isso, um filtro derrubando o arquivo inteiro
    passaria despercebido.
    """
    cruas = _cruas(caminho)
    indice = _achar_cabecalho(cruas)
    if indice is None:
        raise ValueError(
            "Nao encontrei o cabecalho no arquivo de faltas. Ele precisa ter "
            "as colunas do relatorio de ausencias (GESTOR_NAME, MOTIVO, ABS_DATE)."
        )

    posicoes = {}
    for coluna, titulo in enumerate(cruas[indice]):
        nome = COLUNAS.get(normalizar(titulo))
        if nome and nome not in posicoes:
            posicoes[nome] = coluna

    faltando = [c for c in OBRIGATORIAS if c not in posicoes]
    if faltando:
        raise ValueError(
            f"O arquivo de faltas nao tem as colunas {', '.join(faltando)}."
        )

    faltas = []
    resumo = {"linhas": 0, "consideradas": 0, "sem_data": 0,
              "motivo": 0, "contrato": 0, "funcao": 0}

    for crua in cruas[indice + 1:]:
        def campo(nome):
            coluna = posicoes.get(nome)
            if coluna is None or coluna >= len(crua):
                return None
            return crua[coluna]

        gestor = (str(campo("gestor") or "")).strip()
        data = _data_iso(campo("data"))
        if not gestor and not data:
            continue  # linha vazia no fim da planilha

        resumo["linhas"] += 1

        if not data:
            resumo["sem_data"] += 1
            continue
        if normalizar(campo("motivo")) in MOTIVOS_IGNORADOS:
            resumo["motivo"] += 1
            continue
        contrato = normalizar(campo("contrato"))
        if contrato and contrato not in CONTRATOS_ACEITOS:
            resumo["contrato"] += 1
            continue
        if not _funcao_conta(campo("funcao")):
            resumo["funcao"] += 1
            continue

        resumo["consideradas"] += 1
        faltas.append({
            "gestor": gestor,
            "usuario": (str(campo("usuario") or "")).strip(),
            "data": data,
            "funcao": (str(campo("funcao") or "")).strip(),
            "motivo": (str(campo("motivo") or "")).strip(),
            "contrato": (str(campo("contrato") or "")).strip(),
            # Uma linha e um dia de ausencia: o arquivo nao traz
            # quantidade, entao 5 pessoas faltando 1 dia sao 5 linhas.
            "dias": 1,
        })

    resumo["gestores"] = len({f["gestor"] for f in faltas})
    resumo["dias"] = sum(f["dias"] for f in faltas)
    return {"faltas": faltas, "resumo": resumo}
