"""Testes da camada exposta para a interface (api.py)."""

import os

import pytest


@pytest.fixture
def api(sharepoint_dir, isolated_history, monkeypatch):
    """Api pronta pra uso: logada, com a pasta do SharePoint apontando
    para um diretorio temporario e sem janela (os avisos pro JS ficam
    guardados em api.eventos)."""
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))

    instance = Api()
    instance.login("usuario", "senha")
    instance.eventos = []
    instance._emit_js = lambda fn, payload: instance.eventos.append((fn, payload))
    return instance


def eventos_finais(api):
    return [p for fn, p in api.eventos if p.get("status") != "running"]


DATAS = {"from_date": "2026-09-01", "to_date": "2026-09-07"}


def test_extracao_unica_grava_no_historico(api, operations, isolated_history):
    operations("mock", "Mock Co", "MockCo")

    result = api.run_extraction("mock", date_range=DATAS, period="week")

    assert result["success"], result.get("message")
    historico = isolated_history.get_history()
    assert len(historico) == 1
    assert historico[0]["operation"] == "Mock Co"
    assert historico[0]["status"] == "success"
    assert historico[0]["period_type"] == "Week"


def test_multipla_roda_todas_em_sequencia(api, operations, isolated_history):
    operations("mock_a", "Mock A", "MockA")
    operations("mock_b", "Mock B", "MockB")

    result = api.run_multi_extraction(["mock_a", "mock_b"], date_range=DATAS, period="week")

    assert result["success"], result.get("message")
    assert "2 de 2" in result["message"]
    assert len(isolated_history.get_history()) == 2
    assert [p["status"] for p in eventos_finais(api)] == ["success", "success"]


def test_falha_no_meio_nao_interrompe_a_fila(api, operations, isolated_history, sharepoint_dir):
    operations("mock_a", "Mock A", "MockA")
    operations("mock_fail", "Mock Falha", "MockFalha", page="nao-existe.html")
    operations("mock_b", "Mock B", "MockB")

    result = api.run_multi_extraction(
        ["mock_a", "mock_fail", "mock_b"], date_range=DATAS, period="week"
    )

    assert result["success"] is False
    assert "2 de 3" in result["message"]
    # A operacao depois da falha precisa ter rodado.
    assert os.path.isdir(os.path.join(str(sharepoint_dir), "MockB", "Week"))
    assert [p["status"] for p in eventos_finais(api)] == ["success", "error", "success"]
    # Inclusive a que falhou entra no historico.
    assert len(isolated_history.get_history()) == 3


def test_multipla_sem_operacao_selecionada_avisa(api):
    result = api.run_multi_extraction([], date_range=DATAS)

    assert result["success"] is False
    assert "pelo menos uma" in result["message"].lower()


def test_operacao_invalida_e_rejeitada(api):
    result = api.run_extraction("nao_existe", date_range=DATAS)

    assert result["success"] is False
    assert "invalida" in result["message"].lower()


def test_group_by_fora_da_lista_e_rejeitado(api, operations):
    operations("mock", "Mock Co", "MockCo")

    result = api.run_extraction("mock", date_range=DATAS, group_by="Coluna Inventada")

    assert result["success"] is False
    assert "group by" in result["message"].lower()


def test_login_e_obrigatorio(operations, sharepoint_dir, monkeypatch):
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    operations("mock", "Mock Co", "MockCo")

    result = Api().run_extraction("mock", date_range=DATAS)

    assert result["success"] is False
    assert "login" in result["message"].lower()


def test_credenciais_nunca_sao_persistidas(api, operations, isolated_history):
    """A senha so pode viver em memoria durante a sessao."""
    operations("mock", "Mock Co", "MockCo")
    api.run_extraction("mock", date_range=DATAS)

    import settings_store

    assert "senha" not in str(settings_store.get_settings()).lower()
    assert "senha" not in str(isolated_history.get_history()).lower()
