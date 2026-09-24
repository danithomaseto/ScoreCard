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


def _chromium_ja_esta_no_pacote():
    """O .exe leva o Chromium embutido (ver build.spec). Esta funcao so
    confere se o binario esta no lugar, olhando o disco.

    Antes daqui saia um navegador de verdade, aberto e fechado so pra
    testar — o que custava alguns segundos em TODA abertura do
    programa, mesmo com o Chromium ali do lado. Ler o disco responde a
    mesma pergunta sem pagar esse preco.
    """
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        return os.path.isfile(os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"])

    raizes = []
    if hasattr(sys, "_MEIPASS"):
        raizes.append(os.path.join(sys._MEIPASS, "playwright", "driver", "package",
                                   ".local-browsers"))
    local = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if local:
        raizes.append(local)
    if os.environ.get("LOCALAPPDATA"):
        raizes.append(os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright"))

    for raiz in raizes:
        if not os.path.isdir(raiz):
            continue
        for nome in os.listdir(raiz):
            if not nome.startswith("chromium-"):
                continue
            for relativo in (("chrome-win", "chrome.exe"),
                             ("chrome-linux", "chrome"),
                             ("chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium")):
                if os.path.isfile(os.path.join(raiz, nome, *relativo)):
                    return True
    return False


def ensure_browser_installed():
    """Garante que o Chromium existe. No .exe ele vem embutido, entao
    isso e so uma conferencia de disco; rodando do codigo-fonte sem
    'playwright install chromium', baixa uma vez."""
    if _chromium_ja_esta_no_pacote():
        return

    print("Preparando o aplicativo pela primeira vez (baixando componentes)...")
    sys.argv = ["playwright", "install", "chromium"]
    from playwright.__main__ import main as playwright_cli_main

    try:
        playwright_cli_main()
    except SystemExit:
        pass


def fechar_splash():
    """Fecha a tela de abertura do PyInstaller, se houver. Ela aparece
    enquanto o .exe descompacta o conteudo (Chromium incluso), que e a
    parte demorada — sem ela o programa parece travado."""
    try:
        import pyi_splash  # so existe dentro do .exe com splash
    except ImportError:
        return
    try:
        pyi_splash.close()
    except Exception:
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
        # Cor de fundo mostrada por uma fracao de segundo antes da
        # pagina terminar de carregar, pra combinar com o tema escuro
        # em vez do branco padrao do pywebview.
        background_color="#0b0e1a",
    )
    api.set_window(window)
    # Fecha a tela de abertura quando a pagina terminar de carregar, e
    # nao antes: assim nao sobra um intervalo com nada na tela.
    try:
        window.events.loaded += fechar_splash
    except Exception:
        fechar_splash()
    webview.start()


if __name__ == "__main__":
    main()
