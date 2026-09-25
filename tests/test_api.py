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


def test_parar_apos_a_atual_conclui_a_corrente_e_cancela_o_resto(api, operations, isolated_history):
    operations("mock_a", "Mock A", "MockA")
    operations("mock_b", "Mock B", "MockB")
    operations("mock_c", "Mock C", "MockC")

    # Pede a parada durante a primeira operacao, como faria o botao.
    def pedir_parada(fn, payload):
        api.eventos.append((fn, payload))
        if payload["index"] == 0 and payload["status"] == "running":
            api.cancel_multi_extraction()

    api._emit_js = pedir_parada

    result = api.run_multi_extraction(
        ["mock_a", "mock_b", "mock_c"], date_range=DATAS, period="week"
    )

    assert result["succeeded"] == 1, "a operacao em andamento deve terminar normalmente"
    assert result["cancelled"] == 2, "as seguintes devem ser canceladas"
    assert result["failed"] == 0
    assert "cancelada" in result["message"].lower()
    assert [p["status"] for p in eventos_finais(api)] == ["success", "cancelled", "cancelled"]
    # So a que rodou entra no historico.
    assert len(isolated_history.get_history()) == 1


def test_parada_anterior_nao_afeta_a_proxima_fila(api, operations):
    operations("mock_a", "Mock A", "MockA")
    api.cancel_multi_extraction()

    result = api.run_multi_extraction(["mock_a"], date_range=DATAS, period="week")

    assert result["succeeded"] == 1, "o pedido de parada antigo nao pode vazar pra fila nova"
    assert result["cancelled"] == 0


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


def test_guarda_pasta_do_arquivo_e_print_do_erro(api, operations, isolated_history):
    """A tela usa esses caminhos nos botoes 'Abrir pasta' e 'Ver print'."""
    operations("mock", "Mock Co", "MockCo")
    operations("mock_fail", "Mock Falha", "MockFalha", page="nao-existe.html")

    api.run_extraction("mock", date_range=DATAS, period="week")
    assert os.path.isdir(api._last_folder)
    assert os.path.basename(api._last_folder) == "Week"

    api.run_extraction("mock_fail", date_range=DATAS)
    assert api._last_screenshot and os.path.isfile(api._last_screenshot)


def test_abrir_caminho_inexistente_avisa_em_vez_de_quebrar(api):
    resultado = api.open_last_folder()

    assert resultado["success"] is False
    assert "nao encontrada" in resultado["message"].lower()


def test_credenciais_nunca_sao_persistidas(api, operations, isolated_history):
    """A senha so pode viver em memoria durante a sessao."""
    operations("mock", "Mock Co", "MockCo")
    api.run_extraction("mock", date_range=DATAS)

    import settings_store

    assert "senha" not in str(settings_store.get_settings()).lower()
    assert "senha" not in str(isolated_history.get_history()).lower()


def test_fila_abre_um_navegador_so(api, operations, monkeypatch):
    """Cada operacao ganha uma sessao nova, mas o navegador e um so para
    a fila inteira — e ele e fechado no fim."""
    from automation import base

    abertos = []
    original = base.Navegador

    class Contador(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            abertos.append(self)

    monkeypatch.setattr(base, "Navegador", Contador)
    operations("mock_a", "Mock A", "MockA")
    operations("mock_b", "Mock B", "MockB")
    operations("mock_c", "Mock C", "MockC")

    result = api.run_multi_extraction(["mock_a", "mock_b", "mock_c"], date_range=DATAS, period="week")

    assert result["success"], result.get("message")
    assert len(abertos) == 1
    assert not abertos[0].ativo(), "o navegador da fila precisa ser fechado no fim"


def test_sessao_de_uma_operacao_nao_vaza_para_a_proxima(api, operations):
    """Com o navegador compartilhado, a operacao seguinte comeca sem os
    cookies da anterior: o login de cada site acontece do zero."""
    from automation.base import Navegador

    navegador = Navegador(headless=True)
    try:
        primeira = navegador.nova_pagina()
        primeira.context.add_cookies([{"name": "sessao", "value": "x", "url": "https://exemplo.dhl.com"}])
        segunda = navegador.nova_pagina()
        assert segunda.context.cookies() == []
    finally:
        navegador.fechar()
