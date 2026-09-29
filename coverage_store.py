"""Dados do Coverage, guardados em %APPDATA%\\ScoreCard\\coverage.json.

Duas partes, separadas de proposito:

- **extracoes**: as horas por usuario que vieram do Summary, por
  operacao e periodo ("week:2026-09-20" ou "month:2026-09"). Sao
  gravadas na hora da extracao — o arquivo baixado e substituido no
  proximo download, entao e ali ou nunca.
- **manuais**: dias, horas, sinergia cedida e recebida digitados na
  tela, por usuario. Ficam fora das extracoes para que extrair de novo a
  mesma semana nao apague o que foi digitado.
"""

import json
import os
from datetime import datetime

import arquivo_seguro
from indicators.coverage import CAMPOS_MANUAIS

APP_NAME = "ScoreCard"

# campo -> (nome na tela, maximo)
LIMITES = {
    "dias": ("Dias", 31),
    "horas": ("Horas", 24),
    "cedida": ("Sinergia cedida", None),
    "recebida": ("Sinergia recebida", None),
}


def _caminho():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta = os.path.join(base, APP_NAME)
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, "coverage.json")


def ler():
    dados = {}
    if os.path.isfile(_caminho()):
        try:
            with open(_caminho(), encoding="utf-8") as fh:
                lido = json.load(fh)
                dados = lido if isinstance(lido, dict) else {}
        except (OSError, ValueError):
            dados = {}
    dados.setdefault("extracoes", {})
    dados.setdefault("manuais", {})
    return dados


def _gravar(dados):
    arquivo_seguro.gravar_json(_caminho(), dados, compacto=True)


def chave(periodo, chave_periodo):
    """"week:2026-09-20" ou "month:2026-09"."""
    return f"{periodo}:{chave_periodo}"


def salvar_extracao(operacao, periodo, por_chave, de=None, ate=None):
    """por_chave e {chave do periodo: {usuario: {"lms", "diretas_sem_meta"}}}.
    Substitui o que havia daquele periodo: e sempre o export mais novo."""
    dados = ler()
    da_operacao = dados["extracoes"].setdefault(operacao, {})
    agora = datetime.now().isoformat(timespec="seconds")
    for chave_periodo, usuarios in por_chave.items():
        da_operacao[chave(periodo, chave_periodo)] = {
            "usuarios": usuarios,
            "de": de,
            "ate": ate,
            "extraido_em": agora,
        }
    _gravar(dados)


def extracoes(operacao=None):
    """{operacao: {"week:...": {...}}}, ou so de uma operacao."""
    todas = ler()["extracoes"]
    if operacao:
        return {operacao: todas.get(operacao, {})} if operacao in todas else {}
    return todas


def manuais(operacao, chave_periodo):
    return ler()["manuais"].get(operacao, {}).get(chave_periodo, {})


def _numero(campo, valor):
    nome, maximo = LIMITES[campo]
    texto = "" if valor is None else str(valor).strip().replace(",", ".")
    if not texto:
        return None
    try:
        numero = float(texto)
    except ValueError:
        raise ValueError(f"{nome} precisa ser um número.") from None
    if numero < 0:
        raise ValueError(f"{nome} não pode ser negativo.")
    if maximo is not None and numero > maximo:
        raise ValueError(f"{nome} vai no máximo até {maximo}.")
    if campo == "dias" and not numero.is_integer():
        raise ValueError("Dias é um número inteiro.")
    return int(numero) if campo == "dias" else round(numero, 4)


def definir(operacao, chave_periodo, usuarios, campo, valor):
    """Grava (ou apaga, com vazio) um campo digitado para um ou mais
    usuarios de uma operacao num periodo."""
    if campo not in CAMPOS_MANUAIS:
        raise ValueError("Campo inválido.")
    numero = _numero(campo, valor)
    dados = ler()
    do_periodo = dados["manuais"].setdefault(operacao, {}).setdefault(chave_periodo, {})
    for usuario in usuarios:
        do_usuario = do_periodo.setdefault(usuario, {})
        if numero is None:
            do_usuario.pop(campo, None)
            if not do_usuario:
                do_periodo.pop(usuario)
        else:
            do_usuario[campo] = numero
    _gravar(dados)
