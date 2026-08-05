import os
import sys

# Precisa vir ANTES de importar qualquer coisa que use subprocess (o
# Playwright abre um processo interno pra controlar o navegador). Numa
# build "sem console" do PyInstaller (windowed), sys.stdout/stderr/stdin
# ficam None — e isso trava o Playwright silenciosamente na hora de
# abrir o navegador, sem nenhum erro visivel. Ver:
# https://github.com/pyinstaller/pyinstaller/issues/6598 (mesmo padrao
# afeta qualquer lib que dependa de subprocess com stdio herdado).
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
if sys.stdin is None:
    sys.stdin = open(os.devnull, "r")

import webview

from api import Api


def resource_path(relative_path):
    """Resolve caminhos tanto rodando com 'python main.py' quanto
    rodando ja empacotado como .exe (PyInstaller extrai tudo pra uma
    pasta temporaria apontada por sys._MEIPASS)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def ensure_browser_installed():
    """Na primeira execucao, o Chromium que o Playwright usa ainda nao
    foi baixado. Detecta isso e baixa automaticamente, sem exigir que o
    usuario rode nenhum comando — só acontece uma vez, silenciosamente
    (pode demorar um pouco na primeira vez, dependendo da internet)."""
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser.close()
        return
    except Exception:
        pass

    print("Preparando o aplicativo pela primeira vez (baixando componentes)...")
    sys.argv = ["playwright", "install", "chromium"]
    from playwright.__main__ import main as playwright_cli_main

    try:
        playwright_cli_main()
    except SystemExit:
        pass


def main():
    ensure_browser_installed()

    api = Api()
    index_path = resource_path(os.path.join("ui", "index.html"))

    window = webview.create_window(
        "Score Card",
        index_path,
        js_api=api,
        width=980,
        height=700,
        min_size=(820, 600),
        resizable=True,
    )
    api.set_window(window)
    webview.start()


if __name__ == "__main__":
    main()
