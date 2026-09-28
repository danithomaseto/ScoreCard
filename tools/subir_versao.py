"""Sobe o numero da versao: V.01.0 -> V.01.1 ... V.01.9 -> V.02.0.

Rode antes do build de uma versao nova:

    python tools/subir_versao.py

O numero fica no arquivo VERSAO, na raiz do projeto, e aparece no
rodape do app.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import versao  # noqa: E402


def main():
    atual = versao.numero(RAIZ)
    nova = versao.proxima(atual)
    with open(os.path.join(RAIZ, versao.ARQUIVO_DO_NUMERO), "w", encoding="utf-8") as fh:
        fh.write(nova + "\n")
    print(f"Versao: {atual} -> {nova}")


if __name__ == "__main__":
    main()
