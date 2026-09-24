"""Testes do calculo dos indicadores.

Os numeros de referencia vem das duas planilhas montadas a mao no Excel
(`Logica_Score_Card`, semanal, e a versao do mes). As fixtures sao
copias delas com o identificador das pessoas trocado por um codigo
generico — os valores sao os mesmos. Se o app nao reproduzir esses
numeros, ele esta errado, por mais razoavel que o resultado pareca.
"""

import os

import pytest

from indicators import limits, reader, weekly

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def pct(valor):
    """Percentual com uma casa, pra comparar com o que se le na
    planilha sem brigar com casa decimal."""
    return None if valor is None else round(valor * 100, 1)


@pytest.fixture
def semanal():
    return reader.ler(os.path.join(FIXTURES, "summary_3semanas.xlsx"))


@pytest.fixture
def mensal():
    return reader.ler(os.path.join(FIXTURES, "summary_mes.xlsx"))


@pytest.fixture
def real():
    """O formato que o Summary entrega de verdade: .xls antigo."""
    return reader.ler(os.path.join(FIXTURES, "summary_real.xls"))


# ---------------- Leitura ----------------

def test_reconhece_o_export_semanal(semanal):
    assert semanal["tem_semana"] is True
    assert len(semanal["linhas"]) == 33
    primeira = semanal["linhas"][0]
    assert primeira["semana"] == "2026-08-30"
    assert primeira["goal"] == 0.18
    assert primeira["measured_direct"] == 0.24


def test_reconhece_o_export_mensal(mensal):
    """Sem Medium Level Group todas as colunas andam uma posicao pra
    esquerda: e o caso que quebraria um leitor que fosse por letra."""
    assert mensal["tem_semana"] is False
    assert len(mensal["linhas"]) == 16
    primeira = mensal["linhas"][0]
    assert primeira.get("semana") is None
    assert primeira["goal"] == 108.09
    assert primeira["measured_direct"] == 100.78
    assert primeira["pd_brk"] == 2.17
    assert primeira["total"] == 111.26


def test_le_o_xls_antigo_que_o_summary_entrega(real):
    """O relatorio vem em BIFF (.xls), nao em .xlsx: o openpyxl sozinho
    recusava o arquivo e o calculo morria calado."""
    assert real["tem_semana"] is True
    assert len(real["linhas"]) == 46

    primeira = real["linhas"][0]
    assert primeira["semana"] == "2026-08-31"
    assert primeira["goal"] == 25.34
    assert primeira["measured_direct"] == 27.86
    assert primeira["pd_brk"] == 0.67


def test_formato_vem_dos_bytes_e_nao_da_extensao(tmp_path):
    """Extensao e palpite; assinatura e fato. Um .xlsx renomeado para
    .xls tem que continuar sendo lido."""
    import shutil

    disfarcado = tmp_path / "parece_xls.xls"
    shutil.copy(os.path.join(FIXTURES, "summary_mes.xlsx"), disfarcado)

    assert len(reader.ler(str(disfarcado))["linhas"]) == 16


def test_arquivo_que_nao_e_planilha_e_recusado_com_clareza(tmp_path):
    caminho = tmp_path / "relatorio.xls"
    caminho.write_text("<html><body>erro do servidor</body></html>", encoding="utf-8")

    with pytest.raises(ValueError, match="planilha"):
        reader.ler(str(caminho))


def test_semanas_do_arquivo_real_saem_agrupadas(real):
    semanas = weekly.por_semana(real["linhas"], nivel_detalhe="User ID")

    assert list(semanas) == ["2026-08-31", "2026-09-07", "2026-09-14"]
    assert [s["linhas"] for s in semanas.values()] == [15, 15, 16]
    assert pct(semanas["2026-08-31"]["efetividade"]) == 82.0


def test_arquivo_sem_as_colunas_do_summary_e_recusado(tmp_path):
    from openpyxl import Workbook

    caminho = tmp_path / "outra_coisa.xlsx"
    livro = Workbook()
    livro.active.append(["Nome", "Telefone"])
    livro.active.append(["Fulano", "1234"])
    livro.save(caminho)

    with pytest.raises(ValueError, match="Summary"):
        reader.ler(str(caminho))


def test_linha_de_total_no_fim_e_descartada(tmp_path):
    """Se uma linha de fechamento entrar na soma, todo indicador dobra."""
    from openpyxl import Workbook

    caminho = tmp_path / "com_total.xlsx"
    livro = Workbook()
    aba = livro.active
    aba.append(["Detail Level\nGroup", "Var", "Goal", "Measured\nDirect",
                "Unmeasured\nSignon Direct", "Unmeasured\nInsert Direct", "PD Brk", "Total"])
    aba.append(["P01", 0, 10.0, 10.0, 0, 0, 0, 12.0])
    aba.append(["Total", 0, 10.0, 10.0, 0, 0, 0, 12.0])
    livro.save(caminho)

    lido = reader.ler(str(caminho))
    assert len(lido["linhas"]) == 1


# ---------------- Classificacao ----------------

def test_classificacao_dentro_fora_e_ignorada():
    assert weekly.classificar({"goal": 30.0, "measured_direct": 30.0, "var": 8}) == "dentro"
    assert weekly.classificar({"goal": 30.0, "measured_direct": 30.0, "var": -10}) == "dentro"
    assert weekly.classificar({"goal": 30.0, "measured_direct": 30.0, "var": 11}) == "fora"
    assert weekly.classificar({"goal": 30.0, "measured_direct": 30.0, "var": -32}) == "fora"
    # Sem meta ou sem tempo medido, a linha sai so da dispersao.
    assert weekly.classificar({"goal": 0, "measured_direct": 30.0, "var": 5}) is None
    assert weekly.classificar({"goal": 30.0, "measured_direct": 0, "var": 5}) is None


# ---------------- Semana ----------------

def test_semana_36_reproduz_a_planilha(semanal):
    semanas = weekly.por_semana(semanal["linhas"], nivel_detalhe="User ID")
    s36 = semanas["2026-08-30"]

    assert s36["soma_goal"] == 245.99
    assert s36["soma_measured_direct"] == 255.23
    assert pct(s36["efetividade"]) == 96.4
    assert pct(s36["hora_direta"]) == 85.4
    assert (s36["dentro"], s36["fora"]) == (9, 2)
    assert pct(s36["dispersao"]) == 81.8


def test_as_tres_semanas_do_arquivo_saem_de_uma_vez(semanal):
    """Uma extracao pode trazer varias semanas; todas viram resultado."""
    semanas = weekly.por_semana(semanal["linhas"], nivel_detalhe="User ID")

    assert list(semanas) == ["2026-08-30", "2026-09-06", "2026-09-13"]
    assert [pct(s["efetividade"]) for s in semanas.values()] == [96.4, 112.9, 101.9]
    assert [pct(s["hora_direta"]) for s in semanas.values()] == [85.4, 96.1, 96.4]
    assert [pct(s["dispersao"]) for s in semanas.values()] == [81.8, 66.7, 70.0]


def test_indicadores_sem_calculo_ficam_vazios_e_nao_zerados(semanal):
    s36 = weekly.por_semana(semanal["linhas"])["2026-08-30"]

    assert s36["presenteismo"] is None
    assert s36["coverage"] is None
    assert s36["cubo"] is None, "o cubo depende do presenteismo"


# ---------------- Mes ----------------

def test_mes_consolidado_reproduz_a_planilha(mensal):
    """O mensal ja vem somado por pessoa: um grupo so, mesmas formulas."""
    mes = weekly.totais(mensal["linhas"], nivel_detalhe="User ID")

    assert mes["soma_goal"] == 1407.65
    assert mes["soma_measured_direct"] == 1402.52
    assert pct(mes["efetividade"]) == 100.4
    assert pct(mes["hora_direta"]) == 93.0
    assert (mes["dentro"], mes["fora"]) == (9, 6)
    assert pct(mes["dispersao"]) == 60.0


def test_mes_nao_vira_grupo_por_semana(mensal):
    """Sem coluna de data nao ha como quebrar por semana."""
    assert weekly.por_semana(mensal["linhas"]) == {}


# ---------------- Regras ----------------

def test_dispersao_so_vale_com_o_detalhe_em_user_id(semanal):
    """Com outro agrupamento a contagem seria de turnos ou areas."""
    por_turno = weekly.por_semana(semanal["linhas"], nivel_detalhe="Shift")["2026-08-30"]

    assert por_turno["dispersao"] is None
    assert por_turno["dentro"] is None and por_turno["fora"] is None
    # As somas de horas nao dependem do agrupamento e continuam valendo.
    assert pct(por_turno["efetividade"]) == 96.4
    assert pct(por_turno["hora_direta"]) == 85.4


def test_cubo_e_o_produto_dos_tres():
    assert weekly.calcular_cubo(0.9638, 0.8537, 0.98) == pytest.approx(0.80634, abs=1e-5)
    assert weekly.calcular_cubo(0.9638, 0.8537, None) is None


def test_faixas_de_cor():
    assert limits.cor("efetividade", 0.964) == "verde"
    assert limits.cor("efetividade", 1.129) == "azul"
    assert limits.cor("efetividade", 0.89) == "vermelho"
    # Exatamente na meta e verde: "70% ou mais".
    assert limits.cor("dispersao", 0.70) == "verde"
    assert limits.cor("dispersao", 0.667) == "vermelho"
    assert limits.cor("hora_direta", 0.85) == "verde"
    assert limits.cor("cubo", 1.0643) == "azul"
    assert limits.cor("coverage", 0.91) == "vermelho"
    # Sem numero nao tem cor — nao e vermelho.
    assert limits.cor("presenteismo", None) is None


def test_formatacao_do_percentual():
    assert limits.formatar(0.9638) == "96,4%"
    assert limits.formatar(1.129) == "112,9%"
    assert limits.formatar(None) == "", "sem numero vira vazio, nunca zero"
