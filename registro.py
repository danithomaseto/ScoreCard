"""Arquivo de log local: %APPDATA%\\ScoreCard\\logs\\scorecard.log.

O .exe roda sem console, entao um erro que nao aparece na tela some sem
rastro. Aqui fica o que o app fez — abertura, etapas da automacao,
extracoes, importacoes e erros com o traceback — para descobrir depois
o que aconteceu numa maquina.

Tamanho limitado: ao passar de 1 MB o arquivo e renomeado e comeca
outro, guardando so os 3 anteriores.

Credenciais nunca chegam ao arquivo. Nenhum trecho do app registra
usuario ou senha, e alem disso todo texto passa por um filtro que troca
por *** o usuario e a senha da sessao atual, caso aparecam dentro de
alguma mensagem de erro vinda de fora (do navegador, por exemplo). O
filtro so guarda esses valores em memoria, enquanto a sessao dura.
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

APP_NAME = "ScoreCard"

_segredos = set()


def pasta():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME, "logs")


def esconder(*textos):
    """Registra textos que nunca podem aparecer no log (usuario e senha
    da sessao)."""
    for texto in textos:
        if texto:
            _segredos.add(str(texto))


def esquecer():
    _segredos.clear()


def _limpar(texto):
    # Do mais longo pro mais curto: se o usuario estiver contido na
    # senha, a senha inteira some primeiro.
    for segredo in sorted(_segredos, key=len, reverse=True):
        texto = texto.replace(segredo, "***")
    return texto


class _FormatoSemSegredo(logging.Formatter):
    """Filtra o texto ja formatado, traceback incluido — e ali que uma
    mensagem de erro de terceiros poderia trazer um valor digitado."""

    def format(self, record):
        return _limpar(super().format(record))


def configurar():
    """Liga o log em arquivo. Chamado uma vez, na abertura do app."""
    try:
        os.makedirs(pasta(), exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(pasta(), "scorecard.log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
    except OSError:
        return  # sem log e melhor do que sem app

    handler.setFormatter(_FormatoSemSegredo(
        "%(asctime)s %(levelname)-7s [%(name)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.addHandler(handler)

    def excecao_nao_tratada(tipo, valor, tb):
        logging.getLogger("scorecard").critical("Erro nao tratado", exc_info=(tipo, valor, tb))
        sys.__excepthook__(tipo, valor, tb)

    def excecao_em_thread(args):
        if args.exc_type is SystemExit:
            return
        logging.getLogger("scorecard").critical(
            "Erro nao tratado na thread %s", getattr(args.thread, "name", "?"),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback))

    sys.excepthook = excecao_nao_tratada
    threading.excepthook = excecao_em_thread
