"""Testes do arquivo de indicadores e da tabela entregue para a tela."""

import pytest


@pytest.fixture
def store(tmp_path, monkeypatch):
    """indicators_store apontando para uma pasta temporaria."""
    import indicators_store

    caminho = tmp_path / "indicators.json"
    monkeypatch.setattr(indicators_store, "_store_path", lambda: str(caminho))
    return indicators_store


DATAS_SETEMBRO = {"from_date": "2026-08-30", "to_date": "2026-09-19"}

SEMANA = {
    "2026-08-30": {
        "soma_goal": 245.99,
        "soma_measured_direct": 255.23,
        "efetividade": 0.9638,
        "hora_direta": 0.8537,
        "dispersao": 0.8182,
        "dentro": 9,
        "fora": 2,
        "cubo": None,
        "presenteismo": None,
        "coverage": None,
    }
}


def test_grava_e_le_por_operacao_e_periodo(store):
    store.salvar_extracao("hugo_boss", "week", SEMANA)

    guardado = store.get_indicators("hugo_boss")
    assert list(guardado["week"]) == ["2026-08-30"]
    assert guardado["week"]["2026-08-30"]["efetividade"] == 0.9638
    assert guardado["week"]["2026-08-30"]["extraido_em"]


def test_reextrair_substitui_a_semana_e_nao_mexe_nas_outras(store):
    store.salvar_extracao("hugo_boss", "week", SEMANA)
    store.salvar_extracao("hugo_boss", "week", {"2026-09-06": {"efetividade": 1.129}})
    store.salvar_extracao("hugo_boss", "week", {"2026-08-30": {"efetividade": 0.95}})

    semanas = store.get_indicators("hugo_boss")["week"]
    assert semanas["2026-08-30"]["efetividade"] == 0.95, "a semana reextraida e substituida"
    assert semanas["2026-09-06"]["efetividade"] == 1.129, "a outra fica intacta"


def test_reextrair_nao_apaga_o_que_foi_digitado_a_mao(store):
    """Sem esta regra, reextrair uma semana pra corrigir um numero
    apagaria calado o presenteismo e o coverage, e derrubaria o cubo."""
    store.salvar_extracao("hugo_boss", "week", SEMANA)
    store.salvar_manual("hugo_boss", "week", "2026-08-30",
                        {"presenteismo": 0.98, "coverage": 0.95})

    store.salvar_extracao("hugo_boss", "week", SEMANA)

    entrada = store.get_indicators("hugo_boss")["week"]["2026-08-30"]
    assert entrada["presenteismo"] == 0.98
    assert entrada["coverage"] == 0.95
    assert entrada["cubo"] == pytest.approx(0.9638 * 0.8537 * 0.98, abs=1e-6)


def test_cubo_sai_sozinho_quando_o_presenteismo_chega(store):
    store.salvar_extracao("hugo_boss", "week", SEMANA)
    assert store.get_indicators("hugo_boss")["week"]["2026-08-30"]["cubo"] is None

    store.salvar_manual("hugo_boss", "week", "2026-08-30", {"presenteismo": 0.98})

    assert store.get_indicators("hugo_boss")["week"]["2026-08-30"]["cubo"] is not None


def test_da_pra_digitar_antes_da_extracao(store):
    """Os dois caminhos funcionam em qualquer ordem."""
    store.salvar_manual("hugo_boss", "week", "2026-08-30", {"presenteismo": 0.98})
    store.salvar_extracao("hugo_boss", "week", SEMANA)

    entrada = store.get_indicators("hugo_boss")["week"]["2026-08-30"]
    assert entrada["presenteismo"] == 0.98
    assert entrada["efetividade"] == 0.9638


def test_semana_e_mes_nao_se_misturam(store):
    store.salvar_extracao("hugo_boss", "week", SEMANA)
    store.salvar_extracao("hugo_boss", "month", {"2026-09": {"efetividade": 1.0037}})

    guardado = store.get_indicators("hugo_boss")
    assert list(guardado["week"]) == ["2026-08-30"]
    assert list(guardado["month"]) == ["2026-09"]


def test_operacoes_diferentes_nao_se_misturam(store):
    store.salvar_extracao("hugo_boss", "week", SEMANA)
    store.salvar_extracao("nike", "week", {"2026-08-30": {"efetividade": 0.5}})

    assert store.get_indicators("hugo_boss")["week"]["2026-08-30"]["efetividade"] == 0.9638
    assert store.get_indicators("nike")["week"]["2026-08-30"]["efetividade"] == 0.5


# ---------------- A tabela que vai pra tela ----------------

@pytest.fixture
def api_com_dados(store, operations, monkeypatch):
    import api as api_module
    from api import Api

    monkeypatch.setattr(api_module, "indicators_store", store)
    operations("mock", "Mock Co", "MockCo")
    store.salvar_extracao("mock", "week", {
        "2026-08-30": {"efetividade": 0.9638, "hora_direta": 0.8537, "dispersao": 0.8182},
        "2026-09-06": {"efetividade": 1.129, "hora_direta": 0.9606, "dispersao": 0.6667},
    })
    store.salvar_extracao("mock", "month", {
        "2026-09": {"efetividade": 1.0037, "hora_direta": 0.9299, "dispersao": 0.60,
                    "de": "2026-09-01", "ate": "2026-09-19"},
    })
    return Api()


def test_tabela_tem_os_seis_indicadores_na_ordem(api_com_dados):
    tabela = api_com_dados.get_indicator_table("mock")

    assert [linha["chave"] for linha in tabela["linhas"]] == [
        "cubo", "efetividade", "hora_direta", "presenteismo", "dispersao", "coverage"
    ]
    assert tabela["operacao"] == "Mock Co"


def test_semanas_vem_antes_e_o_mes_no_fim(api_com_dados):
    colunas = api_com_dados.get_indicator_table("mock")["colunas"]

    assert [c["periodo"] for c in colunas] == ["week", "week", "month"]
    assert [c["titulo"] for c in colunas] == ["Week 36", "Week 37", "Setembro"]
    assert colunas[0]["subtitulo"] == "30/08 a 05/09"
    assert colunas[2]["subtitulo"] == "01 a 19/09"


def test_celulas_trazem_texto_e_cor(api_com_dados):
    linhas = {l["chave"]: l for l in api_com_dados.get_indicator_table("mock")["linhas"]}

    efetividade = linhas["efetividade"]["celulas"]
    assert [c["texto"] for c in efetividade] == ["96,4%", "112,9%", "100,4%"]
    assert [c["cor"] for c in efetividade] == ["verde", "azul", "verde"]

    dispersao = linhas["dispersao"]["celulas"]
    assert [c["cor"] for c in dispersao] == ["verde", "vermelho", "vermelho"]


def test_indicador_sem_numero_vira_vazio_sem_cor(api_com_dados):
    linhas = {l["chave"]: l for l in api_com_dados.get_indicator_table("mock")["linhas"]}

    for chave in ("cubo", "presenteismo", "coverage"):
        for celula in linhas[chave]["celulas"]:
            assert celula["texto"] == "", "vazio, nunca zero"
            assert celula["cor"] is None, "sem numero nao e vermelho"


def test_operacao_sem_nada_guardado_devolve_tabela_vazia(api_com_dados, operations):
    operations("nova", "Nova Op", "NovaOp")

    tabela = api_com_dados.get_indicator_table("nova")
    assert tabela["colunas"] == []


# ---------------- Da extracao ate o arquivo guardado ----------------

@pytest.fixture
def api_real(store, operations, sharepoint_dir, isolated_history, monkeypatch):
    """Api de verdade, rodando a automacao contra o mock, com o arquivo
    de indicadores numa pasta temporaria."""
    import api as api_module
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    monkeypatch.setattr(api_module, "indicators_store", store)

    instance = Api()
    instance.login("usuario", "senha")
    instance._emit_js = lambda fn, payload: None
    return instance


def test_extracao_semanal_calcula_e_guarda_as_tres_semanas(api_real, operations, store):
    """Fim a fim: extrai do mock, le o arquivo baixado, calcula e grava."""
    operations("mock", "Mock Co", "MockCo")

    resultado = api_real.run_extraction(
        "mock", date_range={"from_date": "2026-08-30", "to_date": "2026-09-19"}, period="week"
    )

    assert resultado["success"], resultado.get("message")
    semanas = store.get_indicators("mock")["week"]
    assert list(semanas) == ["2026-08-30", "2026-09-06", "2026-09-13"]
    assert round(semanas["2026-08-30"]["efetividade"] * 100, 1) == 96.4
    assert round(semanas["2026-09-13"]["dispersao"] * 100, 1) == 70.0


def test_extracao_mensal_guarda_um_mes_consolidado(api_real, operations, store):
    operations("mock", "Mock Co", "MockCo")

    resultado = api_real.run_extraction(
        "mock", date_range={"from_date": "2026-09-01", "to_date": "2026-09-19"}, period="month"
    )

    assert resultado["success"], resultado.get("message")
    meses = store.get_indicators("mock")["month"]
    assert list(meses) == ["2026-09"]
    assert round(meses["2026-09"]["efetividade"] * 100, 1) == 100.4
    assert meses["2026-09"]["de"] == "2026-09-01"


def test_semana_cortada_no_meio_fica_marcada_como_parcial(api_real, operations, store):
    """Um intervalo que nao cobre a semana inteira gera numero menor; a
    marca e o que evita ler isso como queda de indicador."""
    operations("mock", "Mock Co", "MockCo")

    api_real.run_extraction(
        "mock", date_range={"from_date": "2026-09-02", "to_date": "2026-09-19"}, period="week"
    )

    semanas = store.get_indicators("mock")["week"]
    assert semanas["2026-08-30"]["parcial"] is True, "comeca antes do intervalo"
    assert semanas["2026-09-13"]["parcial"] is False, "cabe inteira"


# ---------------- Quando o calculo nao roda ----------------

def _quebrar_leitura(monkeypatch, mensagem="formato nao suportado"):
    """Faz o leitor recusar o arquivo, como aconteceu de verdade com o
    .xls que o Summary entrega."""
    import api as api_module

    def recusar(caminho):
        raise ValueError(mensagem)

    monkeypatch.setattr(api_module.reader, "ler", recusar)


def test_arquivo_salvo_sem_indicador_nao_se_apresenta_como_concluida(
    api_real, operations, store, isolated_history, monkeypatch
):
    """Foi exatamente isso que escondeu o problema do .xls: a extracao
    salvava o arquivo, o calculo falhava calado e a tela dizia
    "Concluida"."""
    operations("mock", "Mock Co", "MockCo")
    _quebrar_leitura(monkeypatch)

    resultado = api_real.run_extraction(
        "mock", date_range=DATAS_SETEMBRO, period="week"
    )

    assert resultado["success"] is True, "o arquivo foi salvo de verdade"
    assert resultado["status"] == "warning", "mas nao e uma extracao concluida"
    assert "nao deu pra calcular" in resultado["indicators_message"]
    assert store.get_indicators("mock") == {}


def test_o_motivo_fica_visivel_no_historico(
    api_real, operations, isolated_history, monkeypatch
):
    operations("mock", "Mock Co", "MockCo")
    _quebrar_leitura(monkeypatch, "formato nao suportado")

    api_real.run_extraction("mock", date_range=DATAS_SETEMBRO, period="week")

    entrada = isolated_history.get_history()[0]
    assert entrada["status"] == "warning"
    assert "formato nao suportado" in entrada["indicators_message"]


def test_extracao_completa_continua_sendo_sucesso(
    api_real, operations, isolated_history
):
    operations("mock", "Mock Co", "MockCo")

    resultado = api_real.run_extraction("mock", date_range=DATAS_SETEMBRO, period="week")

    assert resultado["status"] == "success"
    assert not resultado.get("indicators_message")
    assert isolated_history.get_history()[0]["status"] == "success"


def test_fila_multipla_conta_as_que_ficaram_sem_indicador(
    api_real, operations, store, isolated_history, monkeypatch
):
    operations("mock_a", "Mock A", "MockA")
    operations("mock_b", "Mock B", "MockB")
    _quebrar_leitura(monkeypatch)
    avisos = []
    api_real._emit_js = lambda fn, payload: avisos.append(payload)

    resultado = api_real.run_multi_extraction(
        ["mock_a", "mock_b"], date_range=DATAS_SETEMBRO, period="week"
    )

    assert resultado["sem_indicador"] == 2
    assert "sem indicador" in resultado["message"]
    finais = [p["status"] for p in avisos if p.get("status") != "running"]
    assert finais == ["warning", "warning"]
