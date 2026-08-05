# -*- mode: python ; coding: utf-8 -*-
# Gera o ScoreCard.exe. Rode com: pyinstaller build.spec
# (precisa ser executado no Windows - o .exe nao pode ser gerado a
# partir de outro sistema operacional).
#
# Modo "one-folder": o resultado fica em dist/ScoreCard/ (uma pasta com
# o ScoreCard.exe e os arquivos de apoio ao lado). Mais confiavel e mais
# rapido pra abrir do que o modo "arquivo unico", especialmente com o
# Playwright/Chromium empacotado junto.

import os

from PyInstaller.utils.hooks import collect_all

# Defina SCORECARD_BUILD_CONSOLE=1 antes de rodar o build pra gerar uma
# versao com console visivel (mostra prints e tracebacks de erro) — util
# so pra diagnosticar problemas. A versao final/normal fica sem console.
SHOW_CONSOLE = os.environ.get("SCORECARD_BUILD_CONSOLE") == "1"

datas = [("ui", "ui")]
binaries = []
hiddenimports = []

# Garante que o driver interno do Playwright (usado tanto pra rodar o
# Chromium quanto pro download automatico na primeira execucao) vai
# junto no pacote.
pw_datas, pw_binaries, pw_hiddenimports = collect_all("playwright")
datas += pw_datas
binaries += pw_binaries
hiddenimports += pw_hiddenimports

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
    [],
    exclude_binaries=True,
    name="ScoreCard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=SHOW_CONSOLE,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ScoreCard",
)
