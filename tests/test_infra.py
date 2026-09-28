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
                        lambda caminho, dados, **k: (gravados.append(caminho), original(caminho, dados, **k)))

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


# ---------------- Versao ----------------

def test_versao_do_build_e_de_desenvolvimento(tmp_path, monkeypatch):
    import sys

    import versao

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert versao.info()["versao"] == versao.numero(), "do codigo-fonte, le o arquivo VERSAO"

    from datetime import datetime
    versao.gerar(str(tmp_path / versao.ARQUIVO), agora=datetime(2026, 9, 26, 14, 30),
                 commit="a1b2c3d", versao="V.01.0")
    assert versao.info() == {"versao": "V.01.0", "build": "26/09/2026 14:30", "commit": "a1b2c3d"}


def test_numero_da_versao_sobe_de_um_em_um_e_vira_a_dezena():
    import versao

    assert versao.proxima("V.01.0") == "V.01.1"
    assert versao.proxima("V.01.8") == "V.01.9"
    assert versao.proxima("V.01.9") == "V.02.0"
    assert versao.proxima("V.09.9") == "V.10.0"
    with pytest.raises(ValueError):
        versao.proxima("2026.09.26")


def test_versao_do_projeto_esta_no_formato():
    import versao

    assert versao.FORMATO.match(versao.numero())


# ---------------- Checagem de conexao ----------------

def test_conexao_com_servidor_no_ar_e_fora_do_ar():
    import socket

    import conexao

    servidor = socket.socket()
    servidor.bind(("127.0.0.1", 0))
    servidor.listen(1)
    porta = servidor.getsockname()[1]
    try:
        assert conexao.alcancavel(f"https://127.0.0.1:{porta}/rp/login")
    finally:
        servidor.close()
    assert not conexao.alcancavel(f"https://127.0.0.1:{porta}/rp/login", tempo_limite=1)
    assert conexao.alcancavel("file:///C:/mock/login.html"), "sem rede para checar"


def test_checagem_pode_ser_desligada(monkeypatch):
    import conexao

    monkeypatch.setenv("SCORECARD_SEM_CHECAGEM_VPN", "1")
    assert conexao.alcancavel("https://127.0.0.1:1/")


def _porta_fechada():
    import socket

    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


@pytest.fixture
def api_sem_vpn(tmp_path, monkeypatch):
    import settings_store
    from config.operations import OPERATIONS
    from api import Api

    pasta = tmp_path / "sharepoint"
    pasta.mkdir()
    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(pasta))
    url = f"https://127.0.0.1:{_porta_fechada()}/portal"
    for chave in ("fora_a", "fora_b"):
        OPERATIONS[chave] = {"label": chave, "login_url": url, "report_name": "r",
                             "group_by_option": "User ID", "export_format": "EXCEL"}
    instancia = Api()
    instancia.login("usuario", "senha")
    instancia.eventos = []
    instancia._emit_js = lambda fn, payload: instancia.eventos.append((fn, payload))
    yield instancia
    for chave in ("fora_a", "fora_b"):
        OPERATIONS.pop(chave, None)


def test_sem_vpn_a_extracao_para_antes_de_abrir_o_navegador(api_sem_vpn, monkeypatch):
    import time

    import history_store
    from automation import base

    monkeypatch.setattr(base, "Navegador", lambda *a, **k: pytest.fail("nao devia abrir o navegador"))
    inicio = time.monotonic()
    resultado = api_sem_vpn.run_extraction(
        "fora_a", date_range={"from_date": "2026-09-01", "to_date": "2026-09-07"}, period="peak")

    assert time.monotonic() - inicio < 5
    assert resultado["status"] == "error"
    assert "VPN" in resultado["message"]
    historico = history_store.get_history()[0]
    assert historico["status"] == "error"
    assert historico["period_type"] == "Dias de Pico"
    assert historico["period_label"] == "01/09/2026 - 07/09/2026"


def test_fila_sem_vpn_nao_repete_a_checagem_no_mesmo_servidor(api_sem_vpn, monkeypatch):
    import conexao

    checagens = []
    original = conexao.alcancavel
    monkeypatch.setattr(conexao, "alcancavel", lambda url, **k: checagens.append(url) or original(url, **k))

    resultado = api_sem_vpn.run_multi_extraction(["fora_a", "fora_b"], period="week")

    assert resultado["failed"] == 2
    assert len(checagens) == 1, "o segundo usa o resultado do primeiro"


# ---------------- Diagnostico ----------------

def test_diagnostico_leva_log_e_ambiente_sem_dados_pessoais(log_em_arquivo, tmp_path):
    import zipfile

    import diagnostico
    import headcount_store
    from api import Api

    api = Api()
    api.login("daniel.usuario", "S3nh@Secreta!")
    headcount_store.adicionar_gestor("Marina Duarte", "hugo_boss")
    logging.getLogger("scorecard").info("erro com S3nh@Secreta! no meio")

    caminho = diagnostico.gerar(str(tmp_path / "saida"))

    with zipfile.ZipFile(caminho) as zipado:
        nomes = zipado.namelist()
        tudo = "\n".join(zipado.read(n).decode("utf-8") for n in nomes)
    assert "info.txt" in nomes and "logs/scorecard.log" in nomes
    assert "Gestores cadastrados: 1" in tudo
    assert "Marina Duarte" not in tudo, "nome de gestor nao sai da maquina"
    assert "S3nh@Secreta!" not in tudo and "daniel.usuario" not in tudo
