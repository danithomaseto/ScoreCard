"""tools/build.py: a causa provavel de cada erro comum do build no Windows."""

import os

import pytest

from tools import build


@pytest.mark.parametrize("saida, trecho", [
    ("ERROR: Could not find a version that satisfies the requirement pythonnet", "Python 3.12"),
    ("ERROR: Your platform does not support the splash screen feature, since tkinter is not installed.", "tcl/tk"),
    ("SystemExit: Nao encontrei chromium_headless_shell-1243 em C:\\...", "Chromium"),
    ("PermissionError: [WinError 5] Access is denied: 'dist\\\\ScoreCard.exe'", "Feche o ScoreCard.exe"),
    ("OSError: [WinError 32] The process cannot access the file", "preso"),
    ("ssl.SSLCertVerificationError: certificate verify failed", "proxy"),
])
def test_cada_erro_comum_tem_a_causa_e_o_que_fazer(saida, trecho):
    assert trecho in build.dica_para(saida)


def test_erro_desconhecido_nao_inventa_causa():
    assert build.dica_para("Traceback: algo totalmente novo") is None


def test_build_bat_chama_o_build_py_e_para_no_erro():
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(raiz, "build.bat"), encoding="utf-8") as fh:
        bat = fh.read()
    assert 'cd /d "%~dp0"' in bat
    assert "tools\\build.py" in bat
    assert "if errorlevel 1 goto erro" in bat


# ---------------- O dist com um arquivo so ----------------

@pytest.fixture
def dist(tmp_path, monkeypatch):
    pasta = tmp_path / "dist"
    monkeypatch.setattr(build, "DIST", str(pasta))
    monkeypatch.setattr(build, "LOG", str(tmp_path / "build.log"))
    monkeypatch.setattr(build, "EXECUTAVEL", "ScoreCard.exe")
    return pasta


def _gerado(tmp_path, conteudo=b"novo"):
    caminho = tmp_path / "saida" / "ScoreCard.exe"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)
    return str(caminho)


def test_dist_fica_so_com_o_exe(tmp_path, dist):
    # Como no print: a pasta do app em pasta (ScoreCardApp com _internal)
    # sobrando ao lado do .exe antigo, com arquivo somente leitura.
    (dist / "ScoreCardApp" / "_internal").mkdir(parents=True)
    (dist / "ScoreCardApp" / "ScoreCardApp.exe").write_bytes(b"x")
    dll = dist / "ScoreCardApp" / "_internal" / "python312.dll"
    dll.write_bytes(b"x")
    os.chmod(dll, 0o444)
    (dist / "ScoreCard.exe").write_bytes(b"antigo")
    (dist / "ScoreCard.exe.novo").write_bytes(b"resto de build interrompido")

    sobras = build.colocar_no_dist(_gerado(tmp_path))

    assert sobras == []
    assert os.listdir(dist) == ["ScoreCard.exe"]
    assert (dist / "ScoreCard.exe").read_bytes() == b"novo"


def test_dist_criado_do_zero(tmp_path, dist):
    build.colocar_no_dist(_gerado(tmp_path))
    assert os.listdir(dist) == ["ScoreCard.exe"]


def test_falha_ao_copiar_mantem_o_exe_antigo(tmp_path, dist):
    dist.mkdir()
    (dist / "ScoreCard.exe").write_bytes(b"antigo")
    with pytest.raises(build.BuildFalhou):
        build.colocar_no_dist(str(tmp_path / "nao-existe.exe"))
    assert os.listdir(dist) == ["ScoreCard.exe"]
    assert (dist / "ScoreCard.exe").read_bytes() == b"antigo"


def test_trabalho_fora_da_pasta_do_projeto_e_sobras_antigas_apagadas(tmp_path, monkeypatch):
    # A pasta de trabalho fica fora do projeto (que costuma estar no OneDrive).
    assert not os.path.abspath(build.TEMPORARIA).startswith(build.RAIZ + os.sep)

    antigas = [tmp_path / "build", tmp_path / "dist_novo" / "ScoreCardApp", tmp_path / "dist_antigo"]
    for pasta in antigas:
        pasta.mkdir(parents=True)
        (pasta / "arquivo").write_bytes(b"x")
    monkeypatch.setattr(build, "SOBRAS_ANTIGAS", [str(tmp_path / n) for n in ("build", "dist_novo", "dist_antigo")])
    monkeypatch.setattr(build, "LOG", str(tmp_path / "build.log"))
    build.limpar_sobras_antigas()
    assert sorted(os.listdir(tmp_path)) == []
