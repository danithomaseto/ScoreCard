"""Pasta do SharePoint compartilhada: o nome do relatorio com o periodo, a
limpeza so do que foi substituido e a leitura do que outras pessoas
extrairam (arquivos_sharepoint.py)."""

import datetime
import os
import shutil
import time

import pytest

import arquivos_sharepoint as sp
import coverage_store
import grupos_store
import indicators_store
import indiretas_store
import settings_store
from api import Api

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
QUANDO = datetime.datetime(2026, 10, 13, 15, 22, 59)


# ---------------- Nome do arquivo ----------------

def test_nome_leva_a_data_da_extracao_e_o_periodo():
    nome = sp.nome_do_arquivo("hugo_boss", QUANDO, ".xls", "2026-09-01", "2026-09-30")
    assert nome == "ScoreCard_hugo_boss_20261013_152259_20260901-20260930.xls"

    lido = sp.ler_nome(nome, "hugo_boss")
    assert lido["quando"] == QUANDO
    assert (lido["de"], lido["ate"], lido["group_by"]) == ("2026-09-01", "2026-09-30", None)


def test_group_by_do_month_so_vai_no_nome_quando_nao_e_user_id():
    assert "_GB-" not in sp.nome_do_arquivo("swa", QUANDO, ".xls", "2026-09-01", "2026-09-30", "User ID")
    nome = sp.nome_do_arquivo("swa", QUANDO, ".xls", "2026-09-01", "2026-09-30", "Aisle Area Desc.")
    assert nome.endswith("_GB-Aisle-Area-Desc.xls")
    assert sp.ler_nome(nome, "swa")["group_by"] == "Aisle Area Desc."


@pytest.mark.parametrize("nome, esperado", [
    ("ScoreCard_hughes_20261013_152259.xls", (None, None)),          # antes desta versao
    ("ScoreCard_hughes_20261013_152259_20260830-20260919.xlsx", ("2026-08-30", "2026-09-19")),
])
def test_le_nome_antigo_e_novo(nome, esperado):
    lido = sp.ler_nome(nome, "hughes")
    assert (lido["de"], lido["ate"]) == esperado
    assert lido["quando"] == QUANDO


@pytest.mark.parametrize("nome", [
    "ScoreCard_hughes_20261013_152259 (1).xls",   # copia de conflito do OneDrive
    "ScoreCard_swa_20261013_152259.xls",          # de outra operacao
    "Relatorio.xls",
    "ScoreCard_hughes_20261013_152259.csv",
])
def test_o_que_nao_e_relatorio_desta_operacao_fica_de_fora(nome):
    assert sp.ler_nome(nome, "hughes") is None


# ---------------- Limpeza depois de baixar ----------------

def _por(base, op, tipo, fixture, nome, idade=120):
    pasta = sp.pasta(str(base), op, tipo)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    shutil.copy(os.path.join(FIX, fixture), caminho)
    momento = time.time() - idade
    os.utime(caminho, (momento, momento))
    return caminho


def _nomes(base, op, tipo):
    return sorted(os.listdir(sp.pasta(str(base), op, tipo)))


def test_semana_com_last_week_ganha_o_periodo_das_semanas_do_arquivo(tmp_path):
    caminho = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261013_152259.xlsx")

    final = sp.guardar(caminho, "swa", "week")

    assert os.path.basename(final) == "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx"
    assert _nomes(tmp_path, "swa", "week") == [os.path.basename(final)]


def test_novo_apaga_so_os_anteriores_que_ele_cobre(tmp_path):
    coberto = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261001_080000_20260906-20260912.xlsx")
    outro_mes = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261001_090000_20261004-20261010.xlsx")
    mais_novo = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261014_090000_20260906-20260912.xlsx")
    novo = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261013_152259_20260901-20260930.xlsx")

    sp.guardar(novo, "swa", "week")

    assert not os.path.exists(coberto)        # cabe inteiro no novo
    assert os.path.exists(outro_mes)           # outro periodo: e historico
    assert os.path.exists(mais_novo)           # extraido depois (outra pessoa)
    assert os.path.exists(novo)


def test_month_antigo_sem_periodo_sai_como_antes(tmp_path):
    antigo = _por(tmp_path, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20260901_080000.xlsx")
    outro_mes = _por(tmp_path, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20260901_090000_20260801-20260831.xlsx")
    novo = _por(tmp_path, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20261013_152259_20260901-20260930.xlsx")

    sp.guardar(novo, "swa", "month")

    assert not os.path.exists(antigo)
    assert os.path.exists(outro_mes)


def test_sem_saber_o_periodo_do_novo_nada_e_apagado(tmp_path):
    anterior = _por(tmp_path, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261001_080000_20260906-20260912.xlsx")
    novo = _por(tmp_path, "swa", "week", "summary_mes.xlsx", "ScoreCard_swa_20261013_152259.xlsx")  # sem semana

    assert sp.guardar(novo, "swa", "week") == novo
    assert os.path.exists(anterior)


# ---------------- Leitura compartilhada ----------------

@pytest.fixture
def pasta(tmp_path):
    base = tmp_path / "sharepoint"
    base.mkdir()
    settings_store.set_sharepoint_folder(str(base))
    return base


def test_quem_nao_extraiu_ve_o_que_esta_na_pasta(pasta):
    """Outra pessoa extraiu: a semana, o mes, o pico, o gestor e as
    indiretas aparecem para quem abre o app, com a data do arquivo."""
    _por(pasta, "hughes", "week", "summary_gestor_semana.xlsx", "ScoreCard_hughes_20261013_152259_20260830-20260919.xlsx")
    _por(pasta, "hughes", "month", "summary_mes.xlsx", "ScoreCard_hughes_20261001_090000_20260901-20260930.xlsx")
    _por(pasta, "hughes", "peak", "summary_pico.xlsx", "ScoreCard_hughes_20261001_091500_20260901-20260930.xlsx")
    _por(pasta, "hughes", "gestor_week", "summary_gestor_semana.xlsx", "ScoreCard_hughes_20261013_153000_20260830-20260919.xlsx")
    _por(pasta, "hughes", "indiretas", "summary_indiretas.xls", "ScoreCard_hughes_20261012_080000.xls")

    resposta = Api().sincronizar_sharepoint()

    assert {(a["operacao"], a["tipo"]) for a in resposta["atualizados"]} == {
        ("hughes", "week"), ("hughes", "month"), ("hughes", "peak"), ("hughes", "gestor_week"),
        ("hughes", "indiretas")}
    dados = indicators_store.get_indicators("hughes")
    assert sorted(dados["week"]) == ["2026-08-30", "2026-09-06", "2026-09-13"]
    assert dados["week"]["2026-09-06"]["extraido_em"] == "2026-10-13T15:22:59"
    assert list(dados["month"]) == ["2026-09"] and list(dados["peak"]) == ["2026-09"]
    assert grupos_store.da_operacao("gestor", "hughes")
    assert "week:2026-09-06" in coverage_store.extracoes("hughes")["hughes"]
    assert indiretas_store.da_operacao("hughes")

    # Nada mudou na pasta: nao calcula de novo.
    assert Api().sincronizar_sharepoint()["atualizados"] == []


def test_semana_inteira_extraida_pelo_last_week_nao_fica_parcial(pasta):
    _por(pasta, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx")
    Api().sincronizar_sharepoint()
    assert not any(e["parcial"] for e in indicators_store.get_indicators("swa")["week"].values())


def test_arquivo_atrasado_nao_passa_por_cima_do_mais_novo(pasta):
    """O OneDrive pode entregar um arquivo antigo depois de um novo: a
    extracao mais nova e a que vale para o mesmo periodo."""
    api = Api()
    _por(pasta, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20261013_152259_20260901-20260930.xlsx")
    api.sincronizar_sharepoint()
    novo = indicators_store.get_indicators("swa")["month"]["2026-09"]

    # Chega depois um Month mais antigo, do mesmo mes, com outros numeros.
    _por(pasta, "swa", "month", "summary_gestor_mes.xlsx", "ScoreCard_swa_20261005_080000_20260901-20260930.xlsx")
    api.sincronizar_sharepoint()

    depois = indicators_store.get_indicators("swa")["month"]["2026-09"]
    assert depois["extraido_em"] == "2026-10-13T15:22:59"
    assert depois["efetividade"] == novo["efetividade"]


def test_month_antigo_sem_o_mes_no_nome_fica_de_fora_com_o_motivo(pasta):
    _por(pasta, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20261001_090000.xlsx")

    resposta = Api().sincronizar_sharepoint()

    assert resposta["atualizados"] == []
    assert resposta["ignorados"][0]["motivo"].startswith("arquivo antigo")
    assert "month" not in indicators_store.get_indicators("swa")


def test_pico_antigo_sem_periodo_usa_o_mes_dos_dias(pasta):
    _por(pasta, "swa", "peak", "summary_pico.xlsx", "ScoreCard_swa_20261001_090000.xlsx")
    Api().sincronizar_sharepoint()
    assert list(indicators_store.get_indicators("swa")["peak"]) == ["2026-09"]


def test_arquivo_ainda_sendo_gravado_fica_para_a_proxima(pasta):
    _por(pasta, "swa", "week", "summary_3semanas.xlsx",
         "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx", idade=0)

    assert Api().sincronizar_sharepoint()["atualizados"] == []
    resposta = sp.sincronizar(str(pasta), Api()._calcular_indicadores, agora=time.time() + 60)
    assert [a["tipo"] for a in resposta["atualizados"]] == ["week"]


def test_sem_pasta_e_durante_extracao(tmp_path, monkeypatch):
    api = Api()
    assert api.sincronizar_sharepoint().get("sem_pasta")

    settings_store.set_sharepoint_folder(str(tmp_path))
    api._extracoes_em_andamento = 1
    assert api.sincronizar_sharepoint().get("ocupado")


def test_info_da_pasta_mostra_o_mais_novo_de_cada_tipo(pasta):
    _por(pasta, "hughes", "week", "summary_3semanas.xlsx", "ScoreCard_hughes_20261001_080000_20260906-20260912.xlsx")
    _por(pasta, "hughes", "week", "summary_3semanas.xlsx", "ScoreCard_hughes_20261013_152259_20260913-20260919.xlsx")
    _por(pasta, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261014_100000_20260913-20260919.xlsx")

    info = Api().get_sharepoint_info("hughes")
    assert info["pasta"] is True
    assert info["tipos"]["week"]["texto"] == "13/10/2026 15:22"
    assert info["tipos"]["week"]["periodo"] == "13/09 a 19/09/2026"

    todas = Api().get_sharepoint_info("todas")
    assert todas["tipos"]["week"]["operacao"] == "Swa"
    assert Api().get_sharepoint_info("nao_existe") == {"tipos": {}}


def test_o_que_a_pessoa_extraiu_nao_e_calculado_de_novo(pasta):
    api = Api()
    api.sincronizar_sharepoint()  # primeira leitura da pasta (vazia)
    caminho = _por(pasta, "swa", "week", "summary_3semanas.xlsx", "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx")
    api._registrar_no_sharepoint("swa", {"success": True, "tipo": "week", "file_path": caminho})

    assert api.sincronizar_sharepoint()["atualizados"] == []
