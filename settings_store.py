"""Configuracoes persistidas localmente (fora do codigo-fonte): o caminho
da pasta do SharePoint/OneDrive onde os relatorios sao salvos, os
gestores/turnos escondidos nas abas de resultado e as preferencias de
tela (tema, densidade, menu recolhido).
Cada usuario que roda o aplicativo tem o seu proprio arquivo, guardado
na pasta de dados do Windows (%APPDATA%).
"""

import json
import os

import arquivo_seguro

APP_NAME = "ScoreCard"


def _settings_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def _settings_path():
    return os.path.join(_settings_dir(), "settings.json")


def get_settings():
    path = _settings_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def save_settings(data):
    arquivo_seguro.gravar_json(_settings_path(), data)


def get_sharepoint_folder():
    return get_settings().get("sharepoint_base_dir")


def set_sharepoint_folder(folder):
    settings = get_settings()
    settings["sharepoint_base_dir"] = folder
    save_settings(settings)


# Gestores (ou turnos) que a pessoa escondeu nas abas Resultado Gestor e
# Resultado Turno, por operacao. Guarda os escondidos, e nao os
# escolhidos: um gestor novo que aparecer no Summary ja vem marcado.

def get_grupos_ocultos(dimensao, operacao):
    return list(get_settings().get("grupos_ocultos", {}).get(dimensao, {}).get(operacao, []))


def set_grupos_ocultos(dimensao, operacao, nomes):
    settings = get_settings()
    por_dimensao = settings.setdefault("grupos_ocultos", {}).setdefault(dimensao, {})
    por_dimensao[operacao] = sorted(set(nomes))
    save_settings(settings)


# Preferencias de tela: tema, densidade e menu recolhido. Ficam aqui, e
# nao no localStorage da pagina, porque a janela do app nao guarda o
# localStorage de uma abertura para a outra.
PREFERENCIAS = {
    "tema": ("escuro", ("escuro", "claro")),
    "densidade": ("confortavel", ("confortavel", "compacta")),
    "menu_recolhido": (False, (False, True)),
    # "leves" desliga as animacoes que so enfeitam (modo leve): notebook
    # fraco, Citrix/area de trabalho remota e projetor.
    "animacoes": ("completas", ("completas", "leves")),
}


def get_preferencias():
    guardadas = get_settings().get("preferencias") or {}
    return {chave: guardadas.get(chave, padrao) if guardadas.get(chave) in validos else padrao
            for chave, (padrao, validos) in PREFERENCIAS.items()}


def set_preferencia(chave, valor):
    if chave not in PREFERENCIAS:
        raise ValueError("Preferência inválida.")
    if valor not in PREFERENCIAS[chave][1]:
        raise ValueError("Valor inválido para a preferência.")
    settings = get_settings()
    settings.setdefault("preferencias", {})[chave] = valor
    save_settings(settings)
    return get_preferencias()


# O que a pessoa ja viu nesta maquina: a versao das novidades ("O que ha
# de novo") e o tour do primeiro uso (novidades.py).
def get_vistos():
    vistos = get_settings().get("vistos")
    vistos = vistos if isinstance(vistos, dict) else {}
    novidades = vistos.get("novidades")
    return {"novidades": novidades if isinstance(novidades, str) else "", "tour": vistos.get("tour") is True}


def marcar_visto(chave, valor):
    settings = get_settings()
    if not isinstance(settings.get("vistos"), dict):
        settings["vistos"] = {}
    settings["vistos"][chave] = valor
    save_settings(settings)


# Versao dos arquivos de dados: ate qual migracao (migracoes.py) esta
# maquina ja rodou.
def get_versao_dos_dados():
    try:
        return int(get_settings().get("versao_dos_dados") or 0)
    except (TypeError, ValueError):
        return 0


def set_versao_dos_dados(numero):
    settings = get_settings()
    settings["versao_dos_dados"] = int(numero)
    save_settings(settings)
