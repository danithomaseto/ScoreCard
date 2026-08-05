# -*- mode: python ; coding: utf-8 -*-
# Gera o ScoreCard.exe. Rode com: pyinstaller build.spec
# (precisa ser executado no Windows - o .exe nao pode ser gerado a
# partir de outro sistema operacional).

from PyInstaller.utils.hooks import collect_all

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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
