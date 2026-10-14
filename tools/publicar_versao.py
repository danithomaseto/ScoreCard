"""Publica o ScoreCard.exe gerado na pasta do SharePoint, para o app de
todo mundo avisar que ha versao nova.

Depois do build.bat:

    python tools/publicar_versao.py                 (usa a pasta do SharePoint configurada no app)
    python tools/publicar_versao.py "C:\\...\\Score Card - Documentos"

Copia dist\\ScoreCard.exe para <pasta>\\_ScoreCard\\ScoreCard_<versao>.exe
e deixa so as duas versoes mais novas ali.
"""

import os
import shutil
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import atualizacao  # noqa: E402
import settings_store  # noqa: E402
import versao  # noqa: E402

GUARDADAS = 2


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else settings_store.get_sharepoint_folder()
    if not base or not os.path.isdir(base):
        sys.exit("Informe a pasta do SharePoint (ou configure-a no app antes).")
    exe = os.path.join(RAIZ, "dist", "ScoreCard.exe")
    if not os.path.isfile(exe):
        sys.exit("Nao achei dist\\ScoreCard.exe: rode o build.bat antes.")
    numero = versao.numero(RAIZ)
    destino_pasta = atualizacao.pasta(base)
    os.makedirs(destino_pasta, exist_ok=True)
    destino = os.path.join(destino_pasta, f"ScoreCard_{numero}.exe")
    shutil.copy2(exe, destino)
    print(f"Publicado: {destino}")

    publicadas = sorted(
        (atualizacao.numero(nome[len("ScoreCard_"):-len(".exe")]), nome)
        for nome in os.listdir(destino_pasta)
        if nome.startswith("ScoreCard_") and nome.endswith(".exe")
        and atualizacao.numero(nome[len("ScoreCard_"):-len(".exe")]))
    for _, nome in publicadas[:-GUARDADAS]:
        os.remove(os.path.join(destino_pasta, nome))
        print(f"Removida a antiga: {nome}")


if __name__ == "__main__":
    main()
