"""Lancador do ScoreCard.exe: o app vai dentro dele e e descompactado
uma vez so por versao (ver lancador.py e tools/empacotar.py).

Aqui o "executavel" e de mentira: uns bytes no lugar do lancador e um
pacote com o mesmo rodape que o PyInstaller grava. E o suficiente para
validar o formato, a descompactacao e as protecoes — o build de verdade
foi validado a parte com o PyInstaller.
"""

import os

import pytest

import lancador
from tools import empacotar


def _lancador_falso(caminho):
    """Cabeca de executavel + pacote terminado pelo cookie do PyInstaller."""
    corpo = b"PACOTE DO PYINSTALLER" * 100
    tamanho_pacote = len(corpo) + lancador.COOKIE_PYINSTALLER.size
    cookie = lancador.COOKIE_PYINSTALLER.pack(
        lancador._magic_pyinstaller(), tamanho_pacote, 0, 0, 311, b"python311.dll")
    with open(caminho, "wb") as fh:
        fh.write(b"MZ" + b"\0" * 5000 + corpo + cookie)
    return corpo + cookie


def _app_falso(pasta, texto="v1"):
    os.makedirs(os.path.join(pasta, "_internal", "ui"))
    with open(os.path.join(pasta, lancador.NOME_DO_APP), "wb") as fh:
        fh.write(b"exe do app")
    with open(os.path.join(pasta, "_internal", "ui", "index.html"), "w") as fh:
        fh.write(texto)
    os.makedirs(os.path.join(pasta, "_internal", "vazia"))


@pytest.fixture
def exe(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    caminho = str(tmp_path / "ScoreCard.exe")
    pacote = _lancador_falso(caminho)
    _app_falso(str(tmp_path / "ScoreCardApp"))
    versao = empacotar.empacotar(str(tmp_path / "ScoreCardApp"), caminho)
    return caminho, versao, pacote


def test_empacotar_deixa_um_arquivo_so(exe, tmp_path):
    caminho, _, pacote = exe
    assert sorted(os.listdir(tmp_path)) == ["ScoreCard.exe"], "a pasta do app e o zip nao ficam"
    with open(caminho, "rb") as fh:
        conteudo = fh.read()
    assert conteudo.startswith(b"MZ")
    assert conteudo.endswith(pacote), "o pacote do PyInstaller precisa continuar no fim do arquivo"


def test_primeira_abertura_descompacta_e_a_segunda_nao(exe):
    caminho, versao, _ = exe
    avisos = []

    pasta = lancador.preparar(caminho, avisar=avisos.append)

    assert pasta.endswith(f"app-{versao}")
    with open(os.path.join(pasta, "_internal", "ui", "index.html")) as fh:
        assert fh.read() == "v1"
    assert os.path.isdir(os.path.join(pasta, "_internal", "vazia"))
    assert os.path.isfile(os.path.join(pasta, lancador.PRONTO))
    assert avisos[-1] == 100

    avisos.clear()
    assert lancador.preparar(caminho, avisar=avisos.append) == pasta
    assert avisos == [], "da segunda vez em diante so abre"


def test_descompactacao_interrompida_e_refeita(exe):
    caminho, _, _ = exe
    pasta = lancador.preparar(caminho)
    os.remove(os.path.join(pasta, lancador.PRONTO))
    os.remove(os.path.join(pasta, "_internal", "ui", "index.html"))

    lancador.preparar(caminho)

    assert os.path.isfile(os.path.join(pasta, "_internal", "ui", "index.html"))
    assert os.path.isfile(os.path.join(pasta, lancador.PRONTO))


def test_versao_nova_apaga_a_anterior(exe, tmp_path):
    caminho, versao_antiga, _ = exe
    antiga = lancador.preparar(caminho)

    _lancador_falso(caminho)
    _app_falso(str(tmp_path / "ScoreCardApp"), texto="v2")
    versao_nova = empacotar.empacotar(str(tmp_path / "ScoreCardApp"), caminho)
    nova = lancador.preparar(caminho)

    assert versao_nova != versao_antiga
    assert not os.path.exists(antiga)
    with open(os.path.join(nova, "_internal", "ui", "index.html")) as fh:
        assert fh.read() == "v2"


def test_executavel_sem_app_dentro_e_recusado(tmp_path):
    caminho = str(tmp_path / "ScoreCard.exe")
    _lancador_falso(caminho)
    with pytest.raises(ValueError):
        lancador.localizar_app(caminho)
