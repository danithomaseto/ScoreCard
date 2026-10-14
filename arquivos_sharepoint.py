"""Relatorios do Summary na pasta do SharePoint: nome, periodo, limpeza e a
leitura compartilhada entre as pessoas.

A pasta do SharePoint (sincronizada pelo OneDrive) e a mesma para todo
mundo. Cada extracao salva o relatorio em

    <pasta>\\<operacao>\\<tipo>\\ScoreCard_<op>_<AAAAMMDD_HHMMSS>[_<de>-<ate>][_GB-<group by>].xls

- AAAAMMDD_HHMMSS: quando foi extraido (a data que a tela mostra em
  "No SharePoint");
- de-ate (AAAAMMDD): o periodo do relatorio. No mes e nos dias de pico e
  ele que diz de que mes e o arquivo — o export mensal nao tem coluna de
  data. Na semana vem das datas digitadas ou, com o "Last Week", das
  proprias semanas do arquivo;
- GB: o Group By 1 do Month, so quando nao e o User ID (a dispersao so
  vale com User ID).

Com o periodo no nome a pasta guarda o historico: uma extracao nova apaga
so os arquivos anteriores da mesma operacao que ela cobre por inteiro (o
mesmo periodo, ou um pedaco dele).

**Leitura compartilhada** (sincronizar): o app olha as pastas e calcula os
arquivos que ainda nao leu — extraidos por qualquer pessoa —, na ordem em
que foram extraidos, com o mesmo calculo da extracao. Assim quem filtra
uma operacao/semana/mes ve o resultado mesmo sem ter extraido. O que ja
foi lido fica anotado em %APPDATA%\\ScoreCard\\sharepoint.json (nome,
tamanho e data de cada arquivo), para so ler de novo o que mudou.
"""

import datetime
import json
import logging
import os
import re
import threading
import time

import arquivo_seguro
from config.operations import GROUP_BY_OPTIONS, OPERATIONS, PASTAS_DO_PERIODO, ROTULOS_DO_PERIODO, agrupamento, e_semanal

APP_NAME = "ScoreCard"
# Arquivo mexido ha menos que isto pode estar sendo gravado (o OneDrive
# baixando, ou a extracao deste app): fica para a proxima volta.
RECENTE_SEGUNDOS = 10
# Arquivo extraido ha mais tempo que isto nao entra na leitura: na
# primeira vez de uma pessoa nova, ler anos de historico demoraria.
HORIZONTE_DIAS = 400

log = logging.getLogger("scorecard.sharepoint")
_trava = threading.Lock()


# ---------------- Nome do arquivo ----------------

def _slug(texto):
    return re.sub(r"[^A-Za-z0-9]+", "-", texto).strip("-")


_GROUP_BY_DO_SLUG = {_slug(opcao): opcao for opcao in GROUP_BY_OPTIONS}


def nome_do_arquivo(operacao, quando, extensao, de=None, ate=None, group_by=None):
    """ScoreCard_<op>_<AAAAMMDD_HHMMSS>[_<de>-<ate>][_GB-<group by>]<extensao>."""
    nome = f"ScoreCard_{operacao}_{quando.strftime('%Y%m%d_%H%M%S')}"
    if de and ate:
        nome += f"_{de.replace('-', '')}-{ate.replace('-', '')}"
    if group_by and group_by != "User ID":
        nome += f"_GB-{_slug(group_by)}"
    return nome + extensao


def _padrao(operacao):
    return re.compile(
        rf"^ScoreCard_{re.escape(operacao)}_(\d{{8}}_\d{{6}})"
        r"(?:_(\d{8})-(\d{8}))?(?:_GB-([A-Za-z0-9-]+))?\.xlsx?$",
        re.IGNORECASE,
    )


def _iso(aaaammdd):
    try:
        return datetime.datetime.strptime(aaaammdd, "%Y%m%d").date().isoformat()
    except (TypeError, ValueError):
        return None


def ler_nome(nome, operacao):
    """{"nome", "quando", "de", "ate", "group_by"} de um nome de relatorio
    desta operacao, ou None se o nome nao e de um relatorio do app."""
    achado = _padrao(operacao).match(nome)
    if not achado:
        return None
    try:
        quando = datetime.datetime.strptime(achado.group(1), "%Y%m%d_%H%M%S")
    except ValueError:
        return None
    de, ate = _iso(achado.group(2)), _iso(achado.group(3))
    if not (de and ate) or de > ate:
        de = ate = None
    slug = achado.group(4)
    return {
        "nome": nome,
        "quando": quando,
        "de": de,
        "ate": ate,
        "group_by": _GROUP_BY_DO_SLUG.get(slug, slug) if slug else None,
    }


# ---------------- Pastas e periodos ----------------

def pasta(base, operacao, tipo):
    """<pasta>\\<operacao>\\<tipo> ("Gestor/Week" vira duas pastas)."""
    config = OPERATIONS[operacao]
    pasta_da_operacao = config.get("sharepoint_folder") or config["label"]
    return os.path.join(base, pasta_da_operacao, *PASTAS_DO_PERIODO[tipo].split("/"))


def _arquivos_em(diretorio, operacao):
    try:
        entradas = list(os.scandir(diretorio))
    except OSError:
        return []
    achados = []
    for entrada in entradas:
        info = ler_nome(entrada.name, operacao)
        if not info:
            continue
        try:
            if not entrada.is_file():
                continue
            estado = entrada.stat()
        except OSError:
            continue
        info.update(caminho=entrada.path, tamanho=estado.st_size, mtime=estado.st_mtime)
        achados.append(info)
    return sorted(achados, key=lambda a: (a["quando"], a["nome"]))


def arquivos(base, operacao, tipo):
    """Os relatorios da operacao na pasta do tipo, do mais antigo ao mais novo."""
    return _arquivos_em(pasta(base, operacao, tipo), operacao)


def _semanas_do_conteudo(caminho):
    from indicators import reader  # so quando precisa: le o arquivo

    lido = reader.ler(caminho)
    return sorted({linha["semana"] for linha in lido["linhas"] if linha.get("semana")})


def periodo(arquivo, tipo):
    """(de, ate) do relatorio: do nome ou, sem ele, das semanas do arquivo.
    None quando nao da para saber (Month antigo, sem o periodo no nome)."""
    if arquivo.get("de") and arquivo.get("ate"):
        return arquivo["de"], arquivo["ate"]
    if e_semanal(tipo):
        try:
            semanas = _semanas_do_conteudo(arquivo["caminho"])
        except Exception:  # noqa: BLE001 - arquivo ilegivel: periodo desconhecido
            return None
        if semanas:
            fim = datetime.date.fromisoformat(semanas[-1]) + datetime.timedelta(days=6)
            return semanas[0], fim.isoformat()
    return None


# ---------------- Depois de baixar ----------------

def guardar(caminho, operacao, tipo):
    """Acerta o nome do relatorio recem-baixado e apaga os anteriores que
    ele substitui. Devolve o caminho final.

    Sem periodo no nome (semana com o "Last Week"), o periodo sai das
    semanas do arquivo e entra no nome. Depois saem os relatorios
    anteriores da mesma operacao cujo periodo cabe inteiro no do novo; os
    de periodo desconhecido (Month de antes desta versao) saem como
    antes. Se nem o periodo do novo da para saber, nada e apagado.
    """
    info = ler_nome(os.path.basename(caminho), operacao)
    if not info:
        return caminho
    info["caminho"] = caminho
    periodo_novo = periodo(info, tipo)
    if periodo_novo and not info["de"]:
        nome = nome_do_arquivo(operacao, info["quando"], os.path.splitext(caminho)[1],
                               *periodo_novo, group_by=info["group_by"])
        destino = os.path.join(os.path.dirname(caminho), nome)
        try:
            os.replace(caminho, destino)
            caminho = destino
        except OSError:
            log.warning("não consegui pôr o período no nome de %s", caminho)
    if not periodo_novo:
        return caminho

    for antigo in _arquivos_em(os.path.dirname(caminho), operacao):
        if os.path.abspath(antigo["caminho"]) == os.path.abspath(caminho):
            continue
        if antigo["quando"] > info["quando"]:
            continue  # extraido depois deste (outra pessoa): fica
        periodo_antigo = periodo(antigo, tipo)
        coberto = (periodo_antigo is None
                   or (periodo_novo[0] <= periodo_antigo[0] and periodo_antigo[1] <= periodo_novo[1]))
        if coberto:
            try:
                os.remove(antigo["caminho"])
            except OSError:
                pass  # nao deixa uma falha de limpeza derrubar a extracao
    return caminho


# ---------------- O que existe na pasta ----------------

def ultimos(base, operacao):
    """{tipo: {"quando", "nome", "de", "ate"}} do relatorio mais novo de
    cada tipo da operacao. Tipos sem arquivo ficam de fora."""
    if not base or operacao not in OPERATIONS:
        return {}
    resultado = {}
    for tipo in PASTAS_DO_PERIODO:
        achados = arquivos(base, operacao, tipo)
        if achados:
            mais_novo = achados[-1]
            resultado[tipo] = {chave: mais_novo[chave] for chave in ("quando", "nome", "de", "ate")}
    return resultado


# ---------------- Leitura compartilhada ----------------

def _caminho_do_estado():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    pasta_do_app = os.path.join(base, APP_NAME)
    os.makedirs(pasta_do_app, exist_ok=True)
    return os.path.join(pasta_do_app, "sharepoint.json")


def _ler_estado():
    try:
        with open(_caminho_do_estado(), encoding="utf-8") as fh:
            estado = json.load(fh)
    except (OSError, ValueError):
        return {}
    return estado if isinstance(estado, dict) else {}


def _assinatura(arquivo):
    return [arquivo["tamanho"], int(arquivo["mtime"])]


def _mesma_pasta(base):
    return os.path.normcase(os.path.abspath(base))


def _mes_do_pico(caminho):
    from indicators import datas, reader

    linhas = reader.ler(caminho)["linhas"]
    return datas.mes_predominante([linha.get("detalhe") for linha in linhas if linha.get("detalhe")])


def resultado(arquivo, operacao, tipo):
    """O resultado de uma extracao montado a partir do arquivo, para o
    mesmo calculo dela (Api._calcular_indicadores). None quando nao da
    para saber o mes (Month de antes desta versao, sem o periodo no nome)."""
    niveis = agrupamento(tipo, arquivo.get("group_by"))
    de, ate = arquivo.get("de"), arquivo.get("ate")
    mes = None
    if not e_semanal(tipo):
        if de:
            mes = de[:7]
        elif tipo == "peak":
            try:
                mes = _mes_do_pico(arquivo["caminho"])
            except Exception:  # noqa: BLE001 - ilegivel: fica de fora
                mes = None
        if not mes:
            return None
    return {
        "success": True,
        "file_path": arquivo["caminho"],
        "operation": operacao,
        "tipo": tipo,
        "group_by": niveis[-1],
        "agrupamento": " › ".join(niveis),
        "date_from": de,
        "date_to": ate,
        "month_key": mes,
        "origem": "sharepoint",
        "extraido_em": arquivo["quando"].isoformat(timespec="seconds"),
    }


def _legivel(caminho):
    try:
        with open(caminho, "rb") as fh:
            fh.read(8)
        return True
    except OSError:
        return False


def sincronizar(base, aplicar, agora=None):
    """Le os relatorios novos ou alterados da pasta, de todas as operacoes.

    aplicar(operacao, resultado) faz o calculo — o mesmo da extracao — e
    marca resultado["indicators_message"] quando nao deu para calcular.
    Devolve {"atualizados": [{"operacao", "tipo", "arquivos"}],
    "ignorados": [{"operacao", "tipo", "nome", "motivo"}]}, com "ocupado"
    quando outra leitura ja esta rodando e "sem_pasta" sem a pasta.
    """
    vazio = {"atualizados": [], "ignorados": []}
    if not base or not os.path.isdir(base):
        return {**vazio, "sem_pasta": True}
    if not _trava.acquire(blocking=False):
        return {**vazio, "ocupado": True}
    try:
        return _sincronizar(base, aplicar, agora if agora is not None else time.time())
    finally:
        _trava.release()


def _sincronizar(base, aplicar, agora):
    estado = _ler_estado()
    mudou = False
    if estado.get("pasta") != _mesma_pasta(base):
        # Pasta nova (ou primeira leitura): comeca do zero e ja anota a
        # pasta, para o que esta pessoa extrair em seguida ficar marcado.
        estado = {"pasta": _mesma_pasta(base), "grupos": {}}
        mudou = True
    grupos = estado.setdefault("grupos", {})
    # Os que nao deu para ler, com o motivo (aparecem em Configuracoes).
    nao_lidos = estado.setdefault("ignorados", {})
    limite = datetime.datetime.fromtimestamp(agora) - datetime.timedelta(days=HORIZONTE_DIAS)
    atualizados, ignorados = [], []

    for operacao in OPERATIONS:
        for tipo in PASTAS_DO_PERIODO:
            chave = f"{operacao}|{tipo}"
            lidos = grupos.get(chave, {})
            presentes = arquivos(base, operacao, tipo)
            nomes = {a["nome"] for a in presentes}
            novos = [a for a in presentes if lidos.get(a["nome"]) != _assinatura(a)]
            prontos = [a for a in novos
                       if agora - a["mtime"] >= RECENTE_SEGUNDOS and a["quando"] >= limite
                       and _legivel(a["caminho"])]
            if prontos:
                # Ja lidos e mais novos que o mais antigo que chegou (um
                # arquivo atrasado do OneDrive) sao lidos de novo depois
                # dele: a extracao mais nova e a que vale.
                primeiro = min(a["quando"] for a in prontos)
                reler = [a for a in presentes
                         if a not in novos and a["nome"] in lidos and a["quando"] > primeiro]
                calculados = 0
                do_grupo = nao_lidos.setdefault(chave, {})
                for arquivo in sorted(prontos + reler, key=lambda a: (a["quando"], a["nome"])):
                    montado = resultado(arquivo, operacao, tipo)
                    do_grupo.pop(arquivo["nome"], None)
                    if montado is None:
                        ignorados.append({"operacao": operacao, "tipo": tipo, "nome": arquivo["nome"],
                                          "motivo": "arquivo antigo, sem o mês no nome"})
                        do_grupo[arquivo["nome"]] = ignorados[-1]["motivo"]
                    else:
                        try:
                            aplicar(operacao, montado)
                        except Exception:  # noqa: BLE001 - um arquivo ruim nao para os outros
                            log.exception("não consegui calcular %s", arquivo["caminho"])
                            montado["indicators_message"] = "erro no cálculo"
                        if montado.get("indicators_message"):
                            ignorados.append({"operacao": operacao, "tipo": tipo, "nome": arquivo["nome"],
                                              "motivo": montado["indicators_message"]})
                            do_grupo[arquivo["nome"]] = montado["indicators_message"]
                        else:
                            calculados += 1
                    lidos[arquivo["nome"]] = _assinatura(arquivo)
                    mudou = True
                if calculados:
                    atualizados.append({"operacao": operacao, "tipo": tipo, "arquivos": calculados})
                    log.info("%s · %s: %d arquivo(s) do SharePoint calculado(s)", operacao, tipo, calculados)
            sobra = {nome: assinatura for nome, assinatura in lidos.items() if nome in nomes}
            if sobra != grupos.get(chave, {}):
                mudou = True
            if sobra:
                grupos[chave] = sobra
            else:
                grupos.pop(chave, None)
            ainda = {nome: motivo for nome, motivo in nao_lidos.get(chave, {}).items() if nome in nomes}
            if ainda != nao_lidos.get(chave, {}):
                mudou = True
            if ainda:
                nao_lidos[chave] = ainda
            else:
                nao_lidos.pop(chave, None)

    if mudou:
        arquivo_seguro.gravar_json(_caminho_do_estado(), estado, compacto=True)
    return {"atualizados": atualizados, "ignorados": ignorados}


def registrar(base, operacao, tipo, caminho):
    """Anota como ja lido o relatorio que esta pessoa acabou de extrair e
    calcular, para a proxima leitura nao calcular de novo."""
    if not base or not caminho or not os.path.isfile(caminho):
        return
    info = ler_nome(os.path.basename(caminho), operacao)
    if not info:
        return
    estado_do_arquivo = os.stat(caminho)
    with _trava:
        estado = _ler_estado()
        if estado.get("pasta") != _mesma_pasta(base):
            return  # a primeira leitura desta pasta ainda vai acontecer
        lidos = estado.setdefault("grupos", {}).setdefault(f"{operacao}|{tipo}", {})
        lidos[info["nome"]] = [estado_do_arquivo.st_size, int(estado_do_arquivo.st_mtime)]
        arquivo_seguro.gravar_json(_caminho_do_estado(), estado, compacto=True)


def rotulo(tipo):
    return ROTULOS_DO_PERIODO.get(tipo, tipo)


def nao_lidos(base):
    """[{"operacao", "tipo", "nome", "motivo"}] dos arquivos da pasta que
    a leitura deixou de fora, como ficou anotado na ultima leitura."""
    estado = _ler_estado()
    if not base or estado.get("pasta") != _mesma_pasta(base):
        return []
    itens = []
    for chave, por_nome in sorted((estado.get("ignorados") or {}).items()):
        operacao, _, tipo = chave.partition("|")
        for nome, motivo in sorted(por_nome.items()):
            itens.append({"operacao": operacao, "tipo": tipo, "nome": nome, "motivo": motivo})
    return itens


def lidos(base):
    """Quantos relatorios da pasta ja foram lidos (ultima leitura). Os que
    ficaram de fora tambem estao anotados (para nao tentar de novo a cada
    leitura), mas nao contam."""
    estado = _ler_estado()
    if not base or estado.get("pasta") != _mesma_pasta(base):
        return 0
    ignorados = estado.get("ignorados") or {}
    return sum(len([nome for nome in por_nome if nome not in ignorados.get(chave, {})])
               for chave, por_nome in (estado.get("grupos") or {}).items())


def reler(base, aplicar):
    """Esquece o que ja foi lido e le a pasta inteira de novo."""
    with _trava:
        try:
            os.remove(_caminho_do_estado())
        except OSError:
            pass
    log.info("leitura da pasta do SharePoint refeita do zero")
    return sincronizar(base, aplicar)


# Atributos do Windows de arquivo que o OneDrive deixa so na nuvem.
_SO_NA_NUVEM = 0x1000 | 0x40000 | 0x400000  # OFFLINE, RECALL_ON_OPEN, RECALL_ON_DATA_ACCESS


def estado_da_pasta(base):
    """Para a saude do sistema: a pasta existe, da para gravar, esta no
    OneDrive, quantos relatorios, o mais novo e quantos estao so na nuvem."""
    info = {"configurada": bool(base), "existe": False, "gravavel": False, "onedrive": False,
            "relatorios": 0, "so_na_nuvem": 0, "mais_novo": None}
    if not base or not os.path.isdir(base):
        return info
    info["existe"] = True
    try:
        import tempfile

        with tempfile.NamedTemporaryFile(dir=base, prefix=".scorecard-teste-", delete=True):
            pass
        info["gravavel"] = True
    except OSError:
        pass
    caminho = os.path.normcase(os.path.abspath(base))
    raizes = [os.environ.get(v) for v in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")]
    info["onedrive"] = ("onedrive" in caminho) or any(
        r and caminho.startswith(os.path.normcase(os.path.abspath(r))) for r in raizes)
    mais_novo = None
    for operacao in OPERATIONS:
        for tipo in PASTAS_DO_PERIODO:
            for arquivo in arquivos(base, operacao, tipo):
                info["relatorios"] += 1
                if mais_novo is None or arquivo["quando"] > mais_novo["quando"]:
                    mais_novo = {"quando": arquivo["quando"], "operacao": operacao, "tipo": tipo}
                try:
                    if getattr(os.stat(arquivo["caminho"]), "st_file_attributes", 0) & _SO_NA_NUVEM:
                        info["so_na_nuvem"] += 1
                except OSError:
                    pass
    info["mais_novo"] = mais_novo
    return info
