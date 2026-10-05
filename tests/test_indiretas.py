"""Horas indiretas: o calculo conferido com a planilha de referencia
(Indicadores Score - SumUp, aba HD) e o caminho ate a tela.

A fixture summary_indiretas.xls e um export real Week + Job Code (so
codigos de atividade e horas, nenhuma pessoa)."""

import datetime
import os

import pytest

from indicators import indiretas, periodos, reader

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "summary_indiretas.xls")
HOJE = datetime.date(2026, 10, 5)


@pytest.fixture
def semanas():
    return indiretas.por_semana(reader.ler(FIXTURE)["linhas"])


def test_semana_de_06_09_igual_a_planilha(semanas):
    """Planilha: 715,26 h totais (Total + UnPd Brk), 135,88 h indiretas,
    19,00%, e cada atividade com as horas e o % dela."""
    semana = semanas["2026-09-06"]
    assert semana["horas_totais"] == 715.26
    assert semana["horas_indiretas"] == 135.88
    assert round(semana["percentual"] * 100, 2) == 19.00
    assert [(a["atividade"], a["horas"]) for a in semana["atividades"]] == [
        ("LUNCH", 67.0), ("ISTART", 26.16), ("MEET", 22.48), ("PRESHIFT", 12.0),
        ("IEND", 7.31), ("CAFE", 0.48), ("eAPOIO", 0.27), ("INVT", 0.18)]
    pcts = {a["atividade"]: round(a["percentual"] * 100, 2) for a in semana["atividades"]}
    assert pcts["LUNCH"] == 9.37 and pcts["ISTART"] == 3.66 and pcts["MEET"] == 3.14


def test_sempre_da_maior_para_a_menor(semanas):
    for semana in semanas.values():
        horas = [a["horas"] for a in semana["atividades"]]
        assert horas == sorted(horas, reverse=True)
        assert sum(a["percentual_indiretas"] for a in semana["atividades"]) == pytest.approx(1, abs=1e-4)


def test_regra_da_atividade_indireta():
    """Indireta: Unmeasured Signon Indirect (H), PD Brk (K) ou UnPd Brk
    (M) diferente de zero. Direta, mesmo com Signon Direct, nao entra
    (APOIO na planilha)."""
    linhas = [
        {"semana": "2026-09-06", "detalhe": "LUNCH", "unpd_brk": 10, "total": 0},
        {"semana": "2026-09-06", "detalhe": "PRESHIFT", "pd_brk": 2, "total": 2},
        {"semana": "2026-09-06", "detalhe": "MEET", "signon_indirect": 3, "total": 3},
        {"semana": "2026-09-06", "detalhe": "APOIO", "signon_direct": 5, "total": 5},
        {"semana": "2026-09-06", "detalhe": "PCK", "measured_direct": 80, "total": 80},
    ]
    semana = indiretas.por_semana(linhas)["2026-09-06"]
    assert semana["horas_totais"] == 100  # 90 de Total + 10 de refeicao
    assert semana["horas_indiretas"] == 15
    assert [a["atividade"] for a in semana["atividades"]] == ["LUNCH", "MEET", "PRESHIFT"]


def test_acima_de_15_por_cento_e_vermelho():
    assert indiretas.cor(0.15) == "verde"
    assert indiretas.cor(0.1501) == "vermelho"
    assert indiretas.cor(None) is None


def _salvar(operacao="sumup"):
    import indiretas_store

    semanas = indiretas.por_semana(reader.ler(FIXTURE)["linhas"])
    for chave, semana in semanas.items():
        semana["parcial"] = periodos.semana_parcial(chave, "2026-08-30", "2026-10-03")
    indiretas_store.salvar(operacao, semanas, "2026-08-30", "2026-10-03")


def test_tela_mostra_as_semanas_do_mes():
    import indiretas_tela

    _salvar()
    tela = indiretas_tela.montar("sumup", "2026-09", None, hoje=HOJE)
    assert [s["rotulo"] for s in tela["semanas"]] == ["Week 36", "Week 37", "Week 38", "Week 39", "Week 40"]
    # Sem semana escolhida, a mais recente do mes.
    assert tela["semana_id"] == "2026-W40"
    assert tela["cards"]["percentual"] == pytest.approx(60.55 / 437.32, abs=1e-6)
    assert tela["cards"]["cor"] == "verde"
    assert [s["cor"] for s in tela["semanas"]] == ["vermelho"] * 4 + ["verde"]
    # Tabela: atividades da que mais pesa no mes para a que menos.
    nomes = [l["atividade"] for l in tela["tabela"]["linhas"]]
    assert nomes[:3] == ["LUNCH", "ISTART", "MEET"]
    assert tela["tabela"]["linhas"][2]["celulas"]["2026-W40"] is None, "MEET nao aparece na Week 40"
    assert tela["semanas"][0]["atividades"][0]["maior"] is True
    assert "5 semanas" in tela["ultima_extracao"]


def test_semana_escolhida_e_mes_sem_extracao():
    import indiretas_tela

    _salvar()
    tela = indiretas_tela.montar("sumup", "2026-09", "2026-W37", hoje=HOJE)
    assert tela["cards"]["horas_totais"] == 715.26
    vazio = indiretas_tela.montar("hugo_boss", "2026-09", None, hoje=HOJE)
    assert vazio["semanas"] == [] and vazio["cards"]["percentual"] is None
    assert vazio["mes_anterior"] is None


def test_todas_as_operacoes_somam_a_mesma_semana():
    import indiretas_tela

    _salvar("sumup")
    _salvar("abb")
    tela = indiretas_tela.montar("todas", "2026-09", "2026-W37", hoje=HOJE)
    semana = next(s for s in tela["semanas"] if s["id"] == "2026-W37")
    assert semana["horas_totais"] == pytest.approx(2 * 715.26)
    assert semana["percentual"] == pytest.approx(135.88 / 715.26, abs=1e-6)


def test_extracao_de_indiretas_grava_e_vai_para_a_pasta_indiretas(operations, sharepoint_dir):
    """De ponta a ponta contra o relatorio de mock: Group By 2 fixo em
    Job Code (mesmo pedindo outro), arquivo na pasta Indiretas e as
    semanas gravadas para a tela."""
    import api as api_mod
    import indiretas_store
    from automation import generic

    operations("mock", "Mock Co", "MockCo")
    result = generic.run("mock", base_dir=str(sharepoint_dir), headless=True,
                         username="usuario", password="senha", group_by="User ID",
                         date_range={"from_date": "2026-08-30", "to_date": "2026-10-03"},
                         period="indiretas")
    assert result["success"], result.get("message")
    assert result["group_by"] == "Job Code"
    assert result["period_type"] == "Indiretas"
    assert os.path.basename(os.path.dirname(result["file_path"])) == "Indiretas"

    api_mod.Api()._calcular_indicadores("mock", result)
    guardado = indiretas_store.da_operacao("mock")
    assert guardado["2026-09-06"]["horas_indiretas"] == 135.88
    assert result["indicators"] == 5
