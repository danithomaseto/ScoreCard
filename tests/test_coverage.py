"""Aba Coverage: horas do Summary por usuario, dias/horas/sinergias
digitados e o coverage por usuario e total.

O calculo e conferido contra a planilha de referencia (Indicadores
Score, aba COVERAGE W): (Horas LMS - Diretas sem meta) / (Horas Metrics
+ Sinergia recebida - Sinergia cedida), com Metrics = 5 x 8,75.
"""

import datetime
import os

import pytest

import coverage_store
import coverage_tela
from indicators import coverage, limits

# Linhas da aba SUMMARY W da planilha (User ID, Horas LMS, Diretas sem meta).
PLANILHA = {
    "ESANTOS": (43.4, 0.0), "EMENDES1": (43.1, 0.0), "MNSILVA": (36.03, 0.14),
    "RFLORIANO1": (43.57, 0.0), "LAGOSTINHO1": (43.64, 0.0), "ALRODRIGUES": (44.43, 0.0),
    "MDOMINGOS": (26.83, 0.0),
}
SEMANA = "2026-09-20"  # ABB fecha a semana no domingo


def _usuarios():
    return {u: {"lms": l, "diretas_sem_meta": d} for u, (l, d) in PLANILHA.items()}


def _extrair(operacao="abb", semana=SEMANA, usuarios=None, de=None, ate=None):
    coverage_store.salvar_extracao(operacao, "week", {semana: usuarios or _usuarios()}, de, ate)


# ---------------- Calculo ----------------

def test_calculo_por_usuario_bate_com_a_planilha():
    linha = coverage.linha("ESANTOS", {"lms": 43.4, "diretas_sem_meta": 0}, {}, dias_padrao=5)
    assert linha["metrics"] == pytest.approx(43.75)
    assert linha["coverage"] == pytest.approx(0.992)  # celula I2
    mnsilva = coverage.linha("MNSILVA", {"lms": 36.03, "diretas_sem_meta": 0.14}, {}, dias_padrao=5)
    assert mnsilva["coverage"] == pytest.approx(0.8203428571, abs=1e-6)  # celula I4


def test_total_bate_com_a_planilha():
    """Na planilha, MDOMINGOS (sinergia de outra operacao) tem horas no
    LMS mas nao tem Metrics: aqui isso e dias = 0 para ele."""
    linhas = [coverage.linha(u, h, {"dias": 0} if u == "MDOMINGOS" else {}, dias_padrao=5)
              for u, h in _usuarios().items()]
    total = coverage.total(linhas)
    assert (total["lms"], total["metrics"], total["diretas_sem_meta"]) == (281.0, 262.5, 0.14)
    assert total["coverage"] == pytest.approx(1.069942857, abs=1e-6)  # celula I16


def test_sinergias_entram_no_denominador():
    linha = coverage.linha("X", {"lms": 40, "diretas_sem_meta": 2},
                           {"cedida": 4, "recebida": 10}, dias_padrao=5, horas_padrao=8)
    assert linha["coverage"] == pytest.approx((40 - 2) / (40 + 10 - 4))


def test_por_usuario_le_total_e_signon_direct_das_linhas_do_export():
    from indicators import reader

    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "summary_3semanas.xlsx")
    semanas = coverage.por_semana_e_usuario(reader.ler(fixture)["linhas"])
    semana, usuarios = sorted(semanas.items())[0]
    linha = next(l for l in reader.ler(fixture)["linhas"]
                 if l["semana"] == semana and l["detalhe"] == sorted(usuarios)[0])
    primeiro = usuarios[sorted(usuarios)[0]]
    assert primeiro == {"lms": round(linha["total"], 4),
                        "diretas_sem_meta": round(linha["signon_direct"] or 0.0, 4)}


# ---------------- Tela ----------------

HOJE = datetime.date(2026, 9, 29)


def test_tela_semanal_abre_na_ultima_semana_extraida():
    _extrair(semana="2026-09-13")
    _extrair()
    tela = coverage_tela.montar("abb", "semanal", "2026-09", None, hoje=HOJE)

    assert [p["rotulo"] for p in tela["periodos"]] == ["Week 38 · 13/09 a 19/09", "Week 39 · 20/09 a 26/09"]
    assert tela["periodo_id"] == "2026-W39"
    assert len(tela["linhas"]) == 7
    esantos = next(l for l in tela["linhas"] if l["usuario"] == "ESANTOS")
    assert (esantos["operacao"], esantos["dias"], esantos["horas"]) == ("ABB", 5, 8.75)
    assert esantos["coverage"] == pytest.approx(0.992)


def test_dias_da_semana_parcial_e_da_escala_espanhola():
    # Semana 30/08 a 05/09 extraida so a partir de 01/09: 4 dias uteis.
    _extrair(semana="2026-08-30", de="2026-09-01", ate="2026-09-26")
    linha = coverage_tela.montar("abb", "semanal", "2026-09", "2026-W36", hoje=HOJE)["linhas"][0]
    assert linha["dias"] == 4
    # Rede trabalha o sabado 26/09 (um dos dois ultimos do mes).
    _extrair(operacao="rede")
    linha = coverage_tela.montar("rede", "semanal", "2026-09", "2026-W39", hoje=HOJE)["linhas"][0]
    assert linha["dias"] == 6


def test_todas_as_operacoes_junta_a_mesma_week_de_domingo_e_de_segunda():
    _extrair(operacao="abb", semana="2026-09-20", usuarios={"A1": {"lms": 40, "diretas_sem_meta": 0}})
    _extrair(operacao="lego", semana="2026-09-21", usuarios={"L1": {"lms": 30, "diretas_sem_meta": 0}})
    tela = coverage_tela.montar("todas", "semanal", "2026-09", None, hoje=HOJE)

    assert [p["id"] for p in tela["periodos"]] == ["2026-W39"]
    assert [(l["usuario"], l["operacao"]) for l in tela["linhas"]] == [("A1", "ABB"), ("L1", "Lego")]
    assert tela["total"]["lms"] == 70


def test_resultado_do_mes_vem_da_extracao_month():
    coverage_store.salvar_extracao("abb", "month", {"2026-09": _usuarios()}, "2026-09-01", "2026-09-26")
    tela = coverage_tela.montar("abb", "mes", "2026-09", None, hoje=HOJE)

    esantos = next(l for l in tela["linhas"] if l["usuario"] == "ESANTOS")
    assert esantos["dias"] == 19  # dias uteis de 01 a 26/09/2026 (01/09 e terca)
    assert tela["cards"]["periodo_nota"] == "Extração Month · 01/09 a 26/09"
    # Agosto tem semana extraida, mas nao tem Month: sem linhas.
    _extrair(semana="2026-08-16")
    agosto = coverage_tela.montar("abb", "mes", "2026-08", None, hoje=HOJE)
    assert (agosto["mes"], agosto["linhas"]) == ("2026-08", [])


# ---------------- Campos digitados ----------------

@pytest.fixture
def api_obj():
    from api import Api

    return Api()


def test_digitado_vale_e_sobrevive_a_nova_extracao(api_obj):
    _extrair()
    chave = coverage_store.chave("week", SEMANA)
    assert api_obj.set_coverage("abb", chave, "ESANTOS", "dias", "4")["success"]
    assert api_obj.set_coverage("abb", chave, "ESANTOS", "recebida", "5,5")["success"]

    _extrair()  # extraiu a mesma semana de novo
    esantos = next(l for l in coverage_tela.montar("abb", "semanal", "2026-09", "2026-W39", hoje=HOJE)["linhas"]
                   if l["usuario"] == "ESANTOS")

    assert (esantos["dias"], esantos["dias_origem"], esantos["recebida"]) == (4, "digitado", 5.5)
    assert esantos["coverage"] == pytest.approx(43.4 / (4 * 8.75 + 5.5))


def test_valores_invalidos_sao_recusados(api_obj):
    _extrair()
    chave = coverage_store.chave("week", SEMANA)
    for campo, valor in (("dias", "-1"), ("dias", "2.5"), ("dias", "40"), ("horas", "25"),
                         ("cedida", "abc"), ("nao_existe", "1")):
        assert not api_obj.set_coverage("abb", chave, "ESANTOS", campo, valor)["success"], (campo, valor)
    assert not api_obj.set_coverage("nao_existe", chave, "ESANTOS", "dias", "1")["success"]


def test_para_todos_aplica_na_tela_inteira(api_obj):
    _extrair()
    resposta = api_obj.set_coverage_todos("abb", "semanal", "2026-09", "2026-W39", "dias", "4")

    assert resposta == {"success": True, "usuarios": 7}
    linhas = coverage_tela.montar("abb", "semanal", "2026-09", "2026-W39", hoje=HOJE)["linhas"]
    assert {l["dias"] for l in linhas} == {4}
    assert not api_obj.set_coverage_todos("abb", "semanal", "2026-09", "2026-W39", "cedida", "1")["success"]


# ---------------- Aba Inicio ----------------

def test_inicio_mostra_o_coverage_total(api_obj):
    import indicators_store

    indicators_store.salvar_extracao("abb", "week", {SEMANA: {"efetividade": 1.0}})
    _extrair()
    api_obj.set_coverage("abb", coverage_store.chave("week", SEMANA), "MDOMINGOS", "dias", "0")

    tabela = api_obj.get_indicator_table("abb", mes="2026-09")
    linha = next(l for l in tabela["linhas"] if l["chave"] == "coverage")

    assert linha["celulas"][0]["texto"] == limits.formatar(1.069942857)
    assert linha["celulas"][0]["cor"] == "verde", "entre 92% e 110%"


# ---------------- Extracao ----------------

@pytest.fixture
def api_logada(sharepoint_dir, monkeypatch):
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    instancia = Api()
    instancia.login("usuario", "senha")
    instancia._emit_js = lambda fn, payload: None
    return instancia


def test_extracao_week_e_month_guardam_as_horas_por_usuario(api_logada, operations):
    operations("mock", "Mock Co", "MockCo")
    datas = {"from_date": "2026-09-01", "to_date": "2026-09-19"}

    assert api_logada.run_extraction("mock", date_range=datas, period="week")["success"]
    assert api_logada.run_extraction("mock", date_range=datas, period="month")["success"]

    guardado = coverage_store.extracoes("mock")["mock"]
    semanas = [k for k in guardado if k.startswith("week:")]
    assert semanas and all(guardado[k]["usuarios"] for k in semanas)
    assert guardado["month:2026-09"]["usuarios"]
    usuario, horas = next(iter(guardado["month:2026-09"]["usuarios"].items()))
    assert set(horas) == {"lms", "diretas_sem_meta"} and horas["lms"] > 0


# ---------------- Sinergia da operacao ----------------

def test_sinergia_da_operacao_entra_so_no_total(api_obj):
    _extrair()
    chave = coverage_store.chave("week", SEMANA)
    assert api_obj.set_coverage_sinergia("abb", chave, "recebida", "20")["success"]
    assert api_obj.set_coverage_sinergia("abb", chave, "cedida", "5,5")["success"]

    tela = coverage_tela.montar("abb", "semanal", "2026-09", "2026-W39", hoje=HOJE)
    total = tela["total"]

    esantos = next(l for l in tela["linhas"] if l["usuario"] == "ESANTOS")
    assert esantos["coverage"] == pytest.approx(0.992), "a linha do usuario nao muda"
    assert (total["recebida_operacao"], total["cedida_operacao"]) == (20, 5.5)
    assert total["coverage"] == pytest.approx((281 - 0.14) / (7 * 43.75 + 20 - 5.5))
    assert total["sinergia_editavel"] and total["chave_periodo"] == chave


def test_sinergia_por_usuario_soma_com_a_da_operacao(api_obj):
    _extrair()
    chave = coverage_store.chave("week", SEMANA)
    api_obj.set_coverage_sinergia("abb", chave, "recebida", "20")
    api_obj.set_coverage("abb", chave, "ESANTOS", "recebida", "3")

    total = coverage_tela.montar("abb", "semanal", "2026-09", "2026-W39", hoje=HOJE)["total"]
    assert (total["recebida"], total["recebida_usuarios"], total["recebida_operacao"]) == (23, 3, 20)


def test_sinergia_da_operacao_chega_ao_inicio(api_obj):
    import indicators_store

    indicators_store.salvar_extracao("abb", "week", {SEMANA: {"efetividade": 1.0}})
    _extrair()
    api_obj.set_coverage_sinergia("abb", coverage_store.chave("week", SEMANA), "cedida", "10")

    tabela = api_obj.get_indicator_table("abb", mes="2026-09")
    celula = next(l for l in tabela["linhas"] if l["chave"] == "coverage")["celulas"][0]
    assert celula["texto"] == limits.formatar((281 - 0.14) / (7 * 43.75 - 10))


def test_todas_as_operacoes_soma_a_sinergia_e_nao_deixa_digitar(api_obj):
    _extrair(operacao="abb", semana="2026-09-20", usuarios={"A1": {"lms": 40, "diretas_sem_meta": 0}})
    _extrair(operacao="lego", semana="2026-09-21", usuarios={"L1": {"lms": 30, "diretas_sem_meta": 0}})
    api_obj.set_coverage_sinergia("abb", "week:2026-09-20", "recebida", "4")
    api_obj.set_coverage_sinergia("lego", "week:2026-09-21", "recebida", "6")

    total = coverage_tela.montar("todas", "semanal", "2026-09", None, hoje=HOJE)["total"]
    assert total["recebida"] == 10
    assert not total["sinergia_editavel"]
    assert not api_obj.set_coverage_sinergia("todas", "week:2026-09-20", "recebida", "1")["success"]
