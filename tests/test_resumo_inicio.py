"""Resumo do topo da Inicio (resumo_inicio.py e Api._resumo_da_inicio) e
o usuario do selo da barra amarela (Api.get_usuario)."""

import pytest

import indicators_store
import resumo_inicio


@pytest.fixture
def api_obj():
    from api import Api

    return Api()


# ---------------- Contas do resumo ----------------

def test_pontos_com_sinal_e_virgula():
    assert resumo_inicio._pontos(0.1157) == "+11,57 p.p."
    assert resumo_inicio._pontos(-0.4201) == "−42,01 p.p."
    assert resumo_inicio._pontos(0) == "+0,00 p.p."


def test_contar_so_o_verde_e_na_meta():
    valores = {
        "efetividade": 1.00,     # verde
        "hora_direta": 0.80,     # vermelho
        "coverage": 1.20,        # azul: acima do teto nao e "na meta"
        "dispersao": None,       # sem numero nao conta
    }
    assert resumo_inicio.contar(valores) == {"na_meta": 1, "com_numero": 3}


def test_resumir_acha_o_melhor_e_o_pior():
    valores = {
        "cubo": None,
        "efetividade": 1.0037,   # verde, folga +10,37
        "hora_direta": 0.9299,   # verde, folga +7,99
        "presenteismo": None,
        "dispersao": 0.60,       # vermelho, -10,00
        "coverage": 0.4999,      # vermelho, -42,01: o pior
    }
    resumo = resumo_inicio.resumir("Setembro", "month", valores)

    assert (resumo["coluna"], resumo["periodo"]) == ("Setembro", "month")
    assert (resumo["total"], resumo["com_numero"], resumo["na_meta"]) == (6, 4, 2)
    assert resumo["melhor"] == {"indicador": "efetividade", "nome": "Efetividade", "texto": "100,37%", "folga": "+10,37 p.p."}
    assert resumo["pior"]["indicador"] == "coverage"
    assert resumo["pior"]["folga"] == "−42,01 p.p."
    assert resumo["anterior"] is None


def test_tudo_na_meta_nao_tem_pior_e_nada_na_meta_nao_tem_melhor():
    assert resumo_inicio.resumir("W1", "week", {"efetividade": 1.0, "hora_direta": 0.9})["pior"] is None
    assert resumo_inicio.resumir("W1", "week", {"efetividade": 0.5})["melhor"] is None


def test_total_conta_so_os_indicadores_da_coluna():
    # O pico nao tem coverage: a coluna diz "de 5", nao "de 6".
    valores = {i: 1.0 for i in ("cubo", "efetividade", "hora_direta", "presenteismo", "dispersao")}
    assert resumo_inicio.resumir("Pico", "peak", valores)["total"] == 5


def test_comparacao_com_o_periodo_anterior():
    anterior = {"rotulo": "Agosto/2026", "na_meta": 3, "com_numero": 4}
    resumo = resumo_inicio.resumir("Setembro", "month", {"efetividade": 1.0, "dispersao": 0.5}, anterior)
    assert resumo["anterior"] == {"rotulo": "Agosto/2026", "na_meta": 3, "com_numero": 4, "diferenca": -2}

    # Periodo anterior sem nenhum numero nao entra na comparacao.
    vazio = {"rotulo": "Agosto/2026", "na_meta": 0, "com_numero": 0}
    assert resumo_inicio.resumir("Setembro", "month", {"efetividade": 1.0}, vazio)["anterior"] is None


# ---------------- Na tabela da Inicio ----------------

def test_inicio_traz_o_resumo_do_mes_e_compara_com_o_mes_anterior(api_obj):
    indicators_store.salvar_extracao("hugo_boss", "week", {
        "2026-09-07": {"efetividade": 0.95, "hora_direta": 0.80}})
    indicators_store.salvar_extracao("hugo_boss", "month", {
        "2026-08": {"efetividade": 0.95, "hora_direta": 0.90},
        "2026-09": {"efetividade": 1.00, "hora_direta": 0.80}})

    resumo = api_obj.get_indicator_table("hugo_boss", mes="2026-09")["resumo"]

    # A referencia e o mes, nao a ultima semana.
    assert resumo["periodo"] == "month"
    assert (resumo["na_meta"], resumo["com_numero"]) == (1, 2)
    assert resumo["melhor"]["indicador"] == "efetividade"
    assert resumo["pior"]["indicador"] == "hora_direta"
    assert resumo["anterior"]["rotulo"] == "Agosto/2026"
    assert (resumo["anterior"]["na_meta"], resumo["anterior"]["diferenca"]) == (2, -1)


def test_sem_o_mes_o_resumo_e_da_ultima_semana(api_obj):
    indicators_store.salvar_extracao("hugo_boss", "week", {
        "2026-09-07": {"efetividade": 0.80},
        "2026-09-14": {"efetividade": 1.00}})

    resumo = api_obj.get_indicator_table("hugo_boss", mes="2026-09")["resumo"]

    assert resumo["periodo"] == "week"
    assert resumo["na_meta"] == 1
    # A semana anterior entra na comparacao.
    assert (resumo["anterior"]["na_meta"], resumo["anterior"]["diferenca"]) == (0, 1)


# ---------------- Usuario do selo ----------------

def test_get_usuario_devolve_so_o_nome(api_obj):
    assert api_obj.get_usuario() == {"usuario": None}

    api_obj.login("usuario.teste", "senha-secreta")
    resposta = api_obj.get_usuario()
    assert resposta == {"usuario": "usuario.teste"}
    assert "senha-secreta" not in repr(resposta)

    api_obj.logout()
    assert api_obj.get_usuario() == {"usuario": None}
