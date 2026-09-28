"""Checagem rapida de rede antes de abrir o navegador.

Sem VPN, o servidor do BlueYonder nao responde e a automacao so
descobria isso no timeout do login, depois de abrir o navegador — meio
minuto por operacao. Aqui uma conexao simples na porta do servidor
responde em segundos se da pra chegar nele.

Se algum dia a checagem atrapalhar (rede que so libera o navegador, por
exemplo), SCORECARD_SEM_CHECAGEM_VPN=1 desliga.
"""

import os
import socket
from urllib.parse import urlsplit

TEMPO_LIMITE = 4


def destino(url):
    """(host, porta) de uma URL http/https, ou None (ex.: file://)."""
    partes = urlsplit(url or "")
    if partes.scheme not in ("http", "https") or not partes.hostname:
        return None
    porta = partes.port or (443 if partes.scheme == "https" else 80)
    return partes.hostname, porta


def alcancavel(url, tempo_limite=TEMPO_LIMITE):
    """True se da pra abrir conexao com o servidor da URL."""
    if os.environ.get("SCORECARD_SEM_CHECAGEM_VPN") == "1":
        return True
    alvo = destino(url)
    if alvo is None:
        return True  # nada de rede para checar
    try:
        with socket.create_connection(alvo, timeout=tempo_limite):
            return True
    except OSError:
        return False


def mensagem(url):
    host = (destino(url) or ("o servidor", 0))[0]
    return (
        f"Sem conexão com o servidor da operação ({host}). "
        "Confira se a VPN da DHL está conectada e tente de novo."
    )
