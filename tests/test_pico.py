"""Dias de pico e os sabados da escala espanhola.

A conferencia do pico e contra a planilha de referencia
(Calculo_ScoreCard.xlsx, aba Summary): os numeros da fixture
summary_pico.xlsx sao os dela, no formato do export real. Nela, o
primeiro dia do ranking e o sabado 19/09/2026 — um dos dois ultimos
sabados de setembro — entao o resultado depende da escala.
"""

import datetime
import os

import pytest

from indicators import pico, presenteismo, reader

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "summary_pico.xlsx")


def _linhas():
    return reader.ler(FIXTURE)["linhas"]


# ---------------- Calculo ----------------

def test_pico_na_escala_espanhola_bate_com_a_planilha():
    resultado = pico.calcular(_linhas(), "2026-09", escala_espanhola=True)

    # Celula U2 da planilha: 0,968217793...
    assert resultado["hora_direta"] == pytest.approx(0.968218, abs=1e-6)
    assert [d["data"] for d in resultado["dias"]] == [
        "2026-09-19", "2026-09-18", "2026-09-11", "2026-09-04", "2026-09-09"]


def test_fora_da_escala_espanhola_o_sabado_sai_e_entra_o_sexto_dia():
    resultado = pico.calcular(_linhas(), "2026-09", escala_espanhola=False)

    assert resultado["hora_direta"] == pytest.approx(0.965699, abs=1e-6)
    assert "2026-09-19" not in [d["data"] for d in resultado["dias"]]
    assert resultado["dias"][-1]["data"] == "2026-09-03"
    assert resultado["ignorados"] == [{"data": "2026-09-19", "motivo": "sabado fora da escala"}]


def test_pico_e_agregado_e_nao_a_media_dos_dias():
    resultado = pico.calcular(_linhas(), "2026-09", escala_espanhola=True)
    media = sum(d["hora_direta"] for d in resultado["dias"]) / 5

    assert media == pytest.approx(0.97316, abs=1e-5)
    assert resultado["hora_direta"] != pytest.approx(media, abs=1e-4)


def _linha(data, diretas, total):
    return {"detalhe": data, "measured_direct": diretas, "signon_direct": 0.0,
            "insert_direct": 0.0, "total": total, "pd_brk": 0.0}


def test_domingo_primeiros_sabados_e_outro_mes_nunca_entram():
    linhas = [
        _linha("20/09/2026", 99, 100),   # domingo
        _linha("05/09/2026", 99, 100),   # 1o sabado: folga na escala espanhola
        _linha("30/08/2026", 99, 100),   # outro mes
        _linha("01/09/2026", 90, 100),
    ]
    resultado = pico.calcular(linhas, "2026-09", escala_espanhola=True)

    assert [d["data"] for d in resultado["dias"]] == ["2026-09-01"]
    assert {i["motivo"] for i in resultado["ignorados"]} == {
        "domingo", "sabado fora da escala", "fora do mes"}


def test_sem_dia_valido_nao_ha_pico():
    assert pico.calcular([_linha("20/09/2026", 99, 100)], "2026-09")["hora_direta"] is None


# ---------------- Sabados da escala espanhola ----------------

def test_dois_ultimos_sabados_do_mes():
    setembro = [d for d in range(1, 31) if presenteismo.sabado_trabalhado(datetime.date(2026, 9, d))]
    outubro = [d for d in range(1, 32) if presenteismo.sabado_trabalhado(datetime.date(2026, 10, d))]
    assert setembro == [19, 26]
    assert outubro == [24, 31], "mes com cinco sabados: o 4o e o 5o"


def test_dias_uteis_da_escala_espanhola():
    semana = (datetime.date(2026, 9, 14), datetime.date(2026, 9, 20))
    assert presenteismo.dias_uteis(*semana) == 5
    assert presenteismo.dias_uteis(*semana, escala_espanhola=True) == 6

    primeira = (datetime.date(2026, 9, 1), datetime.date(2026, 9, 6))
    assert presenteismo.dias_uteis(*primeira, escala_espanhola=True) == 4, "5/09 e folga"

    # Ciclo da folha 13/09 -> 12/10: ganha os sabados 19 e 26/09.
    ciclo = (datetime.date(2026, 9, 13), datetime.date(2026, 10, 12))
    assert presenteismo.dias_uteis(*ciclo) == 21
    assert presenteismo.dias_uteis(*ciclo, escala_espanhola=True) == 23


def test_headcount_usa_a_escala_de_cada_gestor():
    import headcount
    import headcount_store

    for nome, operacao in (("G_HUGO", "hugo_boss"), ("G_NIKE", "nike_fisia")):
        gestor = headcount_store.adicionar_gestor(nome, operacao)
        headcount_store.atualizar_gestor(gestor["id"], {"hc": 10})

    hoje = datetime.date(2026, 10, 20)
    tela = headcount.montar("todas", "semanal", "2026-09", "2026-09-S3", hoje=hoje)
    dias = {linha["gestor"]: linha["dias_uteis"] for linha in tela["linhas"]}
    assert dias == {"G_HUGO": 5, "G_NIKE": 6}

    ciclo = headcount.montar("nike_fisia", "mes", None, "2026-09-13", hoje=hoje)
    assert ciclo["linhas"][0]["dias_uteis"] == 23
    assert ciclo["cards"]["periodo_nota"].endswith("23 dias uteis")


# ---------------- Extracao e a coluna Pico ----------------

DATAS = {"from_date": "2026-09-01", "to_date": "2026-09-19"}


@pytest.fixture
def api(sharepoint_dir, monkeypatch):
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    instancia = Api()
    instancia.login("usuario", "senha")
    instancia._emit_js = lambda fn, payload: None
    return instancia


def test_extracao_de_pico_vai_para_a_pasta_e_usa_report_date(api, operations, sharepoint_dir):
    operations("mock", "Mock Co", "MockCo")

    # O Group By escolhido na tela e ignorado: no pico e sempre Report Date.
    result = api.run_extraction("mock", date_range=DATAS, group_by="User ID", period="peak")

    assert result["success"], result.get("message")
    assert result["status"] == "success", result.get("indicators_message")
    assert result["group_by"] == "Report Date"
    assert os.path.dirname(result["file_path"]) == os.path.join(str(sharepoint_dir), "MockCo", "Dias de Pico")

    import indicators_store
    guardado = indicators_store.get_indicators("mock")["peak"]["2026-09"]
    assert guardado["hora_direta"] == pytest.approx(0.965699, abs=1e-6)
    assert guardado["parcial"], "extraido so ate 19/09"


def test_coluna_pico_fica_depois_do_mes_e_usa_os_indicadores_dele(api, operations):
    import indicators_store
    from indicators import limits

    operations("mock", "Mock Co", "MockCo")
    indicators_store.salvar_extracao("mock", "week", {"2026-09-14": {"efetividade": 1.0}})
    indicators_store.salvar_extracao("mock", "month", {"2026-09": {
        "efetividade": 1.004, "hora_direta": 0.93, "dispersao": 0.6}})
    assert api.run_extraction("mock", date_range=DATAS, period="peak")["success"]

    tabela = api.get_indicator_table("mock")
    chaves = [c["chave"] for c in tabela["colunas"]]
    assert chaves == ["2026-09-14", "2026-09", "pico-2026-09"]

    coluna = tabela["colunas"][2]
    assert coluna["titulo"] == "Pico" and coluna["parcial"]
    assert "18/09" in coluna["dica"]

    celulas = {l["chave"]: l["celulas"][2] for l in tabela["linhas"]}
    assert celulas["hora_direta"]["texto"] == limits.formatar(0.965699)
    assert celulas["efetividade"]["texto"] == limits.formatar(1.004), "a do mes"
    assert celulas["dispersao"]["texto"] == limits.formatar(0.6), "a do mes"
    assert celulas["coverage"] == {"texto": "", "cor": "", "nao_se_aplica": True}
    # Sem presenteismo (nenhum headcount), sem cubo — igual ao mes.
    assert celulas["cubo"]["texto"] == ""


def test_cubo_do_pico_usa_a_hora_direta_do_pico(api, operations, monkeypatch):
    import headcount
    import indicators_store
    from indicators import limits

    operations("mock", "Mock Co", "MockCo")
    indicators_store.salvar_extracao("mock", "month", {"2026-09": {"efetividade": 1.004, "hora_direta": 0.93}})
    indicators_store.salvar_extracao("mock", "peak", {"2026-09": {"hora_direta": 0.965699, "dias": []}})
    monkeypatch.setattr(headcount, "presenteismo_por_periodo", lambda op, hoje=None: {
        "week": {}, "month": {"2026-09": {"presenteismo": 0.99, "de": "2026-09-13", "ate": "2026-10-12"}}})

    tabela = api.get_indicator_table("mock")
    cubo = next(l for l in tabela["linhas"] if l["chave"] == "cubo")["celulas"]

    assert cubo[0]["texto"] == limits.formatar(1.004 * 0.93 * 0.99), "o do mes"
    assert cubo[1]["texto"] == limits.formatar(1.004 * 0.965699 * 0.99), "o do pico"
