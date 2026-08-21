# -*- mode: python ; coding: utf-8 -*-
# Gera o ScoreCard.exe. Rode com: pyinstaller build.spec
# (precisa ser executado no Windows - o .exe nao pode ser gerado a
# partir de outro sistema operacional).
#
# Modo "one-file": todo mundo (codigo, interface, Chromium) fica
# compactado dentro de UM UNICO ScoreCard.exe — nada de pasta "dist"
# junto pra distribuir. A troca: como o Chromium embutido e grande, o
# .exe precisa descompactar tudo numa pasta temporaria a CADA abertura
# (nao so na primeira vez), entao o programa demora mais pra iniciar do
# que no modo "pasta". Foi uma escolha deliberada, priorizando
# distribuicao (um arquivo so) sobre velocidade de abertura.

import os

from PyInstaller.utils.hooks import collect_all

# Defina SCORECARD_BUILD_CONSOLE=1 antes de rodar o build pra gerar uma
# versao com console visivel (mostra prints e tracebacks de erro) — util
# so pra diagnosticar problemas. A versao final/normal fica sem console.
SHOW_CONSOLE = os.environ.get("SCORECARD_BUILD_CONSOLE") == "1"

datas = [("ui", "ui")]
binaries = []
hiddenimports = []

# Garante que o driver interno do Playwright (usado pra controlar o
# Chromium) vai junto no pacote.
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")
datas += pw_datas
binaries += pw_binaries
hiddenimports += pw_hiddenimports


def find_playwright_chromium():
    """Localiza o Chromium ja baixado nesta maquina (via 'playwright
    install chromium', rodado antes deste build) e devolve como entrada
    de datas do PyInstaller, pra ir embutido dentro do .exe.

    Baixar o navegador na primeira execucao do usuario final se mostrou
    pouco confiavel rodando de dentro do app ja empacotado (o driver do
    Playwright nao consegue completar o download nesse contexto). Em
    vez disso, o Chromium vai junto no pacote, pronto pra usar — o
    usuario final nunca precisa baixar nada.
    """
    cache_dir = os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright")
    entries = []
    if os.path.isdir(cache_dir):
        for name in os.listdir(cache_dir):
            full_path = os.path.join(cache_dir, name)
            # So o Chromium "completo" (channel="chromium" no codigo) —
            # nao precisamos do chromium_headless_shell.
            if name.startswith("chromium-") and os.path.isdir(full_path):
                entries.append((full_path, f"playwright/driver/package/.local-browsers/{name}"))
    return entries


chromium_datas = find_playwright_chromium()
if not chromium_datas:
    raise SystemExit(
        "Nenhum Chromium do Playwright encontrado em "
        "%LOCALAPPDATA%\\ms-playwright. Rode 'python -m playwright "
        "install chromium' antes de gerar o .exe."
    )
datas += chromium_datas

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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ScoreCard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=SHOW_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
