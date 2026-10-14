"""Aviso de versao nova, pela pasta do SharePoint.

Quem gera uma versao publica o .exe na pasta do SharePoint, em
<pasta>\\_ScoreCard\\ScoreCard_V.01.2.exe (tools/publicar_versao.py faz
isso). Todo mundo usa a mesma pasta: o app compara a versao publicada
com a sua e avisa quando ha uma mais nova — versoes antigas apagam o
historico da pasta e nao enxergam os lancamentos compartilhados.
"""

import os
import re

PASTA = "_ScoreCard"
_NOME = re.compile(r"^ScoreCard[_ ]?(V\.\d{2}\.\d)\.exe$", re.IGNORECASE)
_NUMERO = re.compile(r"^V\.(\d{2})\.(\d)$", re.IGNORECASE)


def numero(versao):
    """"V.01.2" -> (1, 2); None fora do formato."""
    achado = _NUMERO.match(versao or "")
    return (int(achado.group(1)), int(achado.group(2))) if achado else None


def pasta(base):
    return os.path.join(base, PASTA)


def publicada(base):
    """{"versao", "caminho"} do .exe mais novo publicado, ou None."""
    if not base:
        return None
    try:
        nomes = os.listdir(pasta(base))
    except OSError:
        return None
    melhores = []
    for nome in nomes:
        achado = _NOME.match(nome)
        if achado and numero(achado.group(1).upper()):
            versao = achado.group(1).upper()
            melhores.append((numero(versao), versao, os.path.join(pasta(base), nome)))
    if not melhores:
        return None
    _, versao, caminho = max(melhores)
    return {"versao": versao, "caminho": caminho}


def verificar(base, atual):
    """{"atual", "nova" (ou None), "pasta"}: nova so quando a publicada e
    mais nova que a deste app."""
    achada = publicada(base)
    nova = None
    if achada and numero(atual) and numero(achada["versao"]) > numero(atual):
        nova = achada["versao"]
    return {"atual": atual, "nova": nova, "pasta": pasta(base) if base else None,
            "publicada": achada["versao"] if achada else None}
