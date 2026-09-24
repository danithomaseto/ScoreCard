"""Testes da automacao (automation/generic.py) contra as paginas de mock."""

import os

from automation import generic


def run_mock(operations, sharepoint_dir, key="mock", label="Mock Co",
             folder="MockCo", page="login.html", **kwargs):
    operations(key, label, folder, page)
    kwargs.setdefault("date_range", {"from_date": "2026-09-01", "to_date": "2026-09-07"})
    return generic.run(
        key,
        base_dir=str(sharepoint_dir),
        headless=True,
        username="usuario",
        password="senha",
        **kwargs,
    )


def test_extracao_salva_arquivo_na_pasta_da_operacao(operations, sharepoint_dir):
    result = run_mock(operations, sharepoint_dir)

    assert result["success"], result.get("message")
    assert os.path.isfile(result["file_path"])
    assert result["period_label"] == "01/09/2026 - 07/09/2026"


def test_group_by_escolhido_na_tela_e_aplicado(operations, sharepoint_dir):
    result = run_mock(operations, sharepoint_dir, group_by="Work Team")

    assert result["success"], result.get("message")
    assert result["group_by"] == "Work Team"


def test_week_e_month_vao_para_subpastas_diferentes(operations, sharepoint_dir):
    semanal = run_mock(operations, sharepoint_dir, key="mock_w", folder="MockCo", period="week")
    mensal = run_mock(operations, sharepoint_dir, key="mock_m", folder="MockCo", period="month")

    assert semanal["period_type"] == "Week"
    assert mensal["period_type"] == "Month"
    assert os.path.basename(os.path.dirname(semanal["file_path"])) == "Week"
    assert os.path.basename(os.path.dirname(mensal["file_path"])) == "Month"


def test_nova_extracao_apaga_a_anterior_da_mesma_pasta(operations, sharepoint_dir):
    primeira = run_mock(operations, sharepoint_dir)
    segunda = run_mock(operations, sharepoint_dir)

    pasta = os.path.dirname(segunda["file_path"])
    assert sorted(os.listdir(pasta)) == [os.path.basename(segunda["file_path"])]
    assert not os.path.exists(primeira["file_path"])


def test_week_nao_apaga_o_arquivo_de_month(operations, sharepoint_dir):
    mensal = run_mock(operations, sharepoint_dir, key="mock_m", folder="MockCo", period="month")
    run_mock(operations, sharepoint_dir, key="mock_m", folder="MockCo", period="week")
    run_mock(operations, sharepoint_dir, key="mock_m", folder="MockCo", period="week")

    assert os.path.isfile(mensal["file_path"])


def test_falha_devolve_mensagem_e_screenshot(operations, sharepoint_dir):
    result = run_mock(operations, sharepoint_dir, key="mock_fail",
                      folder="MockFalha", page="nao-existe.html")

    assert result["success"] is False
    assert result["message"]
    # O screenshot e o que permite diagnosticar a falha depois.
    assert result.get("screenshot")


def test_progresso_informa_todas_as_etapas(operations, sharepoint_dir):
    passos = []
    run_mock(operations, sharepoint_dir, on_progress=passos.append)

    texto = " | ".join(passos).lower()
    for esperado in [
        "abrindo o navegador",
        "fazendo login",
        "abrindo menu",
        "localizando o iframe",
        "abrindo o relatorio",
        "periodo especifico",
        "group by 1 (week)",
        "segundo nivel",
        "group by 2",
        "exportando e baixando",
        "concluido",
    ]:
        assert esperado in texto, f"etapa ausente no progresso: {esperado}"


def test_sem_datas_usa_o_date_range_do_proprio_relatorio(operations, sharepoint_dir):
    """Sem intervalo digitado, quem define o periodo e o relatorio."""
    semanal = run_mock(operations, sharepoint_dir, key="mock_w", date_range=None, period="week")
    mensal = run_mock(operations, sharepoint_dir, key="mock_m", date_range=None, period="month")

    assert semanal["success"], semanal.get("message")
    assert semanal["period_label"] == "Last Week"
    assert semanal["origem"] == "last_week"

    assert mensal["success"], mensal.get("message")
    assert mensal["period_label"] == "Last Month"
    assert mensal["origem"] == "last_month"


def test_mes_guarda_a_chave_do_periodo_e_a_semana_nao(operations, sharepoint_dir):
    """O export mensal nao traz data nenhuma, entao o mes vem de quem
    pediu a extracao; na semana a data vem pronta no arquivo."""
    mensal = run_mock(operations, sharepoint_dir, key="mock_m", period="month",
                      date_range={"from_date": "2026-09-01", "to_date": "2026-09-19"})
    semanal = run_mock(operations, sharepoint_dir, key="mock_w", period="week")

    assert mensal["month_key"] == "2026-09"
    assert semanal["month_key"] is None


def test_mes_sem_datas_usa_o_mes_anterior_como_chave():
    from datetime import date

    from automation.generic import _month_key

    assert _month_key(None, hoje=date(2026, 9, 24)) == "2026-08"
    assert _month_key(None, hoje=date(2026, 1, 5)) == "2025-12"
    assert _month_key({"from_date": "2026-09-01", "to_date": "2026-09-19"}) == "2026-09"
