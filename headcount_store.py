"""Gestores, quadro e faltas importadas, guardados localmente.

Mesmo padrao dos outros stores: um arquivo por usuario/maquina em
%APPDATA%\\ScoreCard.

O que fica aqui:

- **gestores**: nome, operacao e o quadro (HC, dias uteis, horas/dia).
  O HC e digitado; as faltas, nunca.
- **faltas**: o resultado da ultima planilha importada, ja filtrada. Um
  arquivo so cobre varios periodos, entao os lancamentos ficam soltos,
  com a data, e sao roteados na hora de montar a tela.
- **funcoes**: funcoes que contam como falta alem dos padroes do
  leitor. Cargo com nome proprio aparece o tempo todo; sem essa lista,
  incluir um exigiria mexer no codigo.
- **config**: meta, densidade e se a formula aparece.
"""

import json
import os
import uuid
from datetime import datetime

APP_NAME = "ScoreCard"

PADRAO_CONFIG = {
    "meta": 0.98,
    "mostrar_formula": True,
    "densidade": "padrao",
    "horas_dia": 8.0,
}


def _caminho():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta = os.path.join(base, APP_NAME)
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "headcount.json")


def ler():
    caminho = _caminho()
    dados = {}
    if os.path.isfile(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as fh:
                lido = json.load(fh)
                dados = lido if isinstance(lido, dict) else {}
        except (json.JSONDecodeError, OSError):
            dados = {}

    dados.setdefault("gestores", [])
    dados.setdefault("funcoes", [])
    dados.setdefault("arquivo", None)
    dados["config"] = {**PADRAO_CONFIG, **(dados.get("config") or {})}
    return dados


def _gravar(dados):
    with open(_caminho(), "w", encoding="utf-8") as fh:
        json.dump(dados, fh, indent=2, ensure_ascii=False)
    return dados


# ---------------- Gestores ----------------

def listar_gestores(operacao=None):
    gestores = ler()["gestores"]
    if operacao and operacao != "todas":
        return [g for g in gestores if g["operacao"] == operacao]
    return gestores


def adicionar_gestor(nome, operacao, horas_dia=None):
    """O nome e o unico campo pedido na tela; a operacao vem do filtro.

    HC e faltas nascem zerados: o HC porque sera digitado, as faltas
    porque so a planilha as preenche.
    """
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do gestor.")

    dados = ler()
    ja_existe = any(
        g["nome"].casefold() == nome.casefold() and g["operacao"] == operacao
        for g in dados["gestores"]
    )
    if ja_existe:
        raise ValueError(f"{nome} ja esta cadastrado nesta operacao.")

    gestor = {
        "id": uuid.uuid4().hex[:12],
        "nome": nome,
        "operacao": operacao,
        "hc": 0,
        "dias_uteis": None,   # None = usa os dias uteis do periodo
        "horas_dia": horas_dia or dados["config"]["horas_dia"],
        "criado_em": datetime.now().isoformat(timespec="seconds"),
    }
    dados["gestores"].append(gestor)
    _gravar(dados)
    return gestor


def atualizar_gestor(gestor_id, campos):
    """Altera HC, dias uteis ou horas/dia de um gestor."""
    dados = ler()
    for gestor in dados["gestores"]:
        if gestor["id"] != gestor_id:
            continue
        for campo in ("hc", "dias_uteis", "horas_dia"):
            if campo in campos:
                valor = campos[campo]
                gestor[campo] = None if valor in ("", None) else float(valor)
        # HC e gente: nao faz sentido com casa decimal.
        if gestor.get("hc") is not None:
            gestor["hc"] = int(gestor["hc"])
        if gestor.get("dias_uteis") is not None:
            gestor["dias_uteis"] = int(gestor["dias_uteis"])
        _gravar(dados)
        return gestor
    raise ValueError("Gestor nao encontrado.")


def remover_gestor(gestor_id):
    dados = ler()
    antes = len(dados["gestores"])
    dados["gestores"] = [g for g in dados["gestores"] if g["id"] != gestor_id]
    _gravar(dados)
    return antes != len(dados["gestores"])


# ---------------- Funcoes que contam ----------------

def listar_funcoes():
    return ler()["funcoes"]


def adicionar_funcao(nome):
    """Uma funcao a mais que passa a contar nas faltas. A comparacao e
    por trecho do texto, entao "Operador de Ponte" tambem pega
    "OPERADOR DE PONTE ROLANTE"."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da funcao.")

    dados = ler()
    if any(f.casefold() == nome.casefold() for f in dados["funcoes"]):
        raise ValueError(f"{nome} ja esta na lista.")
    dados["funcoes"].append(nome)
    _gravar(dados)
    return dados["funcoes"]


def remover_funcao(nome):
    dados = ler()
    dados["funcoes"] = [f for f in dados["funcoes"] if f.casefold() != (nome or "").casefold()]
    _gravar(dados)
    return dados["funcoes"]


# ---------------- Faltas ----------------

def salvar_faltas(nome_arquivo, tamanho, linhas):
    """Guarda as linhas da planilha **sem filtro**.

    O filtro roda na leitura (ver arquivo()), com as funcoes cadastradas
    naquele momento. Guardar ja filtrado congelaria a regra da hora da
    importacao: uma funcao cadastrada depois so valeria reenviando o
    arquivo.
    """
    dados = ler()
    dados["arquivo"] = {
        "nome": nome_arquivo,
        "tamanho": tamanho,
        "importado_em": datetime.now().isoformat(timespec="seconds"),
        "linhas": linhas,
    }
    _gravar(dados)
    return arquivo(dados)


def arquivo(dados=None):
    """O arquivo importado com as faltas e o resumo calculados agora,
    com as funcoes cadastradas agora. None se nao ha arquivo."""
    from indicators import faltas as faltas_reader

    dados = dados or ler()
    guardado = dados.get("arquivo")
    if not guardado:
        return None

    if "linhas" in guardado:
        lido = faltas_reader.filtrar(guardado["linhas"], dados.get("funcoes"))
    else:
        # Arquivo importado por uma versao anterior, que guardava as
        # faltas ja filtradas. Continua valendo ate a proxima importacao.
        lido = {"faltas": guardado.get("faltas", []), "resumo": guardado.get("resumo", {})}

    return {
        "nome": guardado["nome"],
        "tamanho": guardado["tamanho"],
        "importado_em": guardado["importado_em"],
        "faltas": lido["faltas"],
        "resumo": lido["resumo"],
    }


def limpar_faltas():
    dados = ler()
    dados["arquivo"] = None
    _gravar(dados)


def faltas():
    atual = arquivo()
    return atual["faltas"] if atual else []


# ---------------- Configuracao ----------------

def salvar_config(campos):
    dados = ler()
    dados["config"].update({k: v for k, v in campos.items() if k in PADRAO_CONFIG})
    _gravar(dados)
    return dados["config"]
