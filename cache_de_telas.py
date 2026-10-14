"""Telas montadas guardadas em memoria ate os dados mudarem.

Montar uma aba (Inicio, Coverage, Headcount, Resultado Gestor/Turno,
Horas Indiretas) le os arquivos de dados inteiros e refaz as contas.
Com meses de extracoes de varias operacoes isso pesa, e a tela pede a
mesma coisa varias vezes (voltar a uma aba, trocar o filtro e voltar).

Cada resultado fica guardado com a "assinatura" dos dados do momento:
o numero de gravacoes deste app (arquivo_seguro.gravacoes), o tamanho e
a data de cada arquivo de %APPDATA%\\ScoreCard (pega mudanca de fora,
como restaurar um backup) e o dia de hoje (semana em andamento, ciclo
ate ontem). Qualquer diferenca e a tela e montada de novo.
"""

import datetime
import functools
import os
import threading
from collections import OrderedDict

import arquivo_seguro

APP_NAME = "ScoreCard"
LIMITE = 48  # telas guardadas; acima disso sai a usada ha mais tempo

_guardadas = OrderedDict()
_trava = threading.Lock()
estatisticas = {"acertos": 0, "montagens": 0}


def _pasta_de_dados():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def _hoje():
    return datetime.date.today()


def assinatura():
    arquivos = []
    try:
        with os.scandir(_pasta_de_dados()) as itens:
            for item in itens:
                if item.name.endswith(".json") and item.is_file():
                    estado = item.stat()
                    arquivos.append((item.name, estado.st_mtime_ns, estado.st_size))
    except OSError:
        pass
    return (arquivo_seguro.gravacoes, _hoje(), tuple(sorted(arquivos)))


def limpar():
    with _trava:
        _guardadas.clear()


def guardada(funcao):
    """Decorador dos metodos get_* da Api. O resultado nao pode ser
    alterado por quem recebe (a tela recebe uma copia, em JSON)."""
    @functools.wraps(funcao)
    def embrulho(*args, **kwargs):
        chave = (funcao.__name__, repr(args[1:]), repr(sorted(kwargs.items())), _pasta_de_dados())
        agora = assinatura()
        with _trava:
            achada = _guardadas.get(chave)
            if achada and achada[0] == agora:
                _guardadas.move_to_end(chave)
                estatisticas["acertos"] += 1
                return achada[1]
        valor = funcao(*args, **kwargs)
        with _trava:
            estatisticas["montagens"] += 1
            if agora == assinatura():  # nada gravou enquanto montava
                _guardadas[chave] = (agora, valor)
                _guardadas.move_to_end(chave)
                while len(_guardadas) > LIMITE:
                    _guardadas.popitem(last=False)
        return valor
    return embrulho
