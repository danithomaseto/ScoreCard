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


def _celulas(api_obj, indicador, operacao="hugo_boss"):
    tabela = api_obj.get_indicator_table(operacao)
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


def test_todas_as_semanas_soma_e_nao_deixa_digitar(api_obj):
    gestor = _gestor()
    api_obj.set_faltas(gestor["id"], "2026-09-S2", "1")
    api_obj.set_faltas(gestor["id"], "2026-09-S3", "2")

    linha = headcount.montar("hugo_boss", "semanal", "2026-09", "todas", hoje=HOJE)["linhas"][0]

    assert linha["faltas"] == 3
    assert linha["faltas_editavel"] is False
    assert not api_obj.set_faltas(gestor["id"], "todas", "1")["success"]


def test_so_numero_inteiro_nao_negativo(api_obj):
    gestor = _gestor()
    for invalido in ("-1", "1.5", "abc"):
        resposta = api_obj.set_faltas(gestor["id"], "2026-09-S2", invalido)
        assert not resposta["success"], invalido

    api_obj.set_faltas(gestor["id"], "2026-09-S2", "2")
    api_obj.set_faltas(gestor["id"], "2026-09-S2", "")
    assert headcount_store.listar_gestores()[0]["faltas_lancadas"] == {}, "vazio apaga"


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
