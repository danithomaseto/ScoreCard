"""Gravacao segura dos arquivos de dados e o log local."""

import json
import logging
import os

import pytest


def test_gravacao_que_falha_no_meio_mantem_o_arquivo_anterior(tmp_path):
    import arquivo_seguro

    caminho = tmp_path / "dados.json"
    arquivo_seguro.gravar_json(str(caminho), {"gestores": ["G05"]})

    with pytest.raises(TypeError):
        # Um valor que o json nao sabe gravar estoura no meio da escrita.
        arquivo_seguro.gravar_json(str(caminho), {"gestores": ["G05", object()]})

    assert json.loads(caminho.read_text(encoding="utf-8")) == {"gestores": ["G05"]}
    assert os.listdir(tmp_path) == ["dados.json"], "o temporario nao pode ficar para tras"


def test_stores_gravam_pelo_caminho_seguro(tmp_path, monkeypatch):
    import arquivo_seguro
    import headcount_store

    gravados = []
    original = arquivo_seguro.gravar_json
    monkeypatch.setattr(arquivo_seguro, "gravar_json",
                        lambda caminho, dados: (gravados.append(caminho), original(caminho, dados)))

    headcount_store.adicionar_gestor("G05", "hugo_boss")

    assert gravados and gravados[0].endswith("headcount.json")
    assert headcount_store.listar_gestores("hugo_boss")[0]["nome"] == "G05"


@pytest.fixture
def log_em_arquivo(tmp_path, monkeypatch):
    import registro

    monkeypatch.setenv("APPDATA", str(tmp_path))
    raiz = logging.getLogger()
    antes = list(raiz.handlers)
    registro.configurar()
    yield tmp_path / "ScoreCard" / "logs" / "scorecard.log"
    for handler in raiz.handlers[:]:
        if handler not in antes:
            handler.close()
            raiz.removeHandler(handler)
    registro.esquecer()


def test_log_nunca_grava_usuario_nem_senha(log_em_arquivo):
    from api import Api

    api = Api()
    api.login("daniel.usuario", "S3nh@Secreta!")
    # Um erro vindo de fora que, por acaso, repete o que foi digitado.
    logging.getLogger("scorecard.automacao").error(
        "fill falhou com valor S3nh@Secreta! para daniel.usuario")
    try:
        raise RuntimeError("timeout preenchendo S3nh@Secreta!")
    except RuntimeError:
        logging.getLogger("scorecard").exception("erro")

    texto = log_em_arquivo.read_text(encoding="utf-8")
    assert "S3nh@Secreta!" not in texto
    assert "daniel.usuario" not in texto
    assert "fill falhou com valor *** para ***" in texto


def test_log_registra_a_importacao_de_faltas(log_em_arquivo):
    import base64

    from api import Api

    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "faltas_abs.xlsx")
    with open(fixture, "rb") as fh:
        Api().import_faltas("faltas_abs.xlsx", base64.b64encode(fh.read()).decode())

    assert "planilha de faltas faltas_abs.xlsx importada" in log_em_arquivo.read_text(encoding="utf-8")
