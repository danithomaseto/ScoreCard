"""Versao dos arquivos de dados e os consertos que mudam o que ja esta
gravado (migracoes), num lugar so.

Cada migracao tem um numero, em ordem. A maquina guarda ate qual numero
ja rodou (settings.json, "versao_dos_dados"); na abertura do app rodam so
as que faltam, uma vez cada. Uma que falha para a fila: as seguintes
podem depender dela, e ela tenta de novo na proxima abertura.

Para criar uma: escreva a funcao (que nao derruba nada se rodar duas
vezes) e acrescente uma linha no fim de MIGRACOES com o proximo numero.
"""

import logging

import reparo_semanas
import settings_store

log = logging.getLogger("scorecard.migracoes")


def _semanas_trocadas():
    reparo_semanas.reparar()


# (numero, o que faz, funcao)
MIGRACOES = [
    (1, "semanas gravadas com dia e mês trocados (data americana)", _semanas_trocadas),
]

VERSAO_ATUAL = MIGRACOES[-1][0]


def versao_dos_dados():
    return settings_store.get_versao_dos_dados()


def pendentes():
    atual = versao_dos_dados()
    return [(numero, descricao) for numero, descricao, _ in MIGRACOES if numero > atual]


def migrar():
    """Roda as migracoes que faltam. Nunca derruba a abertura do app.
    Devolve a versao em que os dados ficaram."""
    atual = versao_dos_dados()
    for numero, descricao, passo in MIGRACOES:
        if numero <= atual:
            continue
        try:
            passo()
        except Exception:  # noqa: BLE001 - tenta de novo na proxima abertura
            log.exception("migração %d (%s) falhou", numero, descricao)
            break
        settings_store.set_versao_dos_dados(numero)
        atual = numero
        log.info("dados na versão %d: %s", numero, descricao)
    return atual
