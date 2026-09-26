"""Gravacao dos arquivos de dados sem risco de corromper no meio.

Os stores (configuracoes, historico, indicadores, headcount) regravam o
arquivo inteiro a cada mudanca. Escrevendo direto por cima, um PC que
desliga ou trava no meio deixa o arquivo pela metade — o JSON nao abre
mais e o app volta zerado, sem gestores e sem indicadores.

Aqui o conteudo vai primeiro para um arquivo temporario na mesma pasta,
e so depois de gravado por completo no disco ele toma o lugar do
original, numa troca que o sistema faz de uma vez. Ou fica o arquivo
antigo inteiro, ou o novo inteiro; nunca um pedaco.
"""

import json
import os
import tempfile
import time


def gravar_json(caminho, dados, compacto=False):
    """compacto=True grava sem indentacao: para os arquivos grandes (a
    planilha de faltas fica guardada linha a linha no headcount.json),
    o arquivo fica bem menor e abre mais rapido a cada tela."""
    pasta = os.path.dirname(os.path.abspath(caminho))
    os.makedirs(pasta, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(prefix=".gravando-", suffix=".json", dir=pasta)
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as fh:
            if compacto:
                json.dump(dados, fh, ensure_ascii=False, separators=(",", ":"))
            else:
                json.dump(dados, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        _substituir(temporario, caminho)
    except BaseException:
        try:
            os.remove(temporario)
        except OSError:
            pass
        raise


def _substituir(origem, destino, tentativas=5):
    """os.replace com algumas tentativas: no Windows, antivirus ou
    OneDrive podem estar com o arquivo aberto por um instante, e a troca
    falha com PermissionError mesmo sem nada de errado."""
    for tentativa in range(tentativas):
        try:
            os.replace(origem, destino)
            return
        except PermissionError:
            if tentativa == tentativas - 1:
                raise
            time.sleep(0.05 * (tentativa + 1))
