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
