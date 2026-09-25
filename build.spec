# -*- mode: python ; coding: utf-8 -*-
# Gera o ScoreCard.exe. Rode com: pyinstaller build.spec --noconfirm
# (precisa ser executado no Windows - o .exe nao pode ser gerado a
# partir de outro sistema operacional).
#
# Continua sendo UM arquivo so para distribuir (dist\ScoreCard.exe), mas
# montado em tres etapas:
#
#   1. o app em modo "pasta" (dist\ScoreCardApp), que abre rapido;
#   2. um lancador pequeno em modo "arquivo unico" (dist\ScoreCard.exe);
#   3. a pasta do app vai para dentro do lancador (tools/empacotar.py).
#
# Na primeira abertura de cada versao, o lancador descompacta o app em
# %LOCALAPPDATA%\ScoreCard\app-<versao>; nas seguintes, so abre. Antes,
# o "arquivo unico" puro descompactava tudo (Chromium incluso) a cada
# abertura — era isso que deixava o programa lento pra abrir. Detalhes
# em lancador.py.

import json
import os
import sys

from PyInstaller.utils.hooks import collect_all

sys.path.insert(0, SPECPATH)

# Defina SCORECARD_BUILD_CONSOLE=1 antes de rodar o build pra gerar uma
# versao com console visivel (mostra prints e tracebacks de erro) — util
# so pra diagnosticar problemas. A versao final/normal fica sem console.
SHOW_CONSOLE = os.environ.get("SCORECARD_BUILD_CONSOLE") == "1"

# Por padrao vai embutido so o chromium-headless-shell, feito pra rodar
# sem janela, com mais ou menos metade do tamanho do Chromium completo.
# SCORECARD_BUILD_FULL_CHROMIUM=1 embute o completo tambem — so e
# preciso pra ver a automacao na tela (SCORECARD_HEADLESS=0).
FULL_CHROMIUM = os.environ.get("SCORECARD_BUILD_FULL_CHROMIUM") == "1"

ICONE = "ui/assets/scorecard.ico"

datas = [("ui", "ui")]
binaries = []
hiddenimports = []

# Garante que o driver interno do Playwright (usado pra controlar o
# Chromium) vai junto no pacote.
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")
datas += pw_datas
binaries += pw_binaries
hiddenimports += pw_hiddenimports

# Leitura do relatorio baixado: o openpyxl le .xlsx e o xlrd le o .xls
# antigo, que e o que o Summary entrega hoje. Os dois carregam parte
# dos seus modulos por nome, em tempo de execucao, e o PyInstaller nao
# enxerga esse tipo de import sozinho — entao a coleta vai explicita.
# Sem isso o .exe abre normalmente e so quebra na hora de ler.
for pacote in ("openpyxl", "xlrd"):
    pk_datas, pk_binaries, pk_hiddenimports = collect_all(pacote)
    datas += pk_datas
    binaries += pk_binaries
    hiddenimports += pk_hiddenimports


def revisoes_esperadas():
    """Pasta de cada navegador que ESTA versao do Playwright procura
    (ex.: chromium_headless_shell-1243), lida do browsers.json dele.

    Embutir so essas evita levar junto revisoes antigas que ficaram no
    cache de builds anteriores — cada uma e algumas centenas de MB que
    o app nunca usaria."""
    import playwright

    caminho = os.path.join(os.path.dirname(playwright.__file__), "driver", "package", "browsers.json")
    with open(caminho, encoding="utf-8") as fh:
        navegadores = {b["name"]: b["revision"] for b in json.load(fh)["browsers"]}
    pastas = [f"chromium_headless_shell-{navegadores['chromium-headless-shell']}"]
    if FULL_CHROMIUM:
        pastas.append(f"chromium-{navegadores['chromium']}")
    return pastas


def find_playwright_chromium():
    """Localiza o Chromium ja baixado nesta maquina (via 'playwright
    install chromium', rodado antes deste build) e devolve como entrada
    de datas do PyInstaller, pra ir embutido no app.

    Baixar o navegador na primeira execucao do usuario final se mostrou
    pouco confiavel rodando de dentro do app ja empacotado (o driver do
    Playwright nao consegue completar o download nesse contexto). Em
    vez disso, o Chromium vai junto no pacote, pronto pra usar — o
    usuario final nunca precisa baixar nada.
    """
    cache_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        cache_dir = os.environ["PLAYWRIGHT_BROWSERS_PATH"]
    entries = []
    faltando = []
    for nome in revisoes_esperadas():
        full_path = os.path.join(cache_dir, nome)
        if os.path.isdir(full_path):
            entries.append((full_path, f"playwright/driver/package/.local-browsers/{nome}"))
        else:
            faltando.append(nome)
    if faltando:
        raise SystemExit(
            f"Nao encontrei {', '.join(faltando)} em {cache_dir}. Rode "
            "'python -m playwright install chromium' antes de gerar o .exe."
        )
    return entries


datas += find_playwright_chromium()

# ---------------- 1. O app, em pasta ----------------

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

app_exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ScoreCardApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX comprime cada binario e o descompacta em memoria a cada
    # abertura: custa mais tempo de abertura do que economiza de espaco.
    upx=False,
    console=SHOW_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICONE,
)
app_pasta = COLLECT(
    app_exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="ScoreCardApp",
)

# ---------------- 2. O lancador, arquivo unico ----------------

lanc = Analysis(
    ["lancador.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
lanc_pyz = PYZ(lanc.pure)

# Tela de abertura: aparece assim que o ScoreCard.exe roda e fica ate a
# janela do app carregar (o app avisa o lancador). Na primeira abertura
# de uma versao, mostra o andamento da descompactacao no rodape.
#
# Precisa vir DEPOIS da Analysis: o Splash usa binaries e datas dela pra
# localizar as bibliotecas que desenham a janelinha.
splash = Splash(
    "ui/assets/splash.png",
    binaries=lanc.binaries,
    datas=lanc.datas,
    text_pos=(16, 250),
    text_size=9,
    text_color="#8a93a8",
    text_default="",
    always_on_top=False,
)

lanc_exe = EXE(
    lanc_pyz,
    lanc.scripts,
    splash,
    splash.binaries,
    lanc.binaries,
    lanc.datas,
    [],
    name="ScoreCard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICONE,
)

# ---------------- 3. O app dentro do lancador ----------------

from tools.empacotar import empacotar  # noqa: E402

empacotar(os.path.join(DISTPATH, "ScoreCardApp"), lanc_exe.name)
