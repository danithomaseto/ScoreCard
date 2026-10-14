"""Novidades da versao, tour do primeiro uso (novidades.py), a imagem da
tabela salva em Downloads (exportar_imagem.py) e as operacoes do rodizio
da apresentacao automatica (Api.operacoes_com_dados)."""

import base64
import datetime
import os
import struct
import zlib

import pytest

import exportar_imagem
import history_store
import indicators_store
import novidades
import settings_store
import versao


# ---------------- Novidades e tour ----------------

def test_quem_nunca_usou_ganha_o_tour():
    estado = novidades.estado()
    assert estado["mostrar"] == "tour"
    assert estado["versao"] == versao.info()["versao"]

    depois = novidades.marcar("tour")
    # Quem acabou de fazer o tour nao ve as novidades da mesma versao.
    assert depois["mostrar"] is None
    assert settings_store.get_vistos() == {"novidades": versao.info()["versao"], "tour": True}


def test_quem_ja_usava_ve_as_novidades_uma_vez(tmp_path):
    settings_store.set_sharepoint_folder(str(tmp_path))
    estado = novidades.estado()
    assert estado["mostrar"] == "novidades"
    assert estado["itens"] and all(item["titulo"] and item["texto"] for item in estado["itens"])

    assert novidades.marcar("novidades")["mostrar"] is None
    # O tour nao e forcado em quem ja usava: fica em Configuracoes > Ajuda.
    assert novidades.estado()["mostrar"] is None


def test_versao_nova_mostra_as_novidades_de_novo():
    history_store.add_entry({"operation": "Hughes", "status": "success"})
    settings_store.marcar_visto("tour", True)
    settings_store.marcar_visto("novidades", "V.00.9")
    assert novidades.estado()["mostrar"] == "novidades"


def test_versao_sem_novidades_nao_abre_janela(monkeypatch):
    settings_store.marcar_visto("tour", True)
    monkeypatch.setattr(novidades, "NOVIDADES", {})
    assert novidades.estado()["mostrar"] is None


def test_marca_invalida_e_settings_estranho():
    with pytest.raises(ValueError):
        novidades.marcar("outra coisa")
    settings = settings_store.get_settings()
    settings["vistos"] = ["lixo"]
    settings_store.save_settings(settings)
    assert settings_store.get_vistos() == {"novidades": "", "tour": False}


def test_versoes_das_novidades_no_formato():
    for numero in novidades.NOVIDADES:
        assert versao.FORMATO.match(numero), numero


def test_api_das_novidades():
    import api

    a = api.Api()
    assert a.get_novidades()["mostrar"] == "tour"
    assert a.marcar_visto("tour")["success"] is True
    assert a.marcar_visto("x")["success"] is False


# ---------------- Imagem da tabela ----------------

def _png(largura=2, altura=2):
    linhas = b"".join(b"\x00" + b"\xff\xff\xff" * largura for _ in range(altura))
    def bloco(tipo, dados):
        return struct.pack(">I", len(dados)) + tipo + dados + struct.pack(">I", zlib.crc32(tipo + dados))
    return (exportar_imagem.ASSINATURA_PNG + bloco(b"IHDR", struct.pack(">IIBBBBB", largura, altura, 8, 2, 0, 0, 0))
            + bloco(b"IDAT", zlib.compress(linhas)) + bloco(b"IEND", b""))


def test_salva_o_png_com_nome_limpo(tmp_path):
    agora = datetime.datetime(2026, 10, 14, 15, 30, 0)
    texto = "data:image/png;base64," + base64.b64encode(_png()).decode()
    caminho = exportar_imagem.salvar_png("Hughes · Setembro/2026", texto, destino=str(tmp_path), agora=agora)
    assert os.path.basename(caminho) == "ScoreCard_Hughes_Setembro_2026_20261014_153000.png"
    with open(caminho, "rb") as fh:
        assert fh.read() == _png()


@pytest.mark.parametrize("conteudo", [
    base64.b64encode(b"MZ isto nao e png").decode(),
    "nao e base64 !!!",
    None,
])
def test_recusa_o_que_nao_e_png(tmp_path, conteudo):
    with pytest.raises(ValueError):
        exportar_imagem.salvar_png("x", conteudo, destino=str(tmp_path))
    assert not os.listdir(tmp_path)


def test_nome_nao_sai_da_pasta():
    nome = exportar_imagem.nome_do_arquivo("../../Windows/system32", datetime.datetime(2026, 1, 2, 3, 4, 5))
    assert "/" not in nome and "\\" not in nome and ".." not in nome
    assert exportar_imagem.nome_do_arquivo("", datetime.datetime(2026, 1, 2, 3, 4, 5)).startswith("ScoreCard_tabela_")


def test_api_salva_a_imagem_em_downloads(tmp_path, monkeypatch):
    import api

    monkeypatch.setattr(exportar_imagem.diagnostico, "pasta_de_destino", lambda: str(tmp_path))
    a = api.Api()
    monkeypatch.setattr(a, "_mostrar_arquivo", lambda caminho, descricao: None)
    r = a.salvar_imagem("Swa", base64.b64encode(_png()).decode())
    assert r["success"] and os.path.isfile(r["caminho"])
    assert a.salvar_imagem("Swa", "AAAA")["success"] is False


# ---------------- Rodizio da apresentacao automatica ----------------

def test_operacoes_com_dados_no_mes():
    import api

    indicators_store.salvar_extracao("swa", "week", {"2026-08-31": {"efetividade": 1.0}})
    indicators_store.salvar_extracao("lego", "month", {"2026-09": {"efetividade": 0.9}})
    indicators_store.salvar_extracao("hughes", "week", {"2026-08-03": {"efetividade": 1.0}})
    a = api.Api()
    # Na ordem do menu; a semana de 31/08 tem dias em setembro.
    assert a.operacoes_com_dados("2026-09") == ["swa", "lego"]
    assert a.operacoes_com_dados("2026-08") == ["hughes", "swa"]
    assert a.operacoes_com_dados("2026-11") == []
    assert a.operacoes_com_dados("setembro") == []
    assert a.operacoes_com_dados(None) == []
