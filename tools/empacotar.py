"""Ultimo passo do build: coloca o app dentro do ScoreCard.exe.

Chamado pelo build.spec depois que o PyInstaller gerou as duas partes:

- dist/ScoreCardApp/   o app em pasta (abre rapido, mas sao milhares de
                       arquivos);
- dist/ScoreCard.exe   o lancador, um arquivo so e pequeno.

Aqui a pasta vira um zip, e o zip entra dentro do lancador, logo antes
do pacote do PyInstaller, seguido do rodape que o lancador le (ver
lancador.py). No fim sobra so o dist/ScoreCard.exe — o unico arquivo
que se distribui.

A versao e um pedaco do hash do zip: muda sozinha a cada build com
alguma diferenca, e e ela que diz ao lancador se precisa descompactar
de novo.
"""

import hashlib
import os
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lancador  # noqa: E402

BLOCO = 4 * 1024 * 1024


def _zipar(pasta, destino):
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zipado:
        for raiz, pastas, arquivos in os.walk(pasta):
            pastas.sort()
            relativa = os.path.relpath(raiz, pasta)
            if relativa != "." and not pastas and not arquivos:
                zipado.write(raiz, relativa.replace(os.sep, "/") + "/")
            for nome in sorted(arquivos):
                caminho = os.path.join(raiz, nome)
                zipado.write(caminho, os.path.relpath(caminho, pasta).replace(os.sep, "/"))


def _hash(caminho):
    soma = hashlib.sha256()
    with open(caminho, "rb") as fh:
        for bloco in iter(lambda: fh.read(BLOCO), b""):
            soma.update(bloco)
    return soma.hexdigest()[:12]


def empacotar(pasta_app, caminho_lancador, manter_pasta=False):
    """Junta o app ao lancador, no lugar. Devolve a versao gravada."""
    zip_temporario = caminho_lancador + ".app.zip"
    novo = caminho_lancador + ".novo"
    try:
        print(f"[empacotar] zipando {pasta_app}...", flush=True)
        _zipar(pasta_app, zip_temporario)
        versao = _hash(zip_temporario)
        tamanho_zip = os.path.getsize(zip_temporario)

        with open(caminho_lancador, "rb") as fh:
            inicio_pacote = lancador.inicio_do_pacote_pyinstaller(fh)
            fh.seek(0)
            cabeca = fh.read(inicio_pacote)
            pacote = fh.read()

        with open(novo, "wb") as saida:
            saida.write(cabeca)
            with open(zip_temporario, "rb") as zipado:
                shutil.copyfileobj(zipado, saida, BLOCO)
            saida.write(lancador.RODAPE.pack(lancador.MARCA, tamanho_zip, versao.encode("ascii")))
            saida.write(pacote)
        if os.name != "nt":
            shutil.copymode(caminho_lancador, novo)
        os.replace(novo, caminho_lancador)
    finally:
        for resto in (zip_temporario, novo):
            if os.path.exists(resto):
                os.remove(resto)

    if not manter_pasta:
        shutil.rmtree(pasta_app, ignore_errors=True)

    # Confere o resultado lendo do jeito que o lancador vai ler.
    _, tamanho_lido, versao_lida = lancador.localizar_app(caminho_lancador)
    assert (tamanho_lido, versao_lida) == (tamanho_zip, versao), "empacotamento inconsistente"
    megas = os.path.getsize(caminho_lancador) / 1024 / 1024
    print(f"[empacotar] {caminho_lancador} pronto: versao {versao}, {megas:.0f} MB", flush=True)
    return versao
