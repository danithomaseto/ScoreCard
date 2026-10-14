"""Headcount e Coverage compartilhados pela pasta do SharePoint
(lancamentos.py): duas maquinas, a mesma pasta, e cada uma vendo o que a
outra digitou."""

import datetime
import json
import os
import time

import pytest

import backup
import coverage_store
import headcount_store
import lancamentos
import settings_store
from api import Api

OP = "hughes"


class Maquina:
    """Uma pessoa com o APPDATA dela e a pasta compartilhada em comum."""

    def __init__(self, raiz, nome, base, monkeypatch):
        self.appdata = str(raiz / nome)
        self.base = str(base)
        self._monkeypatch = monkeypatch

    def __enter__(self):
        self._monkeypatch.setenv("APPDATA", self.appdata)
        return self

    def __exit__(self, *_):
        return False

    def sincronizar(self):
        with self:
            return lancamentos.sincronizar(self.base)

    def gestores(self, operacao=OP):
        with self:
            return {g["nome"]: g for g in headcount_store.listar_gestores(operacao)}


@pytest.fixture
def pasta(tmp_path):
    base = tmp_path / "sharepoint"
    base.mkdir()
    return base


@pytest.fixture
def maquinas(tmp_path, pasta, monkeypatch):
    return (Maquina(tmp_path, "ana", pasta, monkeypatch),
            Maquina(tmp_path, "bruno", pasta, monkeypatch))


def _envelhecer_dados_locais(maquina, horas=24):
    """Os arquivos locais como se tivessem sido mexidos ha um tempo."""
    with maquina:
        antes = time.time() - horas * 3600
        for caminho in (headcount_store._caminho(), coverage_store._caminho()):
            if os.path.exists(caminho):
                os.utime(caminho, (antes, antes))


def test_o_que_uma_pessoa_digita_chega_na_outra(maquinas, pasta):
    ana, bruno = maquinas
    with ana:
        gestor = headcount_store.adicionar_gestor("SILVA,ANA", OP)
        headcount_store.definir_quadro(gestor["id"], "2026-09-S2", "hc", "12")
    assert ana.sincronizar() == {"mudaram": [], "erros": []}
    assert os.path.isfile(lancamentos.arquivo(str(pasta), OP))

    resposta = bruno.sincronizar()
    assert resposta["mudaram"] == [OP]
    recebido = bruno.gestores()["SILVA,ANA"]
    assert recebido["id"] == gestor["id"]
    assert recebido["quadro"] == {"2026-09-S2": {"hc": 12}}
    # Sem mudanca dos dois lados, nada muda de novo.
    assert bruno.sincronizar()["mudaram"] == []


def test_celulas_diferentes_do_mesmo_gestor_nao_se_atrapalham(maquinas):
    ana, bruno = maquinas
    with ana:
        gid = headcount_store.adicionar_gestor("SILVA,ANA", OP)["id"]
    ana.sincronizar()
    bruno.sincronizar()

    with ana:
        headcount_store.definir_quadro(gid, "2026-09-S2", "hc", "12")
    with bruno:
        headcount_store.definir_quadro(gid, "2026-09-S2", "faltas", "3")
    ana.sincronizar()
    bruno.sincronizar()
    ana.sincronizar()

    for maquina in (ana, bruno):
        assert maquina.gestores()["SILVA,ANA"]["quadro"]["2026-09-S2"] == {"hc": 12, "faltas": 3}


def test_na_mesma_celula_vale_a_mudanca_mais_nova(maquinas):
    ana, bruno = maquinas
    with ana:
        gid = headcount_store.adicionar_gestor("SILVA,ANA", OP)["id"]
    ana.sincronizar()
    bruno.sincronizar()

    with ana:
        headcount_store.definir_quadro(gid, "2026-09-S2", "hc", "10")
    ana.sincronizar()
    with bruno:
        headcount_store.definir_quadro(gid, "2026-09-S2", "hc", "15")
    bruno.sincronizar()  # o Bruno mudou depois: vale o dele
    ana.sincronizar()

    for maquina in (ana, bruno):
        assert maquina.gestores()["SILVA,ANA"]["quadro"]["2026-09-S2"]["hc"] == 15


def test_apagar_um_valor_ou_o_gestor_vale_para_todos(maquinas):
    ana, bruno = maquinas
    with ana:
        fica = headcount_store.adicionar_gestor("SILVA,ANA", OP)["id"]
        sai = headcount_store.adicionar_gestor("SOUZA,BRUNO", OP)["id"]
        headcount_store.definir_quadro(fica, "2026-09-S2", "hc", "10")
    ana.sincronizar()
    bruno.sincronizar()

    with bruno:
        headcount_store.definir_quadro(fica, "2026-09-S2", "hc", "")
        headcount_store.remover_gestor(sai)
    bruno.sincronizar()
    ana.sincronizar()

    assert set(ana.gestores()) == {"SILVA,ANA"}
    assert ana.gestores()["SILVA,ANA"].get("quadro") in ({}, None)
    # E nao volta: a marca de apagado fica na pasta.
    ana.sincronizar()
    bruno.sincronizar()
    assert set(bruno.gestores()) == {"SILVA,ANA"}


def test_mesmo_nome_cadastrado_pelos_dois_vira_um_gestor_so(maquinas):
    ana, bruno = maquinas
    with ana:
        da_ana = headcount_store.adicionar_gestor("SILVA,ANA", OP)["id"]
        headcount_store.definir_quadro(da_ana, "2026-09-S2", "hc", "12")
    with bruno:
        do_bruno = headcount_store.adicionar_gestor("silva , ana", OP)["id"]
        headcount_store.definir_quadro(do_bruno, "2026-09-S3", "hc", "9")
    ana.sincronizar()
    bruno.sincronizar()
    ana.sincronizar()

    fica = min(da_ana, do_bruno)
    for maquina in (ana, bruno):
        gestores = list(maquina.gestores().values())
        assert [g["id"] for g in gestores] == [fica]
        assert gestores[0]["quadro"] == {"2026-09-S2": {"hc": 12}, "2026-09-S3": {"hc": 9}}


def test_coverage_e_funcoes_tambem_vao_para_a_pasta(maquinas):
    ana, bruno = maquinas
    with ana:
        coverage_store.definir(OP, "week:2026-09-13", ["P01", "P02"], "dias", "5")
        coverage_store.definir_sinergia(OP, "week:2026-09-13", "cedida", "7,5")
        headcount_store.adicionar_funcao("Operador de Ponte", OP)
    ana.sincronizar()
    bruno.sincronizar()

    with bruno:
        assert coverage_store.manuais(OP, "week:2026-09-13") == {"P01": {"dias": 5}, "P02": {"dias": 5}}
        assert coverage_store.sinergia(OP, "week:2026-09-13") == {"cedida": 7.5}
        assert [f["nome"] for f in headcount_store.listar_funcoes(OP)] == ["Operador de Ponte"]
        headcount_store.remover_funcao("Operador de Ponte", OP)
    bruno.sincronizar()
    ana.sincronizar()
    with ana:
        assert headcount_store.listar_funcoes(OP) == []


def test_o_que_ja_estava_digitado_entra_com_a_data_dos_arquivos(maquinas):
    """Na primeira juncao, dado antigo desta maquina nao passa por cima de
    dado mais novo que ja esta na pasta."""
    ana, bruno = maquinas
    with ana:
        gid = headcount_store.adicionar_gestor("SILVA,ANA", OP)["id"]
        headcount_store.definir_quadro(gid, "2026-09-S2", "hc", "12")
    ana.sincronizar()
    with bruno:
        # O Bruno tinha o mesmo gestor (copiado de um backup, por exemplo)
        # com um HC velho, digitado ontem.
        dados = headcount_store.ler()
        dados["gestores"] = [{"id": gid, "nome": "SILVA,ANA", "operacao": OP, "hc": 0,
                              "dias_uteis": None, "horas_dia": 8.0,
                              "quadro": {"2026-09-S2": {"hc": 3}}}]
        headcount_store._gravar(dados)
    _envelhecer_dados_locais(bruno)
    bruno.sincronizar()

    assert bruno.gestores()["SILVA,ANA"]["quadro"]["2026-09-S2"]["hc"] == 12


def test_copias_de_conflito_do_onedrive_sao_juntadas_e_apagadas(maquinas, pasta):
    ana, bruno = maquinas
    with ana:
        headcount_store.adicionar_gestor("SILVA,ANA", OP)
    ana.sincronizar()
    with bruno:
        headcount_store.adicionar_gestor("SOUZA,BRUNO", OP)
    bruno.sincronizar()

    # O OneDrive nao conseguiu juntar e deixou uma copia com o nome do PC.
    principal = lancamentos.arquivo(str(pasta), OP)
    copia = principal.replace(".json", "-PC123.json")
    with open(principal, encoding="utf-8") as fh:
        dados = json.load(fh)
    extra = {k: v for k, v in dados["celulas"].items()}
    novo = '["f","operador de ponte"]'
    extra[novo] = {"v": "Operador de Ponte", "t": datetime.datetime.now().isoformat()}
    with open(copia, "w", encoding="utf-8") as fh:
        json.dump({**dados, "celulas": extra}, fh)

    assert ana.sincronizar()["mudaram"] == [OP]
    assert not os.path.exists(copia)
    assert set(ana.gestores()) == {"SILVA,ANA", "SOUZA,BRUNO"}
    with ana:
        assert [f["nome"] for f in headcount_store.listar_funcoes(OP)] == ["Operador de Ponte"]


def test_arquivo_da_pasta_pela_metade_fica_para_a_proxima(maquinas, pasta):
    ana, _ = maquinas
    with ana:
        headcount_store.adicionar_gestor("SILVA,ANA", OP)
    ana.sincronizar()
    principal = lancamentos.arquivo(str(pasta), OP)
    with open(principal, "w", encoding="utf-8") as fh:
        fh.write('{"formato": 1, "celulas": {')  # o OneDrive ainda baixando

    resposta = ana.sincronizar()
    assert resposta["erros"] == [OP]
    # Nao grava por cima do arquivo que esta chegando, e o local fica.
    with open(principal, encoding="utf-8") as fh:
        assert fh.read().endswith("{")
    assert set(ana.gestores()) == {"SILVA,ANA"}


def test_sem_pasta_nao_faz_nada(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "ana"))
    assert lancamentos.sincronizar(None)["sem_pasta"]
    assert lancamentos.sincronizar(str(tmp_path / "nao-existe"))["sem_pasta"]


def test_api_leva_o_lancamento_para_a_pasta_e_avisa_o_que_chegou(maquinas, pasta, monkeypatch):
    import api as api_mod

    monkeypatch.setattr(api_mod, "ESPERA_PARA_PUBLICAR", 0.05)
    ana, bruno = maquinas
    for maquina in (ana, bruno):
        with maquina:
            settings_store.set_sharepoint_folder(str(pasta))

    with ana:
        app = Api()
        resposta = app.add_gestor("SILVA,ANA", OP)
        assert resposta["success"]
        assert app.set_quadro(resposta["gestor"]["id"], "2026-09-S2", "hc", "12")["success"]
        # Erro de validacao nao agenda nada.
        assert not app.set_quadro(resposta["gestor"]["id"], "2026-09-S2", "hc", "-1")["success"]
        app._publicacao.join(2)
    assert os.path.isfile(lancamentos.arquivo(str(pasta), OP))

    with bruno:
        tela = Api().sincronizar_sharepoint()
    assert tela["lancamentos"] == [{"operacao": OP, "operacao_rotulo": "Hughes"}]
    assert bruno.gestores()["SILVA,ANA"]["quadro"]["2026-09-S2"]["hc"] == 12


def test_backup_restaurado_volta_com_a_data_dele_e_sem_o_que_nao_existia(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "ana"))
    headcount_store.adicionar_gestor("SILVA,ANA", OP)
    ontem = datetime.date.today() - datetime.timedelta(days=1)
    zip_de_ontem = backup.fazer(hoje=ontem)
    with __import__("zipfile").ZipFile(zip_de_ontem) as zf:
        data_no_zip = datetime.datetime(*zf.getinfo("headcount.json").date_time)

    coverage_store.definir(OP, "week:2026-09-13", ["P01"], "dias", "5")  # coverage.json nasce depois
    headcount_store.adicionar_gestor("SOUZA,BRUNO", OP)
    backup.restaurar(os.path.basename(zip_de_ontem))

    assert [g["nome"] for g in headcount_store.listar_gestores(OP)] == ["SILVA,ANA"]
    assert not os.path.exists(coverage_store._caminho())
    restaurado = datetime.datetime.fromtimestamp(os.path.getmtime(headcount_store._caminho()))
    assert abs((restaurado - data_no_zip).total_seconds()) <= 2


def test_diagnostico_conta_as_celulas_sem_levar_nomes(maquinas, pasta):
    import diagnostico

    ana, _ = maquinas
    with ana:
        headcount_store.adicionar_gestor("SILVA,ANA", OP)
    ana.sincronizar()
    with ana:
        texto = diagnostico.resumo()
    assert f"  {OP}: " in texto
    assert "SILVA" not in texto
