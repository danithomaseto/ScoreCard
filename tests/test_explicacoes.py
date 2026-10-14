"""A conta de cada indicador para a dica da aba Inicio (explicacoes.py)."""

import explicacoes


def test_efetividade_hora_direta_e_dispersao_com_as_somas_do_summary():
    entrada = {"efetividade": 1.128785, "soma_goal": 302.0, "soma_measured_direct": 267.55,
               "hora_direta": 0.9606, "soma_signon_direct": 0.0, "soma_insert_direct": 0.0,
               "soma_total": 290.0, "soma_pd_brk": 11.5, "dispersao": 0.666667, "dentro": 6, "fora": 3}
    assert explicacoes.explicar("efetividade", entrada)["conta"] == "302,0 h ÷ 267,6 h = 112,88%"
    assert explicacoes.explicar("hora_direta", entrada)["conta"] == "267,6 h diretas ÷ 278,5 h = 96,06%"
    assert explicacoes.explicar("dispersao", entrada)["conta"] == "6 de 9 pessoas = 66,67%"


def test_presenteismo_cubo_e_coverage():
    entrada = {"presenteismo": 0.983333, "_presenteismo_partes": {"horas_perdidas": 8, "horas_disponiveis": 480},
               "efetividade": 1.0, "hora_direta": 0.9, "cubo": 0.885,
               "coverage": 0.647748, "_coverage_partes": {"lms": 283.4, "diretas_sem_meta": 0, "metrics": 437.5,
                                                          "recebida": 0, "cedida": 0}}
    assert explicacoes.explicar("presenteismo", entrada)["conta"] == "1 − 8,0 h perdidas ÷ 480,0 h disponíveis = 98,33%"
    assert explicacoes.explicar("cubo", entrada)["conta"] == "100,00% × 90,00% × 98,33% = 88,50%"
    assert explicacoes.explicar("coverage", entrada)["conta"] == "(283,4 h − 0,0 h) ÷ 437,5 h = 64,77%"
    entrada["_coverage_partes"].update(recebida=10, cedida=2.5)
    assert "(437,5 h + 10,0 h recebida − 2,5 h cedida)" in explicacoes.explicar("coverage", entrada)["conta"]


def test_pico_usa_os_dias_de_pico():
    entrada = {"hora_direta": 0.9657, "_dias_pico": [{"horas_diretas": 300, "horas": 310},
                                                     {"horas_diretas": 282.8, "horas": 293.5}]}
    dica = explicacoes.explicar("hora_direta", entrada, "peak")
    assert dica["formula"].startswith("Horas diretas")
    assert dica["conta"] == "582,8 h ÷ 603,5 h em 2 dias = 96,57%"


def test_sem_numero_nao_ha_dica_e_sem_parcelas_fica_so_a_formula():
    assert explicacoes.explicar("efetividade", {}) is None
    dica = explicacoes.explicar("efetividade", {"efetividade": 0.95})
    assert dica == {"formula": "Goal ÷ Measured Direct", "conta": ""}


def test_horas_no_padrao_brasileiro():
    assert explicacoes.horas(1234.56) == "1.234,6 h"
