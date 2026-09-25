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
