"""Imagem da tabela da Inicio (botao Imagem): o PNG e desenhado na tela
(ui/js/15-imagem.js) e, quando nao da para copiar ou a pessoa pede o
arquivo (Shift + clique), vem para ca e vai para a pasta Downloads.

So entra PNG de verdade (pela assinatura do arquivo) e de tamanho
razoavel: o conteudo vem da pagina e nao pode virar qualquer arquivo no
disco. O nome e montado aqui, so com letras, numeros, _ e -.
"""

import base64
import binascii
import datetime
import os
import re

import diagnostico

ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"
LIMITE = 20 * 1024 * 1024


def nome_do_arquivo(nome, agora=None):
    """"Hughes Setembro/2026" -> "ScoreCard_Hughes_Setembro_2026_20261014_153000.png"."""
    limpo = re.sub(r"[^A-Za-z0-9_-]+", "_", str(nome or "")).strip("_")[:60] or "tabela"
    agora = agora or datetime.datetime.now()
    return f"ScoreCard_{limpo}_{agora:%Y%m%d_%H%M%S}.png"


def salvar_png(nome, conteudo_base64, destino=None, agora=None):
    """Grava o PNG (base64, com ou sem o "data:image/png;base64,") e
    devolve o caminho. ValueError se nao for um PNG valido."""
    if not isinstance(conteudo_base64, str):
        raise ValueError("Imagem inválida.")
    if conteudo_base64.startswith("data:"):
        conteudo_base64 = conteudo_base64.split(",", 1)[-1]
    if len(conteudo_base64) > LIMITE * 4 // 3 + 4:
        raise ValueError("Imagem grande demais.")
    try:
        dados = base64.b64decode(conteudo_base64, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Imagem inválida.") from None
    if not dados.startswith(ASSINATURA_PNG):
        raise ValueError("Imagem inválida.")
    destino = destino or diagnostico.pasta_de_destino()
    caminho = os.path.join(destino, nome_do_arquivo(nome, agora))
    with open(caminho, "wb") as fh:
        fh.write(dados)
    return caminho
