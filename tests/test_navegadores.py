"""Escolha do navegador da automacao (navegadores.py): Edge, depois Chrome,
depois o Chromium embutido."""

import pytest

import navegadores


class _Chromium:
    """Imita playwright.chromium.launch: os canais em "quebrados" falham."""

    def __init__(self, quebrados=()):
        self.quebrados = set(quebrados)
        self.chamadas = []

    def launch(self, **kwargs):
        self.chamadas.append(kwargs.get("channel", "headless-shell"))
        if kwargs.get("channel", "headless-shell") in self.quebrados:
            raise RuntimeError(f"Chromium distribution '{kwargs.get('channel')}' is not found")
        return f"browser:{kwargs.get('channel', 'headless-shell')}"


def _playwright(chromium):
    return type("PW", (), {"chromium": chromium})()


@pytest.fixture(autouse=True)
def sem_escolha_anterior(monkeypatch):
    monkeypatch.setattr(navegadores, "_escolhido", None)
    monkeypatch.delenv("SCORECARD_NAVEGADOR", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE", raising=False)
    # Como fora do Windows: Edge e Chrome sao tentados abrindo.
    monkeypatch.setattr(navegadores.os, "name", "posix")


def test_o_edge_vem_primeiro():
    chromium = _Chromium()
    assert navegadores.lancar(_playwright(chromium)) == "browser:msedge"
    assert chromium.chamadas == ["msedge"]
    assert navegadores.nome_do_escolhido() == "Microsoft Edge"


def test_sem_edge_usa_o_chrome_e_depois_o_chromium():
    chromium = _Chromium(quebrados={"msedge"})
    assert navegadores.lancar(_playwright(chromium)) == "browser:chrome"

    navegadores._escolhido = None
    chromium = _Chromium(quebrados={"msedge", "chrome"})
    assert navegadores.lancar(_playwright(chromium)) == "browser:headless-shell"
    assert chromium.chamadas == ["msedge", "chrome", "headless-shell"]


def test_lembra_o_que_abriu_e_tenta_ele_primeiro():
    navegadores.lancar(_playwright(_Chromium(quebrados={"msedge"})))
    chromium = _Chromium()
    navegadores.lancar(_playwright(chromium))
    assert chromium.chamadas == ["chrome"]


def test_sem_nenhum_navegador_a_mensagem_diz_o_que_fazer(monkeypatch):
    monkeypatch.setattr(navegadores.sys, "frozen", True, raising=False)
    monkeypatch.setattr(navegadores, "chromium_embutido", lambda: False)
    with pytest.raises(navegadores.SemNavegador, match="Microsoft Edge"):
        navegadores.lancar(_playwright(_Chromium(quebrados={"msedge", "chrome"})))


def test_variavel_forca_um_navegador(monkeypatch):
    monkeypatch.setenv("SCORECARD_NAVEGADOR", "chrome")
    chromium = _Chromium()
    navegadores.lancar(_playwright(chromium))
    assert chromium.chamadas == ["chrome"]


def test_no_windows_so_tenta_o_que_esta_instalado(monkeypatch):
    monkeypatch.setattr(navegadores.os, "name", "nt")
    monkeypatch.setattr(navegadores, "_instalado", lambda chave: "C:/Chrome/chrome.exe" if chave == "chrome" else None)
    chromium = _Chromium()
    navegadores.lancar(_playwright(chromium))
    assert chromium.chamadas == ["chrome"]
    assert navegadores.descricao()["nome"] == "Google Chrome"
