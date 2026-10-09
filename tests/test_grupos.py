"""Resultado Gestor e Resultado Turno, e o gestor no Coverage.

A Week passou a sair Week > Supervisor > User ID: as somas da operacao
nao mudam, mas quem trabalhou com dois supervisores na semana vem em
duas linhas. As planilhas de teste com Supervisor e Shift sao as mesmas
summary_3semanas / summary_mes, com nomes ficticios e o P05 dividido
entre dois gestores (e dois turnos).
"""

import datetime

import pytest

import coverage_store
import coverage_tela
import grupos_store
import grupos_tela
import headcount_store
from conftest import FIXTURES
from indicators import grupos, limits, reader, weekly

HOJE = datetime.date(2026, 10, 20)
SETEMBRO = {"from_date": "2026-08-30", "to_date": "2026-09-19"}


def _ler(nome):
    return reader.ler(str(FIXTURES / nome))


# ---------------- Leitura ----------------

def test_tres_niveis_viram_semana_grupo_e_usuario():
    lido = _ler("summary_gestor_semana.xlsx")
    assert lido["tem_semana"] and lido["tem_grupo"]
    primeira = lido["linhas"][0]
    assert (primeira["semana"], primeira["grupo"], primeira["detalhe"]) == ("2026-08-30", "SILVA,ANA", "P01")


def test_dois_niveis_sem_data_sao_grupo_e_usuario():
    """Supervisor > User ID (o mes por gestor): o Medium nao e data, entao
    e o grupo, e nao a semana."""
    lido = _ler("summary_gestor_mes.xlsx")
    assert not lido["tem_semana"] and lido["tem_grupo"]
    assert lido["linhas"][0]["grupo"] == "SILVA,ANA"


def test_week_com_user_id_continua_sem_grupo():
    lido = _ler("summary_3semanas.xlsx")
    assert lido["tem_semana"] and not lido["tem_grupo"]


def test_turno_vazio_vira_grupo_sem_nome():
    lido = _ler("summary_turno_semana.xlsx")
    vazios = [l for l in lido["linhas"] if l["grupo"] == ""]
    assert vazios, "P12 em diante esta sem turno"
    assert grupos.rotulo("", "turno") == "Sem turno"
    assert grupos.rotulo(",", "gestor") == "Sem supervisor"
    assert grupos.rotulo("SILVA,ANA", "gestor") == "SILVA,ANA", "o nome fica igual a planilha"


# ---------------- A operacao com o Supervisor no meio ----------------

def test_operacao_com_supervisor_da_o_mesmo_que_sem():
    """Somas e dispersao da Week > Supervisor > User ID iguais as da
    Week > User ID, depois de juntar quem teve dois supervisores."""
    sem = weekly.por_semana(_ler("summary_3semanas.xlsx")["linhas"], "User ID")
    com = weekly.por_semana(weekly.juntar_por_pessoa(_ler("summary_gestor_semana.xlsx")["linhas"]), "User ID")
    for semana in sem:
        for campo in ("efetividade", "hora_direta", "dispersao", "dentro", "fora", "soma_total"):
            assert com[semana][campo] == sem[semana][campo], (semana, campo)


def test_sem_juntar_a_pessoa_contaria_duas_vezes():
    linhas = _ler("summary_gestor_semana.xlsx")["linhas"]
    separado = weekly.por_semana(linhas, "User ID")["2026-08-30"]
    junto = weekly.por_semana(weekly.juntar_por_pessoa(linhas), "User ID")["2026-08-30"]
    assert separado["dentro"] + separado["fora"] == junto["dentro"] + junto["fora"] + 1


def test_var_refeito_com_as_horas_somadas():
    assert weekly.var_de(31.4, 30.45) == 3.0
    assert weekly.var_de(4.49, 22.28) == -80.0
    assert weekly.var_de(0, 10) is None


# ---------------- Por grupo ----------------

def test_indicadores_de_cada_gestor_vem_das_linhas_dele():
    linhas = _ler("summary_gestor_mes.xlsx")["linhas"]
    por_gestor = grupos.por_grupo(linhas)
    assert set(por_gestor) == {"SILVA,ANA", "SOUZA,BRUNO", ","}
    ana = [l for l in linhas if l["grupo"] == "SILVA,ANA"]
    esperado = weekly.totais(ana, nivel_detalhe="User ID")
    assert por_gestor["SILVA,ANA"]["efetividade"] == esperado["efetividade"]
    assert por_gestor["SILVA,ANA"]["dispersao"] == esperado["dispersao"]


def test_usuario_de_dois_gestores_fica_no_de_mais_horas_para_o_coverage():
    """P05 tem 60% das horas com SILVA,ANA e 40% com SOUZA,BRUNO: no
    coverage ele entra so na Ana, com todas as horas dele."""
    por_gestor = grupos.por_grupo(_ler("summary_gestor_mes.xlsx")["linhas"])
    assert "P05" in por_gestor["SILVA,ANA"]["cobertura"]
    assert "P05" not in por_gestor["SOUZA,BRUNO"]["cobertura"]
    assert por_gestor["SILVA,ANA"]["cobertura"]["P05"]["lms"] == pytest.approx(114.19, abs=0.01)


# ---------------- Da extracao ate a aba ----------------

@pytest.fixture
def api_real(operations, sharepoint_dir, isolated_history, monkeypatch):
    import settings_store
    from api import Api

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    instance = Api()
    instance.login("usuario", "senha")
    instance._emit_js = lambda fn, payload: None
    return instance


def _tabela(tela, nome):
    tabela = next(t for t in tela["tabelas"] if t["id"] == nome)
    return {l["chave"]: [c["texto"] for c in l["celulas"]] for l in tabela["linhas"]}


def test_extracao_gestor_week_e_month_monta_a_aba(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    semana = api_real.run_extraction("mock", date_range=SETEMBRO, period="gestor_week")
    mes = api_real.run_extraction("mock", date_range={"from_date": "2026-09-01", "to_date": "2026-09-19"},
                                  period="gestor_month")
    assert semana["status"] == "success", semana.get("indicators_message")
    assert mes["status"] == "success", mes.get("indicators_message")

    tela = grupos_tela.montar("gestor", "mock", "2026-09", hoje=HOJE)
    assert [c["titulo"] for c in tela["colunas"]] == ["Week 36", "Week 37", "Week 38", "Setembro"]
    assert [g["rotulo"] for g in tela["grupos"]] == ["SILVA,ANA", "SOUZA,BRUNO", "Sem supervisor"]

    ana = _tabela(tela, "SILVA,ANA")
    esperado = grupos.por_grupo(_ler("summary_gestor_mes.xlsx")["linhas"])["SILVA,ANA"]
    assert ana["efetividade"][-1] == limits.formatar(esperado["efetividade"])
    assert ana["presenteismo"] == ["", "", "", ""], "sem gestor com o mesmo nome no Headcount"
    assert ana["cubo"] == ["", "", "", ""]
    assert all(ana["coverage"]), "dias x horas do calendario"


def test_presenteismo_so_quando_o_nome_bate_com_o_headcount(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="gestor_week")
    # Mesmo nome com outra caixa e espaco depois da virgula: bate.
    ana = headcount_store.adicionar_gestor("Silva, Ana", "mock")
    headcount_store.atualizar_gestor(ana["id"], {"hc": 10})
    headcount_store.lancar_faltas(ana["id"], "2026-09-S2", "2")
    # Nome diferente: nao puxa nada.
    bruno = headcount_store.adicionar_gestor("Bruno Souza", "mock")
    headcount_store.atualizar_gestor(bruno["id"], {"hc": 10})

    tela = grupos_tela.montar("gestor", "mock", "2026-09", hoje=HOJE)
    vinculo = {g["id"]: g["vinculado"] for g in tela["grupos"]}
    assert vinculo == {"SILVA,ANA": True, "SOUZA,BRUNO": False, ",": False}

    ana_tabela = _tabela(tela, "SILVA,ANA")
    assert all(ana_tabela["presenteismo"]), "as tres semanas com o HC da Ana"
    assert ana_tabela["presenteismo"][1] != "100,00%", "as faltas da S2 entram na Week 37"
    assert all(ana_tabela["cubo"])
    assert _tabela(tela, "SOUZA,BRUNO")["presenteismo"] == ["", "", ""]


def test_turno_nao_tem_presenteismo_nem_cubo(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    resultado = api_real.run_extraction("mock", date_range=SETEMBRO, period="turno_week")
    assert resultado["status"] == "success", resultado.get("indicators_message")

    tela = grupos_tela.montar("turno", "mock", "2026-09", hoje=HOJE)
    assert [g["rotulo"] for g in tela["grupos"]] == ["ADM", "T1", "T2", "Sem turno"]
    tabela = next(t for t in tela["tabelas"] if t["id"] == "T1")
    linhas = {l["chave"]: l for l in tabela["linhas"]}
    for chave in ("presenteismo", "cubo"):
        assert all(c["nao_se_aplica"] and c["copia_vazia"] for c in linhas[chave]["celulas"])
    assert all(c["texto"] for c in linhas["efetividade"]["celulas"])


def test_esconder_gestor_vale_para_a_proxima_vez(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="gestor_week")
    da_tela = ["SILVA,ANA", "SOUZA,BRUNO", ","]

    assert api_real.set_grupos_visiveis("gestor", "mock", da_tela, ["SILVA,ANA"])["success"]

    tela = grupos_tela.montar("gestor", "mock", "2026-09", hoje=HOJE)
    assert [t["id"] for t in tela["tabelas"]] == ["SILVA,ANA"]
    assert [g["visivel"] for g in tela["grupos"]] == [True, False, False]


def test_gestor_novo_aparece_marcado():
    """Guarda os escondidos, nao os escolhidos: quem chega depois aparece."""
    grupos_store.salvar("gestor", "hugo_boss", "week", {"2026-09-06": {"A": {}, "B": {}}})
    grupos_tela.definir_visiveis("gestor", "hugo_boss", ["A", "B"], ["A"])
    grupos_store.salvar("gestor", "hugo_boss", "week", {"2026-09-13": {"C": {}}})

    tela = grupos_tela.montar("gestor", "hugo_boss", "2026-09", hoje=HOJE)
    assert {g["id"]: g["visivel"] for g in tela["grupos"]} == {"A": True, "B": False, "C": True}


def test_extracao_de_gestor_sem_a_coluna_avisa(api_real, operations, monkeypatch):
    import api as api_module

    operations("mock", "Mock Co", "MockCo")
    sem_gestor = _ler("summary_3semanas.xlsx")
    monkeypatch.setattr(api_module.reader, "ler", lambda caminho: sem_gestor)
    resultado = api_real.run_extraction("mock", date_range=SETEMBRO, period="gestor_week")

    assert resultado["status"] == "warning"
    assert "Supervisor" in resultado["indicators_message"]


# ---------------- Coverage por gestor ----------------

def test_week_guarda_o_gestor_de_cada_usuario_no_coverage(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="week")

    usuarios = coverage_store.extracoes("mock")["mock"]["week:2026-08-30"]["usuarios"]
    assert usuarios["P01"]["gestor"] == "SILVA,ANA"
    assert usuarios["P05"]["gestor"] == "SILVA,ANA", "60% das horas com a Ana"


def test_filtro_de_gestor_no_coverage(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="week")
    coverage_store.definir_sinergia("mock", "week:2026-08-30", "recebida", "10")

    todos = coverage_tela.montar("mock", "semanal", "2026-09", "2026-W36", hoje=HOJE)
    assert [g["rotulo"] for g in todos["gestores"]] == [
        "Todos os gestores", "SILVA,ANA", "SOUZA,BRUNO", "Sem supervisor"]

    ana = coverage_tela.montar("mock", "semanal", "2026-09", "2026-W36", hoje=HOJE, gestor="SILVA,ANA")
    assert {l["usuario"] for l in ana["linhas"]} == {"P01", "P02", "P03", "P04", "P05", "P06"}
    assert all(l["gestor_rotulo"] == "SILVA,ANA" for l in ana["linhas"])
    # A sinergia e da operacao: nao entra no coverage de um gestor.
    assert ana["total"]["recebida"] == 0
    assert not ana["total"]["sinergia_editavel"]
    assert ana["cards"]["operacao_nota"] == "Gestor: SILVA,ANA"
    assert len(ana["linhas"]) < len(todos["linhas"])


def test_coverage_do_mes_pega_o_gestor_das_semanas(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="week")
    api_real.run_extraction("mock", date_range={"from_date": "2026-09-01", "to_date": "2026-09-19"},
                            period="month")

    tela = coverage_tela.montar("mock", "mes", "2026-09", hoje=HOJE, gestor="SOUZA,BRUNO")
    assert tela["linhas"], "a extracao Month nao traz o Supervisor; vem das semanas do mes"
    assert all(l["gestor"] == "SOUZA,BRUNO" for l in tela["linhas"])


def test_extracao_antiga_sem_gestor_continua_aparecendo():
    coverage_store.salvar_extracao("abb", "week", {"2026-09-20": {"X": {"lms": 40, "diretas_sem_meta": 0}}})
    tela = coverage_tela.montar("abb", "semanal", "2026-09", hoje=HOJE)
    assert tela["linhas"][0]["gestor_rotulo"] == "—"
    assert tela["gestores"][-1]["id"] == coverage_tela.SEM_GESTOR


# ---------------- Varios filtros de uma vez ----------------

def test_varios_filtros_roda_cada_tipo_para_a_operacao(api_real, operations, isolated_history):
    operations("mock", "Mock Co", "MockCo")
    avisos = []
    api_real._emit_js = lambda fn, payload: avisos.append(payload)

    resultado = api_real.run_multi_filters("mock", ["month", "week", "gestor_week"],
                                           date_range={"from_date": "2026-09-01", "to_date": "2026-09-19"})

    assert resultado["success"], resultado["message"]
    assert resultado["succeeded"] == 3
    # Na ordem dos tipos da tela, nao na ordem do clique.
    tipos = [e["period_type"] for e in reversed(isolated_history.get_history())]
    assert tipos == ["Week", "Month", "Gestor · Week"]
    rotulos = {p["operation_label"] for p in avisos}
    assert rotulos == {"Week", "Month", "Gestor · Week"}


def test_varios_filtros_sem_tipo_avisa(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    assert not api_real.run_multi_filters("mock", [])["success"]
    assert not api_real.run_multi_filters("nao_existe", ["week"])["success"]


# ---------------- Nomes do Summary no Headcount ----------------

def test_headcount_sugere_os_supervisores_do_summary(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    api_real.run_extraction("mock", date_range=SETEMBRO, period="gestor_week")

    nomes = api_real.get_nomes_do_summary("mock")
    assert nomes == ["SILVA,ANA", "SOUZA,BRUNO"], "sem o grupo vazio (sem supervisor)"
    assert api_real.get_nomes_do_summary("nao_existe") == []


def test_headcount_marca_quem_bate_com_o_summary(api_real, operations):
    operations("mock", "Mock Co", "MockCo")
    headcount_store.adicionar_gestor("silva, ana", "mock")
    headcount_store.adicionar_gestor("Bruno Souza", "mock")

    antes = {l["gestor"]: l["summary"] for l in api_real.get_headcount("mock")["linhas"]}
    assert antes == {"silva, ana": None, "Bruno Souza": None}, "sem extracao ainda: nao da para dizer"

    api_real.run_extraction("mock", date_range=SETEMBRO, period="week")
    depois = {l["gestor"]: l["summary"] for l in api_real.get_headcount("mock")["linhas"]}
    assert depois == {"silva, ana": "ligado", "Bruno Souza": "sem_par"}


# ---------------- Preferencias de tela ----------------

def test_preferencias_de_tela_ficam_guardadas():
    import settings_store

    assert settings_store.get_preferencias() == {
        "tema": "escuro", "densidade": "confortavel", "menu_recolhido": False}
    settings_store.set_preferencia("tema", "claro")
    settings_store.set_preferencia("menu_recolhido", True)
    assert settings_store.get_preferencias()["tema"] == "claro"
    assert settings_store.get_preferencias()["menu_recolhido"] is True
    assert settings_store.get_sharepoint_folder() is None, "nao mexe no resto das configuracoes"


def test_preferencia_invalida_e_recusada():
    from api import Api

    api = Api()
    assert not api.set_preferencia("tema", "roxo")["success"]
    assert not api.set_preferencia("fonte", "grande")["success"]
    assert api.get_preferencias()["tema"] == "escuro"
