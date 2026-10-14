"""Manutencao do app: backup diario, versao dos dados (migracoes), aviso
de versao nova, a saude da pasta do SharePoint e a trava de senha
recusada."""

import datetime
import os
import shutil
import time
import zipfile

import pytest

import arquivos_sharepoint as sp
import atualizacao
import backup
import headcount_store
import migracoes
import settings_store

FIX = os.path.join(os.path.dirname(__file__), "fixtures")
HOJE = datetime.date(2026, 10, 14)


# ---------------- Backup ----------------

def test_backup_uma_vez_por_dia_e_guarda_sete(tmp_path):
    headcount_store.adicionar_gestor("SILVA,ANA", "hughes")
    for dias in range(9, -1, -1):
        backup.fazer(hoje=HOJE - datetime.timedelta(days=dias))
    assert backup.fazer(hoje=HOJE) is None  # o de hoje ja existe

    dias = sorted(item["dia"] for item in backup.listar())
    assert len(dias) == backup.DIAS_GUARDADOS
    assert dias[-1] == HOJE.isoformat()
    with zipfile.ZipFile(backup.listar()[0]["caminho"]) as zf:
        assert "headcount.json" in zf.namelist()
        assert not any(nome.startswith("backups") for nome in zf.namelist())


def test_sem_dados_nao_faz_backup():
    assert backup.fazer(hoje=HOJE) is None
    assert backup.listar() == []


def test_restaurar_guarda_antes_o_estado_atual():
    headcount_store.adicionar_gestor("SILVA,ANA", "hughes")
    zip_de_ontem = backup.fazer(hoje=HOJE - datetime.timedelta(days=1))
    headcount_store.adicionar_gestor("SOUZA,BRUNO", "hughes")

    feito = backup.restaurar(os.path.basename(zip_de_ontem), agora=datetime.datetime(2026, 10, 14, 9, 30))

    assert [g["nome"] for g in headcount_store.listar_gestores()] == ["SILVA,ANA"]
    seguranca = next(item for item in backup.listar() if item["antes_de_restaurar"])
    assert seguranca["id"] == feito["seguranca"] == "ScoreCard_2026-10-14_antes-de-restaurar-093000.zip"
    # E o de seguranca volta tudo como estava.
    backup.restaurar(seguranca["id"])
    assert len(headcount_store.listar_gestores()) == 2
    # O "antes de restaurar" nao conta como o ultimo backup do dia.
    assert not backup.ultimo()["antes_de_restaurar"]


def test_restaurar_backup_que_nao_existe_avisa():
    with pytest.raises(ValueError):
        backup.restaurar("ScoreCard_1999-01-01.zip")


# ---------------- Versao dos dados ----------------

def test_migracoes_rodam_uma_vez_e_em_ordem(monkeypatch):
    rodadas = []
    monkeypatch.setattr(migracoes, "MIGRACOES", [
        (1, "um", lambda: rodadas.append(1)),
        (2, "dois", lambda: rodadas.append(2)),
    ])
    assert migracoes.pendentes() == [(1, "um"), (2, "dois")]
    assert migracoes.migrar() == 2
    assert migracoes.migrar() == 2
    assert rodadas == [1, 2]
    assert settings_store.get_versao_dos_dados() == 2


def test_migracao_que_falha_para_a_fila_e_tenta_de_novo(monkeypatch):
    rodadas = []

    def quebra():
        rodadas.append("quebrou")
        raise OSError("arquivo preso")

    monkeypatch.setattr(migracoes, "MIGRACOES", [
        (1, "um", lambda: rodadas.append(1)),
        (2, "dois", quebra),
        (3, "tres", lambda: rodadas.append(3)),
    ])
    assert migracoes.migrar() == 1
    assert rodadas == [1, "quebrou"]
    assert migracoes.pendentes() == [(2, "dois"), (3, "tres")]


def test_a_migracao_das_semanas_trocadas_e_a_primeira():
    assert migracoes.MIGRACOES[0][0] == 1
    assert migracoes.VERSAO_ATUAL >= 1


# ---------------- Versao nova ----------------

def _publicar(base, *nomes):
    pasta = atualizacao.pasta(str(base))
    os.makedirs(pasta, exist_ok=True)
    for nome in nomes:
        with open(os.path.join(pasta, nome), "wb") as fh:
            fh.write(b"MZ")


def test_avisa_so_quando_a_publicada_e_mais_nova(tmp_path):
    _publicar(tmp_path, "ScoreCard_V.01.1.exe", "ScoreCard_V.01.2.exe", "outro.exe")
    assert atualizacao.verificar(str(tmp_path), "V.01.1")["nova"] == "V.01.2"
    assert atualizacao.verificar(str(tmp_path), "V.01.2")["nova"] is None
    assert atualizacao.verificar(str(tmp_path), "V.02.0")["nova"] is None


@pytest.mark.parametrize("base", [None, "nao-existe"])
def test_sem_pasta_nao_avisa(base):
    assert atualizacao.verificar(base, "V.01.1")["nova"] is None


def test_numero_da_versao():
    assert atualizacao.numero("V.01.2") == (1, 2)
    assert atualizacao.numero("V.10.0") > atualizacao.numero("V.09.9")
    assert atualizacao.numero("dev") is None


# ---------------- Saude da pasta ----------------

def _por(base, op, tipo, fixture, nome):
    pasta = sp.pasta(str(base), op, tipo)
    os.makedirs(pasta, exist_ok=True)
    caminho = os.path.join(pasta, nome)
    shutil.copy(os.path.join(FIX, fixture), caminho)
    antes = time.time() - 120
    os.utime(caminho, (antes, antes))
    return caminho


def test_saude_da_pasta_e_arquivos_nao_lidos(tmp_path):
    base = tmp_path / "sharepoint"
    base.mkdir()
    settings_store.set_sharepoint_folder(str(base))
    _por(base, "swa", "week", "summary_gestor_semana.xlsx", "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx")
    _por(base, "swa", "month", "summary_mes.xlsx", "ScoreCard_swa_20261001_080000.xlsx")  # antigo, sem periodo

    from api import Api

    Api().sincronizar_sharepoint()

    estado = sp.estado_da_pasta(str(base))
    assert estado["existe"] and estado["gravavel"]
    assert estado["relatorios"] == 2
    assert estado["mais_novo"]["operacao"] == "swa" and estado["mais_novo"]["tipo"] == "week"
    assert sp.lidos(str(base)) == 1
    assert [(i["operacao"], i["tipo"], i["nome"]) for i in sp.nao_lidos(str(base))] == [
        ("swa", "month", "ScoreCard_swa_20261001_080000.xlsx")]

    saude = Api().get_saude()
    assert saude["pasta"]["relatorios"] == 2
    assert saude["leitura"]["nao_lidos"][0]["operacao_rotulo"] == "Swa"
    assert saude["dados"]["atual"] == migracoes.VERSAO_ATUAL


def test_ler_a_pasta_do_zero_calcula_tudo_de_novo(tmp_path):
    base = tmp_path / "sharepoint"
    base.mkdir()
    settings_store.set_sharepoint_folder(str(base))
    _por(base, "swa", "week", "summary_gestor_semana.xlsx", "ScoreCard_swa_20261013_152259_20260830-20260919.xlsx")

    from api import Api

    app = Api()
    assert app.sincronizar_sharepoint()["atualizados"]
    assert not app.sincronizar_sharepoint()["atualizados"]
    relido = app.reler_sharepoint()
    assert [(a["operacao"], a["tipo"]) for a in relido["atualizados"]] == [("swa", "week")]


def test_pasta_que_nao_existe():
    estado = sp.estado_da_pasta("/nao/existe")
    assert estado["configurada"] and not estado["existe"] and not estado["gravavel"]


# ---------------- Senha recusada ----------------

RECUSADA = {"success": False, "message": "Cliquei em Sign In, mas a tela continua sendo a de login (senha?)."}


@pytest.fixture
def app_logado(sharepoint_dir, monkeypatch):
    import conexao
    from api import Api
    from automation import base as automacao_base
    from automation import generic

    monkeypatch.setattr(settings_store, "get_sharepoint_folder", lambda: str(sharepoint_dir))
    monkeypatch.setattr(conexao, "alcancavel", lambda url: True)
    chamadas = []
    monkeypatch.setattr(generic, "run", lambda key, **_: chamadas.append(key) or dict(RECUSADA))

    class Navegador:
        def __init__(self, **_):
            pass

        def ativo(self):
            return True

        def fechar(self):
            pass

    monkeypatch.setattr(automacao_base, "Navegador", Navegador)
    app = Api()
    app.login("usuario", "senha")
    app._emit_js = lambda *_: None
    app.chamadas = chamadas
    return app


def test_fila_para_na_segunda_senha_recusada(app_logado):
    resposta = app_logado.run_multi_extraction(["hughes", "swa", "rede", "lego"], period="week")

    assert app_logado.chamadas == ["hughes", "swa"]
    assert resposta["success"] is False


def test_depois_de_duas_recusas_nao_tenta_mais_ate_novo_login(app_logado):
    app_logado.run_extraction("hughes", period="week")
    app_logado.run_extraction("hughes", period="week")
    bloqueada = app_logado.run_extraction("hughes", period="week")

    assert app_logado.chamadas == ["hughes", "hughes"]
    assert bloqueada["senhas_recusadas"] == 2
    assert "recusou a senha 2 vezes" in bloqueada["message"]

    app_logado.login("usuario", "senha-certa")
    app_logado.run_extraction("hughes", period="week")
    assert app_logado.chamadas == ["hughes", "hughes", "hughes"]
