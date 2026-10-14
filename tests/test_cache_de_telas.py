"""Telas guardadas em memoria ate os dados mudarem (cache_de_telas.py)."""

import datetime
import os
import time

import pytest

import cache_de_telas
import headcount_store
from api import Api


@pytest.fixture
def app():
    cache_de_telas.limpar()
    cache_de_telas.estatisticas.update(acertos=0, montagens=0)
    return Api()


def test_a_mesma_tela_pedida_de_novo_nao_e_montada_de_novo(app):
    primeira = app.get_headcount("hughes", "semanal", "2026-09", None)
    segunda = app.get_headcount("hughes", "semanal", "2026-09", None)
    assert segunda is primeira
    assert cache_de_telas.estatisticas == {"acertos": 1, "montagens": 1}
    # Outro filtro e outra tela.
    app.get_headcount("swa", "semanal", "2026-09", None)
    assert cache_de_telas.estatisticas["montagens"] == 2


def test_gravar_qualquer_dado_monta_de_novo(app):
    antes = app.get_headcount("hughes", "semanal", "2026-09", None)
    headcount_store.adicionar_gestor("SILVA,ANA", "hughes")
    depois = app.get_headcount("hughes", "semanal", "2026-09", None)
    assert depois is not antes
    assert [linha["gestor"] for linha in depois["linhas"]] == ["SILVA,ANA"]


def test_arquivo_mudado_por_fora_monta_de_novo(app):
    headcount_store.adicionar_gestor("SILVA,ANA", "hughes")
    app.get_headcount("hughes", "semanal", "2026-09", None)
    # Como um backup restaurado: o arquivo muda sem passar pelo app.
    caminho = headcount_store._caminho()
    with open(caminho, encoding="utf-8") as fh:
        texto = fh.read()
    with open(caminho, "w", encoding="utf-8") as fh:
        fh.write(texto.replace("SILVA,ANA", "SOUZA,BRUNO"))
    futuro = time.time() + 5
    os.utime(caminho, (futuro, futuro))
    tela = app.get_headcount("hughes", "semanal", "2026-09", None)
    assert [linha["gestor"] for linha in tela["linhas"]] == ["SOUZA,BRUNO"]


def test_virar_o_dia_monta_de_novo(app, monkeypatch):
    app.get_headcount("hughes", "semanal", "2026-09", None)

    amanha = datetime.date.today() + datetime.timedelta(days=1)
    monkeypatch.setattr(cache_de_telas, "_hoje", lambda: amanha)
    app.get_headcount("hughes", "semanal", "2026-09", None)
    assert cache_de_telas.estatisticas["montagens"] == 2


def test_guarda_no_maximo_o_limite(app, monkeypatch):
    monkeypatch.setattr(cache_de_telas, "LIMITE", 2)
    for mes in ("2026-07", "2026-08", "2026-09"):
        app.get_headcount("hughes", "semanal", mes, None)
    assert len(cache_de_telas._guardadas) == 2
