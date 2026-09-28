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
  incluir um exigiria mexer no codigo. Cada uma e de uma operacao e
  so conta nas faltas dos gestores dela.
- **config**: meta, densidade e se a formula aparece.
"""

import json
import os
import uuid
from datetime import datetime

import arquivo_seguro

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
    for gestor in dados["gestores"]:
        _migrar_faltas_lancadas(gestor)
    dados.setdefault("funcoes", [])
    dados.setdefault("arquivo", None)
    dados["config"] = {**PADRAO_CONFIG, **(dados.get("config") or {})}
    return dados


def _migrar_faltas_lancadas(gestor):
    """Versao anterior guardava so as faltas por periodo; agora o quadro
    inteiro (HC, dias uteis, horas/dia e faltas) e por periodo."""
    antigas = gestor.pop("faltas_lancadas", None)
    if antigas:
        quadro = gestor.setdefault("quadro", {})
        for periodo_id, faltas in antigas.items():
            quadro.setdefault(periodo_id, {}).setdefault("faltas", faltas)


def _gravar(dados):
    arquivo_seguro.gravar_json(_caminho(), dados, compacto=True)
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
        raise ValueError(f"{nome} já está cadastrado nesta operação.")

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
    raise ValueError("Gestor não encontrado.")


# Campos do quadro digitados por periodo: (nome na tela, inteiro?, maximo).
CAMPOS_DO_QUADRO = {
    "hc": ("HC", True, None),
    "dias_uteis": ("Dias úteis", True, 31),
    "horas_dia": ("Horas/dia", False, 24),
    "faltas": ("Faltas", True, None),
}


def definir_quadro(gestor_id, periodo_id, campo, valor):
    """Um numero do quadro de um gestor num periodo: uma semana do mes
    ("2026-09-S2") ou um ciclo da folha ("2026-09-13").

    Cada semana e cada ciclo tem os seus numeros — HC e dias uteis mudam
    de uma semana pra outra. Vazio apaga o valor do periodo, e ele volta
    a herdar (HC e horas/dia da semana anterior, dias uteis do
    calendario, faltas zero).
    """
    if campo not in CAMPOS_DO_QUADRO:
        raise ValueError("Campo inválido.")
    if not periodo_id or periodo_id == "todas":
        raise ValueError("Escolha uma semana ou um ciclo.")
    nome, inteiro, maximo = CAMPOS_DO_QUADRO[campo]
    texto = "" if valor is None else str(valor).strip().replace(",", ".")
    numero = None
    if texto:
        try:
            numero = float(texto)
        except ValueError:
            raise ValueError(f"{nome} precisa ser um número.") from None
        if numero < 0:
            raise ValueError(f"{nome} não pode ser negativo.")
        if inteiro and not numero.is_integer():
            raise ValueError(f"{nome} é um número inteiro (0, 1, 2...).")
        if maximo is not None and numero > maximo:
            raise ValueError(f"{nome} vai no máximo até {maximo}.")
        if campo == "horas_dia" and numero == 0:
            raise ValueError("Horas/dia precisa ser maior que zero.")
        numero = int(numero) if inteiro else numero

    dados = ler()
    for gestor in dados["gestores"]:
        if gestor["id"] != gestor_id:
            continue
        quadro = gestor.setdefault("quadro", {})
        do_periodo = quadro.setdefault(periodo_id, {})
        if numero is None:
            do_periodo.pop(campo, None)
            if not do_periodo:
                quadro.pop(periodo_id)
        else:
            do_periodo[campo] = numero
        _gravar(dados)
        return gestor
    raise ValueError("Gestor não encontrado.")


def lancar_faltas(gestor_id, periodo_id, valor):
    """Faltas (em dias) de um gestor num periodo."""
    return definir_quadro(gestor_id, periodo_id, "faltas", valor)


def editar_gestor(gestor_id, nome, operacao):
    """Corrige o nome ou muda a operacao de um gestor, mantendo HC, dias
    uteis e horas/dia digitados.

    O nome e o que liga o gestor as faltas da planilha: corrigi-lo para
    ficar igual ao GESTOR_NAME do arquivo faz as faltas aparecerem na
    hora, sem reenviar nada.
    """
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome do gestor.")
    if not operacao or operacao == TODAS:
        raise ValueError("Escolha a operação do gestor.")

    dados = ler()
    gestor = next((g for g in dados["gestores"] if g["id"] == gestor_id), None)
    if gestor is None:
        raise ValueError("Gestor não encontrado.")
    repetido = any(
        g["id"] != gestor_id and g["nome"].casefold() == nome.casefold() and g["operacao"] == operacao
        for g in dados["gestores"]
    )
    if repetido:
        raise ValueError(f"{nome} já está cadastrado nesta operação.")

    gestor["nome"] = nome
    gestor["operacao"] = operacao
    gestor["editado_em"] = datetime.now().isoformat(timespec="seconds")
    _gravar(dados)
    return gestor


def remover_gestor(gestor_id):
    dados = ler()
    antes = len(dados["gestores"])
    dados["gestores"] = [g for g in dados["gestores"] if g["id"] != gestor_id]
    _gravar(dados)
    return antes != len(dados["gestores"])


# ---------------- Funcoes que contam ----------------
# Cada funcao e cadastrada para uma operacao: o nome do cargo muda de
# uma operacao pra outra, e uma funcao que conta numa pode nao contar
# em outra. Versoes anteriores guardavam so o nome, valendo para todas;
# essas continuam valendo para todas ate serem removidas.

TODAS = "todas"


def _normalizar_funcao(item):
    if isinstance(item, str):
        return {"nome": item, "operacao": TODAS}
    return {"nome": item.get("nome", ""), "operacao": item.get("operacao") or TODAS}


def listar_funcoes(operacao=None):
    funcoes = [_normalizar_funcao(f) for f in ler()["funcoes"]]
    if operacao and operacao != TODAS:
        return [f for f in funcoes if f["operacao"] in (operacao, TODAS)]
    return funcoes


def adicionar_funcao(nome, operacao):
    """Uma funcao a mais que passa a contar nas faltas dos gestores de
    uma operacao. A comparacao e por trecho do texto, entao "Operador de
    Ponte" tambem pega "OPERADOR DE PONTE ROLANTE"."""
    nome = (nome or "").strip()
    if not nome:
        raise ValueError("Informe o nome da função.")
    if not operacao or operacao == TODAS:
        raise ValueError("Escolha a operação da função.")

    dados = ler()
    funcoes = [_normalizar_funcao(f) for f in dados["funcoes"]]
    if any(f["nome"].casefold() == nome.casefold() and f["operacao"] == operacao
           for f in funcoes):
        raise ValueError(f"{nome} já está na lista desta operação.")
    funcoes.append({"nome": nome, "operacao": operacao})
    dados["funcoes"] = funcoes
    _gravar(dados)
    return funcoes


def remover_funcao(nome, operacao=None):
    dados = ler()
    alvo = (nome or "").casefold()
    dados["funcoes"] = [
        f for f in (_normalizar_funcao(x) for x in dados["funcoes"])
        if not (f["nome"].casefold() == alvo and (operacao is None or f["operacao"] == operacao))
    ]
    _gravar(dados)
    return dados["funcoes"]


def _extras(dados):
    """(funcoes que valem pra todos, funcao que diz as de cada gestor)."""
    funcoes = [_normalizar_funcao(f) for f in dados.get("funcoes", [])]
    globais = [f["nome"] for f in funcoes if f["operacao"] == TODAS]

    por_operacao = {}
    for f in funcoes:
        if f["operacao"] != TODAS:
            por_operacao.setdefault(f["operacao"], []).append(f["nome"])

    operacoes_do_gestor = {}
    for g in dados.get("gestores", []):
        operacoes_do_gestor.setdefault(g["nome"].casefold(), set()).add(g["operacao"])

    def do_gestor(nome):
        extras = []
        for operacao in operacoes_do_gestor.get((nome or "").casefold(), ()):
            extras += por_operacao.get(operacao, [])
        return extras

    return globais, do_gestor


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
        globais, do_gestor = _extras(dados)
        lido = faltas_reader.filtrar(guardado["linhas"], globais, do_gestor)
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
