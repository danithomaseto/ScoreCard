"""Backup diario dos dados do app, com restauracao.

Na abertura do app, uma vez por dia, os arquivos de dados de
%APPDATA%\\ScoreCard (Headcount, Coverage, indicadores, historico,
configuracoes...) vao para um zip em %APPDATA%\\ScoreCard\\backups,
ScoreCard_AAAA-MM-DD.zip. Ficam os ultimos DIAS_GUARDADOS.

Restaurar deixa os arquivos de dados como estavam no zip escolhido (o
que nao existia naquele dia sai, e cada arquivo volta com a data dele).
Antes, o estado atual vai para um zip "antes-de-restaurar", para dar
para voltar. Os logs e a propria pasta de backups ficam de fora.

A data volta junto porque os lancamentos compartilhados (lancamentos.py)
usam a data dos arquivos: dado restaurado e dado antigo, e nao passa por
cima do que outras pessoas lancaram depois.
"""

import datetime
import logging
import os
import re
import tempfile
import zipfile

log = logging.getLogger("scorecard.backup")

APP_NAME = "ScoreCard"
DIAS_GUARDADOS = 7
PASTA = "backups"
_NOME = re.compile(r"^ScoreCard_(\d{4}-\d{2}-\d{2})(?:_(antes-de-restaurar-\d{6}))?\.zip$")


def _pasta_de_dados():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta = os.path.join(base, APP_NAME)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _pasta_de_backups():
    pasta = os.path.join(_pasta_de_dados(), PASTA)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _arquivos_de_dados():
    pasta = _pasta_de_dados()
    return sorted(nome for nome in os.listdir(pasta)
                  if nome.endswith(".json") and os.path.isfile(os.path.join(pasta, nome)))


def _gravar_zip(destino):
    """Zip com os .json de dados. Grava num temporario e troca no fim."""
    pasta = _pasta_de_dados()
    descritor, temporario = tempfile.mkstemp(suffix=".zip", dir=os.path.dirname(destino))
    os.close(descritor)
    try:
        with zipfile.ZipFile(temporario, "w", zipfile.ZIP_DEFLATED) as zf:
            for nome in _arquivos_de_dados():
                zf.write(os.path.join(pasta, nome), nome)
        os.replace(temporario, destino)
    except BaseException:
        try:
            os.remove(temporario)
        except OSError:
            pass
        raise
    return destino


def fazer(hoje=None, forcar=False):
    """O backup do dia, se ainda nao existe (ou se forcar). Apaga os mais
    antigos que DIAS_GUARDADOS. Devolve o caminho do zip ou None."""
    hoje = hoje or datetime.date.today()
    if not _arquivos_de_dados():
        return None
    destino = os.path.join(_pasta_de_backups(), f"ScoreCard_{hoje.isoformat()}.zip")
    if os.path.isfile(destino) and not forcar:
        return None
    _gravar_zip(destino)
    log.info("backup do dia gravado: %s", os.path.basename(destino))
    _apagar_antigos(hoje)
    return destino


def _apagar_antigos(hoje):
    limite = hoje - datetime.timedelta(days=DIAS_GUARDADOS - 1)
    for item in listar():
        if datetime.date.fromisoformat(item["dia"]) < limite:
            try:
                os.remove(item["caminho"])
            except OSError:
                pass


def listar():
    """Os backups, do mais novo ao mais antigo:
    [{"id", "dia", "quando", "arquivos", "tamanho", "caminho", "antes_de_restaurar"}]."""
    pasta = _pasta_de_backups()
    itens = []
    for nome in os.listdir(pasta):
        achado = _NOME.match(nome)
        if not achado:
            continue
        caminho = os.path.join(pasta, nome)
        try:
            with zipfile.ZipFile(caminho) as zf:
                arquivos = len(zf.namelist())
            estado = os.stat(caminho)
        except (OSError, zipfile.BadZipFile):
            continue
        itens.append({
            "id": nome,
            "dia": achado.group(1),
            "quando": datetime.datetime.fromtimestamp(estado.st_mtime).isoformat(timespec="seconds"),
            "arquivos": arquivos,
            "tamanho": estado.st_size,
            "caminho": caminho,
            "antes_de_restaurar": bool(achado.group(2)),
        })
    return sorted(itens, key=lambda item: (item["dia"], item["quando"]), reverse=True)


def restaurar(identificador, agora=None):
    """Troca os arquivos de dados pelos do backup. O estado atual vai antes
    para um zip "antes-de-restaurar" (que pode ser restaurado depois)."""
    agora = agora or datetime.datetime.now()
    escolhido = next((item for item in listar() if item["id"] == identificador), None)
    if not escolhido:
        raise ValueError("Backup não encontrado.")
    seguranca = os.path.join(_pasta_de_backups(),
                             f"ScoreCard_{agora.date().isoformat()}_antes-de-restaurar-{agora:%H%M%S}.zip")
    if _arquivos_de_dados():
        _gravar_zip(seguranca)

    pasta = _pasta_de_dados()
    with zipfile.ZipFile(escolhido["caminho"]) as zf:
        membros = [m for m in zf.infolist()
                   if m.filename.endswith(".json") and "/" not in m.filename and "\\" not in m.filename]
        nomes = [m.filename for m in membros]
        for membro in membros:
            descritor, temporario = tempfile.mkstemp(suffix=".json", dir=pasta)
            with os.fdopen(descritor, "wb") as fh:
                fh.write(zf.read(membro))
            data = datetime.datetime(*membro.date_time).timestamp()
            os.utime(temporario, (data, data))
            os.replace(temporario, os.path.join(pasta, membro.filename))
    for nome in _arquivos_de_dados():
        if nome not in nomes:
            os.remove(os.path.join(pasta, nome))
    log.info("backup %s restaurado (%d arquivos)", identificador, len(nomes))
    return {"restaurados": len(nomes), "seguranca": os.path.basename(seguranca)}


def ultimo():
    itens = [item for item in listar() if not item["antes_de_restaurar"]]
    return itens[0] if itens else None
