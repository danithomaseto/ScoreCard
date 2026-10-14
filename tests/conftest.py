"""Infraestrutura comum dos testes.

Os testes rodam a automacao de verdade (Playwright + Chromium) contra as
paginas de mock em tests/fixtures, que imitam a tela do Summary: login,
menu Reports, iframe de relatorios, filtros e exportacao. Assim da pra
validar uma mudanca sem depender da VPN nem do sistema real.

Requer o Chromium do Playwright instalado ("playwright install chromium").
Se voce tiver um Chromium em outro lugar, aponte a variavel de ambiente
PLAYWRIGHT_CHROMIUM_EXECUTABLE para ele.
"""

import os
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(REPO_ROOT))

# A automacao usa o Edge/Chrome da maquina quando existem (navegadores.py);
# os testes ficam no Chromium do Playwright, igual em toda maquina e no CI.
os.environ.setdefault("SCORECARD_NAVEGADOR", "chromium")

# Os testes trocam o HOME por uma pasta temporaria (dados_do_app_isolados).
# No Linux e no Mac o Playwright procura os navegadores dentro do HOME, entao
# o caminho de verdade fica fixado antes da troca. No Windows eles ficam no
# LOCALAPPDATA, que os testes nao mexem.
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
    if sys.platform.startswith("linux"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser("~/.cache/ms-playwright")
    elif sys.platform == "darwin":
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.expanduser("~/Library/Caches/ms-playwright")

# O pywebview so e usado pra abrir a janela do app e nao esta disponivel
# fora do Windows; um stub deixa api.py importavel nos testes.
if "webview" not in sys.modules:
    try:
        import webview  # noqa: F401
    except ImportError:
        stub = types.ModuleType("webview")
        stub.FOLDER_DIALOG = "FOLDER_DIALOG"
        sys.modules["webview"] = stub


def fixture_url(name):
    return f"file://{FIXTURES / name}"


def mock_operation(label, folder, page="login.html"):
    """Uma entrada de config/operations.py apontando para o mock."""
    return {
        "label": label,
        "login_url": fixture_url(page),
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": folder,
    }


@pytest.fixture
def operations():
    """Registra operacoes de mock e desfaz no fim do teste."""
    from config.operations import OPERATIONS

    added = []

    def register(key, label, folder, page="login.html"):
        OPERATIONS[key] = mock_operation(label, folder, page)
        added.append(key)
        return key

    yield register

    for key in added:
        OPERATIONS.pop(key, None)


@pytest.fixture
def sharepoint_dir(tmp_path):
    """Pasta temporaria no lugar da pasta do SharePoint."""
    folder = tmp_path / "sharepoint"
    folder.mkdir()
    return folder


@pytest.fixture
def isolated_history(tmp_path, monkeypatch):
    """Mantem o history.json do teste longe do arquivo real do usuario."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("HOME", str(tmp_path / "appdata"))
    import history_store

    return history_store


@pytest.fixture(autouse=True)
def dados_do_app_isolados(tmp_path, monkeypatch):
    """Todo teste roda com a pasta de dados do app numa pasta temporaria.

    Os stores (settings, historico, indicadores e headcount) acham o
    arquivo pelo APPDATA na hora de ler. Sem isto, um teste que monta a
    aba Inicio leria os gestores e as faltas de verdade de quem roda os
    testes — e poderia passar ou falhar conforme a maquina.
    """
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("HOME", str(tmp_path / "appdata"))
