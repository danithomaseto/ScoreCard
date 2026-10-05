"""Pacote de diagnostico para mandar a quem da suporte.

Um zip com o que explica um problema numa maquina: o log, a versao, o
ambiente (Windows, pastas, Chromium) e as ultimas extracoes. **Nao
leva credenciais nem dados das pessoas**: dos arquivos de dados vao so
tamanhos e contagens — nada de nomes de gestores, matriculas ou
faltas. O log ja e gravado sem usuario e senha (ver registro.py), e o
texto passa pelo mesmo filtro de novo antes de entrar no zip.
"""

import json
import os
import platform
import sys
import zipfile
from datetime import datetime

import registro
import versao

APP_NAME = "ScoreCard"


def _pasta_de_dados():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    return os.path.join(base, APP_NAME)


def pasta_de_destino():
    """Downloads do usuario, ou a pasta pessoal se nao houver."""
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    return downloads if os.path.isdir(downloads) else os.path.expanduser("~")


def _ler_json(nome):
    try:
        with open(os.path.join(_pasta_de_dados(), nome), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def _navegadores():
    raizes = []
    if hasattr(sys, "_MEIPASS"):
        raizes.append(os.path.join(sys._MEIPASS, "playwright", "driver", "package", ".local-browsers"))
    for variavel in ("PLAYWRIGHT_BROWSERS_PATH",):
        if os.environ.get(variavel):
            raizes.append(os.environ[variavel])
    if os.environ.get("LOCALAPPDATA"):
        raizes.append(os.path.join(os.environ["LOCALAPPDATA"], "ms-playwright"))
    achados = []
    for raiz in raizes:
        if os.path.isdir(raiz):
            achados += [f"{raiz}: {nome}" for nome in sorted(os.listdir(raiz)) if nome.startswith("chromium")]
    return achados or ["nenhum Chromium encontrado"]


def resumo():
    """O texto do info.txt: so contagens e tamanhos, nada pessoal."""
    info = versao.info()
    linhas = [
        f"Score Card - diagnostico gerado em {datetime.now():%d/%m/%Y %H:%M}",
        "",
        f"Versao: {info['versao']}  build: {info['build'] or '-'}  commit: {info['commit'] or '-'}",
        f"Windows: {platform.platform()}",
        f"Python: {platform.python_version()}  empacotado: {bool(getattr(sys, 'frozen', False))}",
        f"Executavel: {sys.executable}",
        "",
        "Arquivos de dados:",
    ]
    pasta = _pasta_de_dados()
    if os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            caminho = os.path.join(pasta, nome)
            if os.path.isfile(caminho):
                linhas.append(f"  {nome}: {os.path.getsize(caminho)} bytes")
    else:
        linhas.append("  (pasta de dados ainda nao existe)")

    pasta_sp = (_ler_json("settings.json") or {}).get("sharepoint_base_dir")
    linhas += ["", f"Pasta do SharePoint configurada: {'sim' if pasta_sp else 'nao'}"
               + (f" (existe: {'sim' if os.path.isdir(pasta_sp) else 'NAO'})" if pasta_sp else "")]

    headcount = _ler_json("headcount.json") or {}
    arquivo = headcount.get("arquivo") or {}
    linhas += [
        f"Gestores cadastrados: {len(headcount.get('gestores', []))}",
        f"Funcoes cadastradas: {len(headcount.get('funcoes', []))}",
        f"Planilha de faltas: {'sim, ' + str(len(arquivo.get('linhas', []))) + ' linhas' if arquivo else 'nao'}",
    ]

    indicadores = _ler_json("indicators.json") or {}
    linhas.append("Indicadores guardados (periodos por operacao):")
    for operacao, periodos in sorted(indicadores.items()):
        contagem = ", ".join(f"{p}={len(v)}" for p, v in sorted(periodos.items()))
        linhas.append(f"  {operacao}: {contagem}")

    horas_indiretas = _ler_json("indiretas.json") or {}
    linhas.append("Horas indiretas guardadas (semanas por operacao):")
    for operacao, semanas in sorted(horas_indiretas.items()):
        linhas.append(f"  {operacao}: {len(semanas)}")

    linhas += ["", "Chromium:"] + [f"  {n}" for n in _navegadores()]

    historico = _ler_json("history.json") or []
    linhas += ["", "Ultimas extracoes:"]
    for item in historico[:20]:
        linhas.append(
            f"  {item.get('timestamp', '')} {item.get('operation', '')} "
            f"{item.get('period_type', '')} {item.get('status', '')} "
            f"{item.get('duration_seconds', '')}s - {item.get('message', '')}"
        )
    return "\n".join(linhas)


def gerar(destino=None):
    """Grava o zip e devolve o caminho dele."""
    destino = destino or pasta_de_destino()
    os.makedirs(destino, exist_ok=True)
    caminho = os.path.join(destino, f"ScoreCard-diagnostico-{datetime.now():%Y%m%d-%H%M%S}.zip")
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zipado:
        zipado.writestr("info.txt", registro.limpar(resumo()))
        pasta_logs = registro.pasta()
        if os.path.isdir(pasta_logs):
            for nome in sorted(os.listdir(pasta_logs)):
                if nome.startswith("scorecard.log"):
                    with open(os.path.join(pasta_logs, nome), encoding="utf-8", errors="replace") as fh:
                        zipado.writestr(f"logs/{nome}", registro.limpar(fh.read()))
    return caminho
