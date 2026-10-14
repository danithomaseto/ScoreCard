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

import logging

import instancia_unica
import registro

registro.configurar()
log = logging.getLogger("scorecard")

import webview  # noqa: E402 - depois do log, para registrar erro de import

from api import Api  # noqa: E402
import backup  # noqa: E402
import migracoes  # noqa: E402
import navegadores  # noqa: E402


def resource_path(relative_path):
    """Resolve caminhos tanto rodando com 'python main.py' quanto
    rodando ja empacotado como .exe (PyInstaller extrai tudo pra uma
    pasta temporaria apontada por sys._MEIPASS)."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)


def ensure_browser_installed():
    """A automacao usa o Edge (ou o Chrome) da maquina; o .exe completo
    leva tambem um Chromium (ver navegadores.py). So rodando do
    codigo-fonte, sem nenhum dos tres, baixa o Chromium uma vez."""
    if getattr(sys, "frozen", False) or navegadores.descricao():
        return

    print("Preparando o aplicativo pela primeira vez (baixando componentes)...")
    sys.argv = ["playwright", "install", "chromium"]
    from playwright.__main__ import main as playwright_cli_main

    try:
        playwright_cli_main()
    except SystemExit:
        pass


def fechar_splash():
    """Chamado quando a janela termina de carregar: avisa o lancador
    (ScoreCard.exe), que mantem a tela de abertura na frente ate aqui,
    e fecha a tela de abertura propria, se este executavel tiver uma."""
    log.info("janela carregada")
    sinal = os.environ.pop("SCORECARD_SINAL_PRONTO", None)
    if sinal:
        try:
            with open(sinal, "w", encoding="utf-8") as fh:
                fh.write("ok")
        except OSError:
            pass  # sem o aviso o lancador so espera um pouco mais

    if "_PYI_SPLASH_IPC" not in os.environ:
        return  # sem tela de abertura propria (aberto pelo lancador)
    try:
        import pyi_splash  # so existe dentro do .exe com splash
    except ImportError:
        return
    try:
        pyi_splash.close()
    except Exception:
        pass


AVISO_AO_FECHAR = (
    "Há uma extração em andamento.\n\n"
    "Se fechar agora, o download fica pela metade e a extração não é concluída.\n\n"
    "Clique em OK para fechar mesmo assim ou em Cancelar para continuar."
)


def main():
    log.info("Score Card aberto (%s)", sys.executable if getattr(sys, "frozen", False) else "codigo-fonte")
    # O lancador ja confere isso antes; aqui cobre duas aberturas quase
    # juntas e o app aberto direto (codigo-fonte ou ScoreCardApp.exe).
    if not instancia_unica.segurar():
        log.info("ja existe uma janela aberta; trazendo para a frente")
        instancia_unica.trazer_para_frente()
        return
    ensure_browser_installed()
    # Backup do dia antes de qualquer conserto mexer nos dados, e depois os
    # consertos no que ja esta gravado, uma vez cada (migracoes.py).
    try:
        backup.fazer()
    except Exception:  # noqa: BLE001 - sem backup o app abre igual
        log.exception("não consegui fazer o backup do dia")
    migracoes.migrar()

    api = Api()
    index_path = resource_path(os.path.join("ui", "index.html"))

    window = webview.create_window(
        "Score Card",
        index_path,
        js_api=api,
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
        # Abre ocupando a tela: a aba Inicio e uma tabela larga, e a 980 px
        # o mes e o pico ficavam escondidos. Ao restaurar a janela, volta
        # para 1280 x 800.
        maximized=True,
        # Cor de fundo mostrada por uma fracao de segundo antes da
        # pagina terminar de carregar, pra combinar com o tema escuro
        # em vez do branco padrao do pywebview.
        background_color="#0b0e1a",
        # So aparece enquanto uma extracao roda: a api liga e desliga o
        # confirm_close da janela (Api._extraindo).
        localization={"global.quitConfirmation": AVISO_AO_FECHAR},
    )
    api.set_window(window)
    # Fecha a tela de abertura quando a pagina terminar de carregar, e
    # nao antes: assim nao sobra um intervalo com nada na tela.
    try:
        window.events.loaded += fechar_splash
    except Exception:
        fechar_splash()
    webview.start()


def autoteste(destino=None):
    """ScoreCardApp --autoteste [arquivo]: confere, sem abrir janela, que o
    pacote tem tudo o que o app usa (o build roda isto antes de juntar o
    app ao lancador; ver build.spec). Importa os modulos que so carregam
    na hora de extrair ou ler um relatorio, faz uma planilha de ida e
    volta e confere os arquivos da tela e o driver do Playwright.
    Devolve 0 se esta tudo certo."""
    import importlib
    import re
    import tempfile

    problemas = []
    modulos = ("api", "automation.generic", "automation.base", "indicators.reader", "indicators.faltas",
               "indicators.pico", "indicators.coverage", "indicators.grupos", "indicators.indiretas",
               "lancamentos", "arquivos_sharepoint", "diagnostico", "navegadores", "openpyxl", "xlrd",
               "concurrent.futures", "playwright.sync_api", "webview")
    for nome in modulos:
        try:
            importlib.import_module(nome)
        except Exception as exc:  # noqa: BLE001
            problemas.append(f"import {nome}: {exc}")
    try:
        import openpyxl

        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "teste.xlsx")
            planilha = openpyxl.Workbook()
            planilha.active["A1"] = "ok"
            planilha.save(caminho)
            if openpyxl.load_workbook(caminho, read_only=True).active["A1"].value != "ok":
                problemas.append("openpyxl: ida e volta da planilha")
    except Exception as exc:  # noqa: BLE001
        problemas.append(f"openpyxl: {exc}")
    try:
        from playwright._impl._driver import compute_driver_executable

        driver = compute_driver_executable()
        for caminho in (driver if isinstance(driver, tuple) else (driver,)):
            if not os.path.isfile(caminho):
                problemas.append(f"driver do Playwright sem {caminho}")
    except Exception as exc:  # noqa: BLE001
        problemas.append(f"driver do Playwright: {exc}")
    pagina = resource_path(os.path.join("ui", "index.html"))
    try:
        with open(pagina, encoding="utf-8") as fh:
            html = fh.read()
        for arquivo in re.findall(r'(?:src|href)="((?:js|css|assets)/[^"]+)"', html):
            if not os.path.isfile(resource_path(os.path.join("ui", arquivo))):
                problemas.append(f"tela sem ui/{arquivo}")
    except OSError as exc:
        problemas.append(f"tela: {exc}")

    texto = "AUTOTESTE OK" if not problemas else "AUTOTESTE FALHOU\n" + "\n".join(problemas)
    if destino:
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write(texto + "\n")
    print(texto)
    return 0 if not problemas else 1


if __name__ == "__main__":
    if "--autoteste" in sys.argv:
        resto = sys.argv[sys.argv.index("--autoteste") + 1:]
        sys.exit(autoteste(resto[0] if resto else None))
    main()
