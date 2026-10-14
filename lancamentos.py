"""Lancamentos digitados (Headcount e Coverage) compartilhados pela pasta
do SharePoint.

Os indicadores ja vem da pasta compartilhada (arquivos_sharepoint.py);
aqui vai o que e digitado: gestores e o quadro deles (HC, dias uteis,
horas/dia, faltas), as funcoes que contam como falta e, no Coverage, os
dias/horas por usuario e a sinergia. Com isso o presenteismo e o cubo
sao os mesmos para todo mundo.

Um arquivo por operacao, para o OneDrive nao brigar com edicoes de
operacoes diferentes:

    <pasta>\\<operacao>\\Lancamentos\\ScoreCard_lancamentos_<op>.json

Cada valor e uma "celula" com a data em que foi mudado; juntando duas
versoes, vale a mais recente de cada celula (e nao a do arquivo inteiro),
entao duas pessoas mexendo em gestores diferentes nao se atrapalham. O
que e apagado fica marcado como apagado (com data), para nao voltar. As
copias de conflito que o OneDrive cria ("..._swa-PC123.json") sao
juntadas e apagadas. Dois gestores com o mesmo nome na mesma operacao
(cadastrados por pessoas diferentes antes do compartilhamento) viram um
so — o de menor id —, com os valores mais recentes de cada um.

A copia local (headcount.json, coverage.json) continua sendo o que as
telas leem; este modulo junta a local com a da pasta, grava a da pasta e
traz para a local o que mudou. O ultimo estado junto fica em
%APPDATA%\\ScoreCard\\lancamentos.json: e com ele que se descobre o que
esta pessoa mudou desde a ultima vez.
"""

import datetime
import json
import logging
import os
import threading

import arquivo_seguro
import coverage_store
import headcount_store
from config.operations import OPERATIONS
from headcount import nome_comparavel

log = logging.getLogger("scorecard.lancamentos")

APP_NAME = "ScoreCard"
PASTA = "Lancamentos"
FORMATO = 1
CAMPOS_DO_GESTOR = ("nome", "hc", "dias_uteis", "horas_dia", "criado_em", "editado_em")
_trava = threading.Lock()


# ---------------- Celulas ----------------

def _k(*partes):
    return json.dumps(list(partes), ensure_ascii=False, separators=(",", ":"))


def _partes(chave):
    return json.loads(chave)


def _vivo(celula):
    return bool(celula) and not celula.get("x")


def _mais_nova(a, b):
    """A celula que vale entre duas: a de data maior; no empate, a
    apagada, e depois a de valor maior (para todo mundo escolher igual)."""
    chave = lambda c: (c.get("t", ""), 1 if c.get("x") else 0, json.dumps(c.get("v"), sort_keys=True))
    return a if chave(a) >= chave(b) else b


def _juntar(*mapas):
    junto = {}
    for mapa in mapas:
        for chave, celula in mapa.items():
            if not isinstance(celula, dict):
                continue
            atual = junto.get(chave)
            junto[chave] = celula if atual is None else _mais_nova(celula, atual)
    return junto


def _agora():
    return datetime.datetime.now().isoformat(timespec="microseconds")


# ---------------- Local <-> celulas ----------------

def _funcoes(hc):
    return [headcount_store._normalizar_funcao(f) for f in hc.get("funcoes", [])]


def celulas_locais(operacao, hc, cv):
    """{chave: valor} do que esta digitado nesta maquina para a operacao."""
    celulas = {}
    for gestor in hc.get("gestores", []):
        if gestor.get("operacao") != operacao:
            continue
        gid = gestor["id"]
        celulas[_k("g", gid)] = True
        for campo in CAMPOS_DO_GESTOR:
            if gestor.get(campo) is not None:
                celulas[_k("g", gid, campo)] = gestor[campo]
        for periodo, valores in (gestor.get("quadro") or {}).items():
            for campo, valor in (valores or {}).items():
                if valor is not None:
                    celulas[_k("g", gid, "q", periodo, campo)] = valor
    for funcao in _funcoes(hc):
        if funcao["operacao"] == operacao and funcao["nome"]:
            celulas[_k("f", funcao["nome"].casefold())] = funcao["nome"]
    for chave_periodo, por_usuario in (cv.get("manuais", {}).get(operacao) or {}).items():
        for usuario, campos in (por_usuario or {}).items():
            for campo, valor in (campos or {}).items():
                if valor is not None:
                    celulas[_k("cv", chave_periodo, usuario, campo)] = valor
    for chave_periodo, campos in (cv.get("sinergia", {}).get(operacao) or {}).items():
        for campo, valor in (campos or {}).items():
            if valor is not None:
                celulas[_k("sin", chave_periodo, campo)] = valor
    return celulas


def _valores_vivos(celulas):
    """{chave: valor} das celulas vivas, considerando gestor apagado."""
    vivos = {}
    for chave, celula in celulas.items():
        if not _vivo(celula):
            continue
        partes = _partes(chave)
        if partes[0] == "g" and len(partes) > 2 and not _vivo(celulas.get(_k("g", partes[1]))):
            continue
        vivos[chave] = celula.get("v")
    return vivos


def _carimbar(conhecido, locais, quando):
    """O que esta pessoa mudou desde a ultima juncao, com a data de agora:
    valores novos ou diferentes e, para o que sumiu, a marca de apagado.
    A comparacao e com o que aparecia na tela (os campos de um gestor
    apagado nao aparecem, entao nao viram mudanca)."""
    meu = dict(conhecido)
    visiveis = _valores_vivos(conhecido)
    for chave, valor in locais.items():
        if chave not in visiveis or visiveis[chave] != valor:
            meu[chave] = {"v": valor, "t": quando}
    for chave in visiveis:
        if chave not in locais:
            meu[chave] = {"x": 1, "t": quando}
    return meu


def _unificar(celulas):
    """Gestores vivos com o mesmo nome na operacao viram um so: fica o de
    menor id, com o valor mais recente de cada campo dos dois."""
    por_nome = {}
    for chave, celula in celulas.items():
        partes = _partes(chave)
        if partes[0] == "g" and len(partes) == 2 and _vivo(celula):
            nome = celulas.get(_k("g", partes[1], "nome"))
            if _vivo(nome):
                por_nome.setdefault(nome_comparavel(nome.get("v") or ""), []).append(partes[1])
    for ids in por_nome.values():
        if len(ids) < 2:
            continue
        fica = min(ids)
        for sai in ids:
            if sai == fica:
                continue
            datas = [celulas[_k("g", sai)].get("t", "")]
            for chave, celula in list(celulas.items()):
                partes = _partes(chave)
                if partes[0] == "g" and partes[1] == sai and len(partes) > 2:
                    datas.append(celula.get("t", ""))
                    destino = _k("g", fica, *partes[2:])
                    atual = celulas.get(destino)
                    celulas[destino] = celula if atual is None else _mais_nova(celula, atual)
            celulas[_k("g", sai)] = {"x": 1, "t": max(datas)}
    return celulas


def _materializar(operacao, celulas, hc, cv):
    """Troca na copia local o que e da operacao pelo que ficou junto."""
    vivos = _valores_vivos(celulas)
    gestores = {}
    funcoes = []
    manuais = {}
    sinergia = {}
    for chave, valor in vivos.items():
        partes = _partes(chave)
        if partes[0] == "g" and len(partes) >= 2:
            gestor = gestores.setdefault(partes[1], {"id": partes[1], "operacao": operacao, "quadro": {}})
            if len(partes) == 3 and partes[2] in CAMPOS_DO_GESTOR:
                gestor[partes[2]] = valor
            elif len(partes) == 5 and partes[2] == "q":
                gestor["quadro"].setdefault(partes[3], {})[partes[4]] = valor
        elif partes[0] == "f" and len(partes) == 2:
            funcoes.append({"nome": valor, "operacao": operacao})
        elif partes[0] == "cv" and len(partes) == 4:
            manuais.setdefault(partes[1], {}).setdefault(partes[2], {})[partes[3]] = valor
        elif partes[0] == "sin" and len(partes) == 3:
            sinergia.setdefault(partes[1], {})[partes[2]] = valor

    horas_padrao = hc.get("config", {}).get("horas_dia", 8.0)
    ordem = {g["id"]: i for i, g in enumerate(hc.get("gestores", []))}
    novos = []
    for gestor in gestores.values():
        if not gestor.get("nome"):
            continue
        gestor.setdefault("hc", 0)
        gestor.setdefault("dias_uteis", None)
        gestor.setdefault("horas_dia", horas_padrao)
        novos.append(gestor)
    novos.sort(key=lambda g: (ordem.get(g["id"], len(ordem)), g["nome"].casefold()))
    hc["gestores"] = [g for g in hc.get("gestores", []) if g.get("operacao") != operacao] + novos
    hc["funcoes"] = [f for f in _funcoes(hc) if f["operacao"] != operacao] + sorted(
        funcoes, key=lambda f: f["nome"].casefold())
    if manuais:
        cv.setdefault("manuais", {})[operacao] = manuais
    else:
        cv.setdefault("manuais", {}).pop(operacao, None)
    if sinergia:
        cv.setdefault("sinergia", {})[operacao] = sinergia
    else:
        cv.setdefault("sinergia", {}).pop(operacao, None)


# ---------------- Pasta compartilhada ----------------

def pasta(base, operacao):
    config = OPERATIONS[operacao]
    return os.path.join(base, config.get("sharepoint_folder") or config["label"], PASTA)


def arquivo(base, operacao):
    return os.path.join(pasta(base, operacao), f"ScoreCard_lancamentos_{operacao}.json")


def _copias(base, operacao):
    """O arquivo da operacao e as copias de conflito do OneDrive dele."""
    prefixo = f"ScoreCard_lancamentos_{operacao}"
    try:
        nomes = os.listdir(pasta(base, operacao))
    except OSError:
        return []
    achados = []
    for nome in nomes:
        resto = nome[len(prefixo):]
        if nome.startswith(prefixo) and nome.lower().endswith(".json") and resto[:1] in (".", "-", " ", "("):
            achados.append(os.path.join(pasta(base, operacao), nome))
    return sorted(achados)


def _ler_celulas(caminho):
    try:
        with open(caminho, encoding="utf-8") as fh:
            dados = json.load(fh)
    except (OSError, ValueError):
        return None
    if not isinstance(dados, dict) or not isinstance(dados.get("celulas"), dict):
        return None
    return dados["celulas"]


def _caminho_do_estado():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta_do_app = os.path.join(base, APP_NAME)
    os.makedirs(pasta_do_app, exist_ok=True)
    return os.path.join(pasta_do_app, "lancamentos.json")


def _ler_estado():
    try:
        with open(_caminho_do_estado(), encoding="utf-8") as fh:
            estado = json.load(fh)
    except (OSError, ValueError):
        return {}
    return estado if isinstance(estado, dict) else {}


def _data_dos_arquivos_locais():
    """Para a primeira juncao desta maquina: o que ja estava digitado vale
    da data em que os arquivos locais foram mexidos pela ultima vez (e nao
    de agora, para dado antigo nao passar por cima de dado novo)."""
    datas = []
    for caminho in (headcount_store._caminho(), coverage_store._caminho()):
        try:
            datas.append(os.path.getmtime(caminho))
        except OSError:
            pass
    if not datas:
        return _agora()
    return datetime.datetime.fromtimestamp(max(datas)).isoformat(timespec="microseconds")


def sincronizar(base):
    """Junta os lancamentos desta maquina com os da pasta, operacao por
    operacao, grava a pasta e traz para a copia local o que mudou.

    Devolve {"mudaram": [operacoes cuja copia local mudou], "erros": [...]},
    ou {"sem_pasta": True}.
    """
    if not base or not os.path.isdir(base):
        return {"sem_pasta": True, "mudaram": [], "erros": []}
    with _trava:
        return _sincronizar(base)


def _sincronizar(base):
    estado = _ler_estado()
    mesma_pasta = os.path.normcase(os.path.abspath(base))
    if estado.get("pasta") != mesma_pasta:
        estado = {"pasta": mesma_pasta, "operacoes": {}}
    por_operacao = estado.setdefault("operacoes", {})
    hc = headcount_store.ler()
    cv = coverage_store.ler()
    hc_antes = json.dumps(hc, sort_keys=True)
    cv_antes = json.dumps(cv, sort_keys=True)
    agora = _agora()
    primeira_data = None
    mudaram, erros = [], []
    estado_mudou = False

    for operacao in OPERATIONS:
        locais = celulas_locais(operacao, hc, cv)
        conhecido = por_operacao.get(operacao)
        if conhecido is None:
            primeira_data = primeira_data or _data_dos_arquivos_locais()
            meu = _carimbar({}, locais, primeira_data)
        else:
            meu = _carimbar(conhecido, locais, agora)
        copias = _copias(base, operacao)
        lidas = [_ler_celulas(c) for c in copias]
        if any(celulas is None for celulas in lidas):
            # Arquivo da pasta ilegivel (meio baixado): tenta na proxima.
            erros.append(operacao)
            continue
        compartilhado = _juntar(*lidas) if lidas else {}
        if not meu and not compartilhado:
            continue
        junto = _unificar(_juntar(compartilhado, meu))

        principal = arquivo(base, operacao)
        if junto != compartilhado or len(copias) > 1 or principal not in copias:
            try:
                os.makedirs(pasta(base, operacao), exist_ok=True)
                arquivo_seguro.gravar_json(principal, {"formato": FORMATO, "operacao": operacao,
                                                       "atualizado_em": agora, "celulas": junto},
                                           compacto=True)
                for copia in copias:
                    if os.path.abspath(copia) != os.path.abspath(principal):
                        os.remove(copia)
            except OSError:
                log.exception("não consegui gravar os lançamentos de %s na pasta", operacao)
                erros.append(operacao)
                continue
        if por_operacao.get(operacao) != junto:
            por_operacao[operacao] = junto
            estado_mudou = True
        if _valores_vivos(junto) != locais:
            _materializar(operacao, junto, hc, cv)
            if _valores_vivos(junto) != locais:
                mudaram.append(operacao)

    if json.dumps(hc, sort_keys=True) != hc_antes:
        headcount_store._gravar(hc)
    if json.dumps(cv, sort_keys=True) != cv_antes:
        coverage_store._gravar(cv)
    if estado_mudou:
        arquivo_seguro.gravar_json(_caminho_do_estado(), estado, compacto=True)
    if mudaram:
        log.info("lançamentos atualizados da pasta: %s", ", ".join(mudaram))
    return {"mudaram": mudaram, "erros": erros}


def resumo(base):
    """Para a tela de saude: quantas operacoes tem lancamentos na pasta e
    quando o mais novo foi gravado."""
    if not base or not os.path.isdir(base):
        return {"operacoes": 0, "atualizado_em": None}
    operacoes, datas = 0, []
    for operacao in OPERATIONS:
        try:
            with open(arquivo(base, operacao), encoding="utf-8") as fh:
                dados = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(dados, dict):
            operacoes += 1
            if dados.get("atualizado_em"):
                datas.append(dados["atualizado_em"])
    return {"operacoes": operacoes, "atualizado_em": max(datas) if datas else None}


def contagem():
    """Para o diagnostico: quantas celulas de cada operacao este app ja
    juntou (so numeros, sem nome de gestor)."""
    return {operacao: len(celulas) for operacao, celulas in (_ler_estado().get("operacoes") or {}).items()}
