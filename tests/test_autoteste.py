"""autoteste.py: a conferencia que o build roda no app gerado."""

import openpyxl
import pytest

import autoteste
from tools import build


def test_codigo_fonte_passa(tmp_path):
    relatorio = tmp_path / "autoteste.txt"
    assert autoteste.rodar(str(relatorio)) == 0
    assert relatorio.read_text(encoding="utf-8").strip() == "AUTOTESTE OK"


def test_planilha_de_teste_e_fechada(monkeypatch):
    # No Windows, a planilha aberta em read_only nao deixava apagar a pasta
    # temporaria ("arquivo em uso") e o autoteste falhava so la.
    abertas = []
    original = openpyxl.load_workbook

    def abrir(*args, **kwargs):
        livro = original(*args, **kwargs)
        fechar = livro.close
        estado = {"fechado": False}

        def close():
            estado["fechado"] = True
            fechar()

        livro.close = close
        abertas.append(estado)
        return livro

    monkeypatch.setattr(openpyxl, "load_workbook", abrir)
    problemas = []
    autoteste._planilha(problemas)
    assert problemas == []
    assert abertas and all(estado["fechado"] for estado in abertas)


def test_import_quebrado_vira_linha_do_relatorio(tmp_path, monkeypatch):
    monkeypatch.setattr(autoteste, "MODULOS", ("modulo_que_nao_existe",))
    relatorio = tmp_path / "autoteste.txt"
    assert autoteste.rodar(str(relatorio)) == 1
    linhas = relatorio.read_text(encoding="utf-8").splitlines()
    assert linhas[0] == "AUTOTESTE FALHOU"
    assert "import modulo_que_nao_existe" in linhas[1]


def test_build_mostra_o_que_o_autoteste_achou(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(build, "LOG", str(tmp_path / "build.log"))
    monkeypatch.setattr(build, "DIST", str(tmp_path / "dist"))
    saida = ("12 INFO: Building COLLECT\n[autoteste] AUTOTESTE FALHOU\n"
             "[autoteste] - import webview: ModuleNotFoundError: No module named 'clr'\n"
             "[autoteste] - tela sem ui/js/13-novidades.js\nSystemExit: AUTOTESTE FALHOU\n")
    with pytest.raises(build.BuildFalhou):
        build.falhar("Gerando o executavel", saida)
    tela = capsys.readouterr().out
    assert "  - import webview: ModuleNotFoundError: No module named 'clr'" in tela
    assert "  - tela sem ui/js/13-novidades.js" in tela
    assert "nao passou no autoteste" in tela
