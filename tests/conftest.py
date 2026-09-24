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
