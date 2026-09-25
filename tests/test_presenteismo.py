"""Testes da leitura das faltas e do calculo do presenteismo."""

import datetime
import os

import pytest

from indicators import faltas, presenteismo

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
HOJE = datetime.date(2026, 9, 25)


# ---------------- Leitura das faltas ----------------

@pytest.fixture
def arquivo():
    return faltas.ler(os.path.join(FIXTURES, "faltas_abs.xlsx"))


def test_le_o_arquivo_de_ausencias(arquivo):
    assert arquivo["resumo"]["linhas"] == 18
    assert arquivo["resumo"]["consideradas"] == 3
    assert arquivo["resumo"]["dias"] == 3
    assert arquivo["resumo"]["gestores"] == 1


def test_ferias_nao_e_falta(arquivo):
    assert arquivo["resumo"]["motivo"] == 5
    assert all(f["motivo"] != "FERIAS" for f in arquivo["faltas"])


def test_temporario_fica_de_fora(arquivo):
    assert arquivo["resumo"]["contrato"] == 9
    assert all(f["contrato"] == "EFETIVO" for f in arquivo["faltas"])


def test_so_as_funcoes_que_compoem_o_quadro(arquivo):
    assert arquivo["resumo"]["funcao"] == 1
    assert all("LOGISTICO" in f["funcao"] for f in arquivo["faltas"])


@pytest.mark.parametrize("funcao, conta", [
    ("AUXILIAR LOGISTICO I", True),
    ("AUXILIAR LOGISTICO II", True),
    ("Auxiliar Log I", True),
    ("OPERADOR DE EMPILHADEIRA", True),
    ("Operador de Ponte Rolante", True),
    ("ASSISTENTE DE LOGISTICA", False),
    ("INSPETOR DE PRODUTO E PROCESSOS", False),
    ("ANALISTA", False),
    ("", True),
])
def test_regra_da_funcao_e_por_padrao_e_nao_lista_fechada(funcao, conta):
    """Uma funcao escrita de outro jeito nao pode sumir da conta em
    silencio, por isso a regra e por padrao de texto."""
    assert faltas._funcao_conta(funcao) is conta


def test_cada_linha_e_um_dia(arquivo):
    assert all(f["dias"] == 1 for f in arquivo["faltas"])


def test_arquivo_sem_as_colunas_esperadas_e_recusado(tmp_path):
    from openpyxl import Workbook

    caminho = tmp_path / "outra_coisa.xlsx"
    livro = Workbook()
    livro.active.append(["Nome", "Telefone"])
    livro.save(caminho)

    with pytest.raises(ValueError, match="cabecalho"):
        faltas.ler(str(caminho))


# ---------------- Semanas do mes ----------------

def test_semanas_de_setembro_2026():
    """O mes comeca numa terca e acaba numa quarta, entao a primeira e a
    ultima semana tem menos dias uteis."""
    semanas = presenteismo.semanas_do_mes(2026, 9, hoje=HOJE)

    assert [s["dias_uteis"] for s in semanas] == [4, 5, 5, 5, 3]
    assert semanas[0]["inicio"] == "2026-09-01" and semanas[0]["fim"] == "2026-09-06"
    assert semanas[1]["inicio"] == "2026-09-07" and semanas[1]["fim"] == "2026-09-13"
    assert semanas[4]["inicio"] == "2026-09-28" and semanas[4]["fim"] == "2026-09-30"


def test_uma_falta_cai_na_semana_certa():
    assert presenteismo.semana_de("2026-09-08", hoje=HOJE) == "2026-09-S2"
    assert presenteismo.semana_de("2026-09-01", hoje=HOJE) == "2026-09-S1"
    assert presenteismo.semana_de("2026-09-30", hoje=HOJE) == "2026-09-S5"


# ---------------- Ciclos da folha ponto ----------------

def test_ciclo_vai_do_dia_13_ao_dia_12():
    ciclos = {c["id"]: c for c in presenteismo.ciclos_folha(hoje=HOJE)}
    atual = ciclos["2026-09-13"]

    assert atual["rotulo"] == "13/09/2026 → 12/10/2026"
    assert atual["status"] == "Em aberto"


def test_ciclo_em_aberto_conta_so_os_dias_ja_decorridos():
    """Senao o presenteismo de um ciclo que mal comecou apareceria
    despencando: as faltas ja aconteceram e os dias ainda nao."""
    ciclos = {c["id"]: c for c in presenteismo.ciclos_folha(hoje=HOJE)}

    # De 13/09 a 25/09 ha 10 dias uteis; o ciclo fechado anterior tem 22.
    assert ciclos["2026-09-13"]["dias_uteis"] == 10
    assert ciclos["2026-08-13"]["dias_uteis"] == 22
    assert ciclos["2026-08-13"]["status"] == "Fechado"


def test_proximo_ciclo_ja_aparece_para_receber_lancamentos():
    ciclos = presenteismo.ciclos_folha(hoje=HOJE)
    proximo = ciclos[0]

    assert proximo["id"] == "2026-10-13"
    assert proximo["status"] == "Aberto em 13/10"
    assert proximo["dias_uteis"] == 0


def test_uma_falta_cai_no_ciclo_certo():
    assert presenteismo.ciclo_de("2026-09-14") == "2026-09-13"
    assert presenteismo.ciclo_de("2026-09-12") == "2026-08-13", "dia 12 ainda e do ciclo anterior"
    assert presenteismo.ciclo_de("2026-09-13") == "2026-09-13"


def test_a_mesma_falta_alimenta_a_semana_e_o_ciclo():
    """Um arquivo so alimenta os dois calendarios de uma vez."""
    data = "2026-09-08"
    assert presenteismo.semana_de(data, hoje=HOJE) == "2026-09-S2"
    assert presenteismo.ciclo_de(data) == "2026-08-13"


# ---------------- A formula ----------------

def test_formula_do_presenteismo():
    # 10 pessoas x 20 dias x 8h = 1600h; 4 faltas x 8h = 32h perdidas.
    assert presenteismo.calcular(10, 20, 8, 4) == pytest.approx(0.98, abs=1e-6)


def test_sem_faltas_o_presenteismo_e_cheio():
    assert presenteismo.calcular(10, 20, 8, 0) == 1.0


def test_sem_quadro_nao_ha_o_que_calcular():
    """Zero pessoas ou zero dias nao viram 100%: viram "nao da pra
    calcular"."""
    assert presenteismo.calcular(0, 20, 8, 0) is None
    assert presenteismo.calcular(10, 0, 8, 0) is None


def test_memoria_de_calculo():
    memoria = presenteismo.memoria(10, 20, 8, 4)

    assert memoria["horas_disponiveis"] == 1600.0
    assert memoria["horas_perdidas"] == 32.0
    assert memoria["horas_efetivas"] == 1568.0
    assert memoria["presenteismo"] == pytest.approx(0.98, abs=1e-6)


def test_contagem_de_faltas_por_gestor_e_periodo():
    lancamentos = [
        {"gestor": "A", "data": "2026-09-08", "dias": 1},
        {"gestor": "A", "data": "2026-09-10", "dias": 1},
        {"gestor": "A", "data": "2026-09-14", "dias": 1},
        {"gestor": "B", "data": "2026-09-08", "dias": 1},
    ]

    assert presenteismo.contar_faltas(lancamentos, gestor="A") == 3
    assert presenteismo.contar_faltas(
        lancamentos, gestor="A", inicio="2026-09-07", fim="2026-09-13") == 2
    assert presenteismo.contar_faltas(lancamentos, inicio="2026-09-14") == 1


# ---------------- Da tela ate o indicador ----------------

@pytest.fixture
def app(tmp_path, monkeypatch):
    """Api com os stores numa pasta temporaria."""
    import api as api_module
    import headcount_store
    import indicators_store

    monkeypatch.setattr(headcount_store, "_caminho", lambda: str(tmp_path / "headcount.json"))
    monkeypatch.setattr(indicators_store, "_store_path", lambda: str(tmp_path / "indicators.json"))
    return api_module.Api(), headcount_store, indicators_store


def _preparar(app, hc=25):
    _, headcount_store, _ = app
    gestor = headcount_store.adicionar_gestor("G05", "hugo_boss")
    headcount_store.atualizar_gestor(gestor["id"], {"hc": hc})
    with open(os.path.join(FIXTURES, "faltas_abs.xlsx"), "rb") as fh:
        import base64
        conteudo = base64.b64encode(fh.read()).decode()
    app[0].import_faltas("faltas_abs.xlsx", conteudo)
    return gestor


def test_a_tela_junta_quadro_digitado_e_faltas_da_planilha(app):
    api_obj = app[0]
    _preparar(app)

    tela = api_obj.get_headcount("hugo_boss", "semanal", "2026-09", "todas")
    linha = tela["linhas"][0]

    assert linha["gestor"] == "G05"
    assert linha["hc"] == 25, "digitado na tela"
    assert linha["faltas"] == 3, "veio da planilha"
    assert linha["presenteismo"] == pytest.approx(1 - 24 / (25 * 22 * 8), abs=1e-6)


def test_faltas_sao_roteadas_para_a_semana_pela_data(app):
    api_obj = app[0]
    _preparar(app)

    # As faltas sao 08, 10 e 14 de setembro: duas na S2, uma na S3.
    s2 = api_obj.get_headcount("hugo_boss", "semanal", "2026-09", "2026-09-S2")
    s3 = api_obj.get_headcount("hugo_boss", "semanal", "2026-09", "2026-09-S3")
    s1 = api_obj.get_headcount("hugo_boss", "semanal", "2026-09", "2026-09-S1")

    assert s2["cards"]["faltas"] == 2
    assert s3["cards"]["faltas"] == 1
    assert s1["cards"]["faltas"] == 0


def test_aplicar_leva_o_presenteismo_para_o_indicador(app):
    """E o que destrava o CUBO na aba Inicio."""
    api_obj, _, indicators_store = app
    _preparar(app)

    resposta = api_obj.aplicar_presenteismo("hugo_boss", "semanal", "2026-09", "2026-09-S2")

    assert resposta["success"], resposta.get("message")
    semanas = indicators_store.get_indicators("hugo_boss")["week"]
    # A chave do indicador e a segunda-feira da semana, como o Summary
    # identifica a semana.
    assert "2026-09-07" in semanas
    assert semanas["2026-09-07"]["presenteismo"] == resposta["presenteismo"]


def test_o_cubo_sai_quando_o_presenteismo_chega(app):
    api_obj, _, indicators_store = app
    _preparar(app)
    indicators_store.salvar_extracao("hugo_boss", "week", {
        "2026-09-07": {"efetividade": 0.9638, "hora_direta": 0.8537},
    })

    assert indicators_store.get_indicators("hugo_boss")["week"]["2026-09-07"]["cubo"] is None

    api_obj.aplicar_presenteismo("hugo_boss", "semanal", "2026-09", "2026-09-S2")

    entrada = indicators_store.get_indicators("hugo_boss")["week"]["2026-09-07"]
    assert entrada["cubo"] == pytest.approx(
        0.9638 * 0.8537 * entrada["presenteismo"], abs=1e-6)


def test_aplicar_sem_escolher_operacao_avisa(app):
    api_obj = app[0]
    _preparar(app)

    resposta = api_obj.aplicar_presenteismo("todas", "semanal", "2026-09", "todas")

    assert resposta["success"] is False
    assert "operacao" in resposta["message"].lower()


def test_funcao_cadastrada_passa_a_contar(app):
    """A funcao nova vale ja na releitura, sem precisar reenviar o
    arquivo."""
    api_obj, headcount_store, _ = app
    _preparar(app)

    antes = api_obj.get_headcount("hugo_boss", "semanal", "2026-09", "todas")
    assert antes["arquivo"]["resumo"]["consideradas"] == 3

    resposta = api_obj.add_funcao("ASSISTENTE DE LOGISTICA")

    assert resposta["success"]
    assert resposta["resumo"]["consideradas"] == 4, "a linha de assistente passa a entrar"
