"""Observador da pasta do SharePoint (observador_de_pasta.py)."""

import threading
import time

import observador_de_pasta
import settings_store
from api import Api


def _esperar(evento, segundos=5):
    return evento.wait(segundos)


def test_avisa_uma_vez_por_rajada_de_mudancas(tmp_path, monkeypatch):
    monkeypatch.setattr(observador_de_pasta.os, "name", "posix")  # conferencia por assinatura
    pasta = tmp_path / "Hughes" / "Week"
    pasta.mkdir(parents=True)
    avisos = []
    avisou = threading.Event()

    def ao_mudar():
        avisos.append(time.monotonic())
        avisou.set()

    observador = observador_de_pasta.Observador(str(tmp_path), ao_mudar, espera=0.3, intervalo=0.1).iniciar()
    try:
        time.sleep(0.3)
        for n in range(3):  # o OneDrive baixando tres arquivos seguidos
            (pasta / f"ScoreCard_hughes_2026101{n}_080000.xls").write_bytes(b"x" * (n + 1))
            time.sleep(0.05)
        assert _esperar(avisou)
        time.sleep(0.8)
        assert len(avisos) == 1
        assert observador.modo == "conferencia"

        avisou.clear()
        (tmp_path / "Hughes" / "Lancamentos").mkdir()
        (tmp_path / "Hughes" / "Lancamentos" / "ScoreCard_lancamentos_hughes.json").write_text("{}")
        assert _esperar(avisou)
    finally:
        observador.parar()


def test_sem_mudanca_nao_avisa(tmp_path, monkeypatch):
    monkeypatch.setattr(observador_de_pasta.os, "name", "posix")
    avisou = threading.Event()
    observador = observador_de_pasta.Observador(str(tmp_path), avisou.set, espera=0.1, intervalo=0.1).iniciar()
    try:
        assert not avisou.wait(0.6)
    finally:
        observador.parar()


def test_a_leitura_da_pasta_liga_o_observador(tmp_path):
    base = tmp_path / "sharepoint"
    base.mkdir()
    settings_store.set_sharepoint_folder(str(base))
    app = Api()
    try:
        assert app.sincronizar_sharepoint()["observando"] is True
        primeiro = app._observador
        app.sincronizar_sharepoint()
        assert app._observador is primeiro  # nao abre outro a cada leitura

        outra = tmp_path / "outra"
        outra.mkdir()
        settings_store.set_sharepoint_folder(str(outra))
        app.sincronizar_sharepoint()
        assert app._observador is not primeiro and not primeiro.ativo
        assert app._observador.base == str(outra)
    finally:
        if app._observador:
            app._observador.parar()


def test_sem_pasta_nao_observa(tmp_path):
    settings_store.set_sharepoint_folder(str(tmp_path / "nao-existe"))
    app = Api()
    assert app.sincronizar_sharepoint().get("observando") in (False, None)
    assert app._observador is None
