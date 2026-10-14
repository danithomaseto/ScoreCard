"""ScoreCardApp --autoteste [arquivo]: confere, sem abrir janela, que o
pacote gerado pelo build tem tudo o que o app usa. O build (build.spec)
roda isto no app em pasta antes de junta-lo ao lancador; se faltar
alguma coisa, o build para ali, e nao na maquina de quem usa.

Importa os modulos que so carregam na hora de extrair ou ler um
relatorio, faz uma planilha de ida e volta e confere os arquivos da tela
e o driver do Playwright. O main.py chama isto antes dos imports dele:
um import que quebra vira uma linha do relatorio, em vez de derrubar o
app (que, sem console, mostraria so uma janela de erro).

Cuidado com o Windows: arquivo aberto nao se apaga. A planilha de teste
e fechada antes de a pasta temporaria sair — sem isso o autoteste falhava
so no Windows, com "arquivo em uso", e passava no Linux.
"""

import importlib
import os
import re
import sys
import tempfile
import traceback

MODULOS = ("api", "automation.generic", "automation.base", "indicators.reader", "indicators.faltas",
           "indicators.pico", "indicators.coverage", "indicators.grupos", "indicators.indiretas",
           "lancamentos", "arquivos_sharepoint", "diagnostico", "navegadores", "novidades",
           "explicacoes", "exportar_imagem", "openpyxl", "xlrd", "concurrent.futures",
           "playwright.sync_api", "webview")


def _pasta_do_app():
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _imports(problemas):
    for nome in MODULOS:
        try:
            importlib.import_module(nome)
        except Exception as exc:  # noqa: BLE001
            problemas.append(f"import {nome}: {type(exc).__name__}: {exc}")


def _planilha(problemas):
    try:
        import openpyxl

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as pasta:
            caminho = os.path.join(pasta, "teste.xlsx")
            planilha = openpyxl.Workbook()
            planilha.active["A1"] = "ok"
            planilha.save(caminho)
            # read_only deixa o arquivo aberto ate o close().
            livro = openpyxl.load_workbook(caminho, read_only=True)
            try:
                valor = livro.active["A1"].value
            finally:
                livro.close()
            if valor != "ok":
                problemas.append("openpyxl: ida e volta da planilha")
    except Exception as exc:  # noqa: BLE001
        problemas.append(f"openpyxl: {type(exc).__name__}: {exc}")


def _driver_do_playwright(problemas):
    try:
        from playwright._impl._driver import compute_driver_executable

        driver = compute_driver_executable()
        for caminho in (driver if isinstance(driver, tuple) else (driver,)):
            if not os.path.isfile(caminho):
                problemas.append(f"driver do Playwright sem {caminho}")
    except Exception as exc:  # noqa: BLE001
        problemas.append(f"driver do Playwright: {type(exc).__name__}: {exc}")


def _arquivos_da_tela(problemas):
    ui = os.path.join(_pasta_do_app(), "ui")
    try:
        with open(os.path.join(ui, "index.html"), encoding="utf-8") as fh:
            html = fh.read()
    except OSError as exc:
        problemas.append(f"tela: {exc}")
        return
    for arquivo in re.findall(r'(?:src|href)="((?:js|css|assets)/[^"]+)"', html):
        if not os.path.isfile(os.path.join(ui, *arquivo.split("/"))):
            problemas.append(f"tela sem ui/{arquivo}")


def rodar(destino=None):
    """Devolve 0 se esta tudo certo. Com destino, grava o resultado nele
    (a primeira linha e AUTOTESTE OK ou AUTOTESTE FALHOU)."""
    problemas = []
    for etapa in (_imports, _planilha, _driver_do_playwright, _arquivos_da_tela):
        try:
            etapa(problemas)
        except Exception:  # noqa: BLE001 - o relatorio sai de qualquer jeito
            problemas.append(f"{etapa.__name__}: {traceback.format_exc(limit=3)}")
    texto = "AUTOTESTE OK" if not problemas else "AUTOTESTE FALHOU\n" + "\n".join(problemas)
    if destino:
        with open(destino, "w", encoding="utf-8") as fh:
            fh.write(texto + "\n")
    print(texto)
    return 0 if not problemas else 1
