"""Faltas digitadas na tela de Headcount, por gestor e por periodo, e o
caminho delas ate a aba Inicio e o cubo.

A planilha de faltas esta desligada (headcount.FALTAS_DA_PLANILHA); o
numero que a tela de Headcount mostra para uma semana ou um ciclo e o
mesmo que vai para o Inicio.
"""

import datetime

import pytest

import headcount
import headcount_store
import indicators_store
from indicators import limits

HOJE = datetime.date(2026, 10, 20)  # setembro inteiro ja passou


@pytest.fixture
def api_obj():
    from api import Api

    return Api()


def _gestor(nome="Daniel Thomaseto", operacao="hugo_boss", hc=5):
    gestor = headcount_store.adicionar_gestor(nome, operacao)
    headcount_store.atualizar_gestor(gestor["id"], {"hc": hc})
    return gestor


def _celulas(api_obj, indicador, operacao="hugo_boss", mes="2026-09"):
    tabela = api_obj.get_indicator_table(operacao, mes=mes)
    linha = next(l for l in tabela["linhas"] if l["chave"] == indicador)
    return {c["chave"]: cel["texto"] for c, cel in zip(tabela["colunas"], linha["celulas"])}


def test_a_tela_esta_no_modo_de_faltas_digitadas():
    assert headcount.FALTAS_DA_PLANILHA is False
    tela = headcount.montar("hugo_boss", "semanal", "2026-09", "2026-09-S2", hoje=HOJE)
    assert tela["faltas_manuais"] is True


def test_lancar_faltas_na_semana(api_obj):
    gestor = _gestor()

    assert api_obj.set_faltas(gestor["id"], "2026-09-S2", "1")["success"]

    tela = headcount.montar("hugo_boss", "semanal", "2026-09", "2026-09-S2", hoje=HOJE)
    linha = tela["linhas"][0]
    assert (linha["faltas"], linha["dias_uteis"], linha["faltas_editavel"]) == (1, 5, True)
    assert linha["presenteismo"] == pytest.approx(1 - 8 / (5 * 5 * 8))


def test_sem_todas_as_semanas_abre_na_ultima_encerrada(api_obj):
    """Sem semana escolhida (ou pedindo "todas"), a tela abre na ultima
    semana ja encerrada do mes: em 28/09/2026, a S4 (21 a 27/09)."""
    gestor = _gestor()
    hoje = datetime.date(2026, 9, 28)

    for pedido in (None, "todas"):
        tela = headcount.montar("hugo_boss", "semanal", "2026-09", pedido, hoje=hoje)
        assert tela["periodo_id"] == "2026-09-S4"
        assert "todas" not in [p["id"] for p in tela["periodos"]]
    assert not api_obj.set_faltas(gestor["id"], "todas", "1")["success"]


def test_semanas_com_o_nome_do_inicio():
    tela = headcount.montar("hugo_boss", "semanal", "2026-09", None, hoje=HOJE)
    assert [p["rotulo"] for p in tela["periodos"]] == [
        "Week 36 · 01/09 a 06/09", "Week 37 · 07/09 a 13/09", "Week 38 · 14/09 a 20/09",
        "Week 39 · 21/09 a 27/09", "Week 40 · 28/09 a 30/09"]


def test_so_numero_inteiro_nao_negativo(api_obj):
    gestor = _gestor()
    for invalido in ("-1", "1.5", "abc"):
        resposta = api_obj.set_faltas(gestor["id"], "2026-09-S2", invalido)
        assert not resposta["success"], invalido

    api_obj.set_faltas(gestor["id"], "2026-09-S2", "2")
    api_obj.set_faltas(gestor["id"], "2026-09-S2", "")
    assert headcount_store.listar_gestores()[0].get("quadro", {}) == {}, "vazio apaga"


def test_presenteismo_da_semana_vai_para_o_inicio_e_gera_o_cubo(api_obj):
    """O caso da tela: HC 5 na S2 (07/09 a 13/09) da Hugo Boss."""
    gestor = _gestor()
    indicators_store.salvar_extracao("hugo_boss", "week", {
        "2026-09-07": {"efetividade": 1.0, "hora_direta": 0.9}})
    api_obj.set_faltas(gestor["id"], "2026-09-S2", "1")

    tela = headcount.montar("hugo_boss", "semanal", "2026-09", "2026-09-S2", hoje=HOJE)
    no_headcount = tela["linhas"][0]["presenteismo"]

    assert _celulas(api_obj, "presenteismo")["2026-09-07"] == limits.formatar(no_headcount)
    assert _celulas(api_obj, "cubo")["2026-09-07"] == limits.formatar(1.0 * 0.9 * no_headcount)


def test_semana_sem_falta_lancada_conta_como_zero(api_obj):
    """Igual a tela de Headcount mostra: sem lancamento, 0 falta, 100%."""
    _gestor()
    indicators_store.salvar_extracao("hugo_boss", "week", {"2026-09-07": {"efetividade": 1.0}})

    assert _celulas(api_obj, "presenteismo")["2026-09-07"] == "100,0%"


def test_semana_da_virada_do_mes_soma_os_dois_pedacos(api_obj):
    """31/08 a 06/09 = S6 de agosto (31/08; agosto/2026 comeca num sabado) + S1 de
    setembro (01 a 06/09)."""
    gestor = _gestor()
    indicators_store.salvar_extracao("hugo_boss", "week", {"2026-08-31": {"efetividade": 1.0}})
    api_obj.set_faltas(gestor["id"], "2026-08-S6", "1")
    api_obj.set_faltas(gestor["id"], "2026-09-S1", "1")

    # 5 dias uteis (seg 31/08 + ter a sex 01 a 04/09), 2 faltas.
    assert _celulas(api_obj, "presenteismo")["2026-08-31"] == limits.formatar(1 - 2 / (5 * 5))


def test_mes_do_inicio_e_o_ciclo_da_folha(api_obj):
    gestor = _gestor()
    api_obj.set_faltas(gestor["id"], "2026-09-13", "2")

    ciclo = headcount.montar("hugo_boss", "mes", None, "2026-09-13", hoje=HOJE)["linhas"][0]
    vivo = headcount.presenteismo_por_periodo("hugo_boss", hoje=HOJE, semanas=[], meses=["2026-09"])

    assert ciclo["dias_uteis"] == 21
    assert vivo["month"]["2026-09"]["presenteismo"] == pytest.approx(1 - 2 / (5 * 21), abs=1e-6)
    assert vivo["month"]["2026-09"]["presenteismo"] == ciclo["presenteismo"]


def test_escala_espanhola_conta_os_sabados(api_obj):
    gestor = _gestor(operacao="nike_fisia")
    api_obj.set_faltas(gestor["id"], "2026-09-S3", "3")

    vivo = headcount.presenteismo_por_periodo("nike_fisia", hoje=HOJE, semanas=["2026-09-14"], meses=[])

    # 14 a 20/09: seg a sex + sabado 19 (um dos dois ultimos) = 6 dias.
    assert vivo["week"]["2026-09-14"]["presenteismo"] == pytest.approx(1 - 3 / (5 * 6), abs=1e-6)


def test_semana_futura_e_operacao_sem_gestor_ficam_sem_numero():
    _gestor()
    vivo = headcount.presenteismo_por_periodo("hugo_boss", hoje=datetime.date(2026, 9, 10),
                                              semanas=["2026-09-14"], meses=[])
    assert vivo["week"] == {}
    assert headcount.presenteismo_por_periodo("lego", hoje=HOJE) == {"week": {}, "month": {}}


def test_editar_e_mudar_de_operacao_mantem_as_faltas(api_obj):
    gestor = _gestor()
    api_obj.set_faltas(gestor["id"], "2026-09-S2", "2")

    api_obj.edit_gestor(gestor["id"], "D. Thomaseto", "lego")

    linha = headcount.montar("lego", "semanal", "2026-09", "2026-09-S2", hoje=HOJE)["linhas"][0]
    assert (linha["gestor"], linha["faltas"]) == ("D. Thomaseto", 2)


# ---------------- Quadro por semana ----------------

def _linha(semana, hoje=HOJE, operacao="hugo_boss", visualizacao="semanal", mes="2026-09"):
    return headcount.montar(operacao, visualizacao, mes, semana, hoje=hoje)["linhas"][0]


def test_cada_semana_tem_o_seu_hc_dias_horas_e_faltas(api_obj):
    gestor = _gestor(hc=5)
    for campo, valor in (("hc", "3"), ("dias_uteis", "4"), ("horas_dia", "6"), ("faltas", "1")):
        assert api_obj.set_quadro(gestor["id"], "2026-09-S3", campo, valor)["success"]

    s3, s2 = _linha("2026-09-S3"), _linha("2026-09-S2")

    assert (s3["hc"], s3["dias_uteis"], s3["horas_dia"], s3["faltas"]) == (3, 4, 6.0, 1)
    assert s3["presenteismo"] == pytest.approx(1 - 1 / (3 * 4))
    assert (s2["hc"], s2["dias_uteis"], s2["horas_dia"], s2["faltas"]) == (5, 5, 8.0, 0), \
        "a semana anterior nao muda"


def test_hc_e_horas_herdam_da_semana_anterior_ate_mudar(api_obj):
    gestor = _gestor(hc=5)
    api_obj.set_quadro(gestor["id"], "2026-09-S2", "hc", "3")

    s4 = _linha("2026-09-S4")
    assert (s4["hc"], s4["hc_origem"], s4["hc_de"]) == (3, "herdado", "Week 37")
    assert (s4["dias_uteis"], s4["dias_origem"]) == (5, "calendario"), "dias vem do calendario"
    assert s4["faltas"] == 0, "falta nao se herda"

    api_obj.set_quadro(gestor["id"], "2026-09-S4", "hc", "4")
    assert (_linha("2026-09-S4")["hc"], _linha("2026-09-S4")["hc_origem"]) == (4, "digitado")
    assert _linha("2026-09-S5")["hc"] == 4, "vale dali pra frente"
    assert _linha("2026-09-S1")["hc"] == 5, "semana anterior a mudanca fica com o cadastro"

    api_obj.set_quadro(gestor["id"], "2026-09-S4", "hc", "")
    assert _linha("2026-09-S4")["hc"] == 3, "vazio volta a herdar"


def test_ciclo_da_folha_tem_os_seus_numeros(api_obj):
    gestor = _gestor(hc=5)
    api_obj.set_quadro(gestor["id"], "2026-09-S3", "hc", "3")
    api_obj.set_quadro(gestor["id"], "2026-09-13", "hc", "7")

    ciclo = _linha("2026-09-13", visualizacao="mes", mes=None)
    assert ciclo["hc"] == 7
    assert _linha("2026-09-S3")["hc"] == 3, "semana e ciclo nao se misturam"


def test_quadro_invalido_e_recusado(api_obj):
    gestor = _gestor()
    for campo, valor in (("hc", "-1"), ("hc", "2.5"), ("dias_uteis", "40"), ("horas_dia", "0"),
                         ("horas_dia", "25"), ("faltas", "x"), ("nao_existe", "1")):
        assert not api_obj.set_quadro(gestor["id"], "2026-09-S2", campo, valor)["success"], (campo, valor)
    assert api_obj.set_quadro(gestor["id"], "2026-09-S2", "horas_dia", "7,5")["success"]
    assert _linha("2026-09-S2")["horas_dia"] == 7.5


def test_inicio_usa_os_numeros_de_cada_semana(api_obj):
    gestor = _gestor(hc=5)
    indicators_store.salvar_extracao("hugo_boss", "week", {
        "2026-09-14": {"efetividade": 1.0}, "2026-09-21": {"efetividade": 1.0}})
    for campo, valor in (("hc", "3"), ("dias_uteis", "4"), ("faltas", "1")):
        api_obj.set_quadro(gestor["id"], "2026-09-S3", campo, valor)

    presenteismo = _celulas(api_obj, "presenteismo")

    assert presenteismo["2026-09-14"] == limits.formatar(1 - 1 / (3 * 4))
    assert presenteismo["2026-09-21"] == "100,0%", "Week 39 herda o HC 3, sem faltas"


def test_semana_da_virada_usa_os_numeros_de_cada_pedaco(api_obj):
    gestor = _gestor(hc=5)
    indicators_store.salvar_extracao("hugo_boss", "week", {"2026-08-31": {"efetividade": 1.0}})
    api_obj.set_quadro(gestor["id"], "2026-08-S6", "hc", "10")   # 31/08: 1 dia
    api_obj.set_quadro(gestor["id"], "2026-09-S1", "hc", "4")    # 01 a 06/09: 4 dias
    api_obj.set_quadro(gestor["id"], "2026-09-S1", "faltas", "2")

    # horas: 10x1x8 + 4x4x8 = 208 disponiveis; 2x8 = 16 perdidas
    assert _celulas(api_obj, "presenteismo")["2026-08-31"] == limits.formatar(1 - 16 / 208)


def test_dados_antigos_sao_migrados():
    """Versao anterior: faltas em "faltas_lancadas" e HC unico no gestor."""
    gestor = _gestor(hc=6)
    dados = headcount_store.ler()
    dados["gestores"][0]["faltas_lancadas"] = {"2026-09-S2": 2}
    headcount_store._gravar(dados)

    s2 = _linha("2026-09-S2")
    assert (s2["hc"], s2["hc_origem"], s2["faltas"]) == (6, "cadastro", 2)
    assert "faltas_lancadas" not in headcount_store.ler()["gestores"][0]


# ---------------- Inicio so com o mes ----------------

def test_inicio_mostra_so_o_mes_escolhido(api_obj):
    indicators_store.salvar_extracao("hugo_boss", "week", {
        k: {"efetividade": 1.0} for k in ("2026-08-24", "2026-08-31", "2026-09-07", "2026-09-28")})
    indicators_store.salvar_extracao("hugo_boss", "month", {
        "2026-08": {"efetividade": 1.0}, "2026-09": {"efetividade": 1.0}})

    setembro = api_obj.get_indicator_table("hugo_boss", mes="2026-09")
    agosto = api_obj.get_indicator_table("hugo_boss", mes="2026-08")

    # 31/08 a 06/09 tem dias de setembro; 24 a 30/08 nao.
    assert [c["chave"] for c in setembro["colunas"]] == ["2026-08-31", "2026-09-07", "2026-09-28", "2026-09"]
    assert [c["chave"] for c in agosto["colunas"]] == ["2026-08-24", "2026-08-31", "2026-08"]
    assert {"2026-08", "2026-09", "2026-10"} <= {m["id"] for m in setembro["meses"]}
