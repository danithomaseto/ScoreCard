import os

from automation.base import (
    export_report,
    get_report_frame,
    login,
    open_report,
    open_reports_menu,
    select_combobox,
    open_browser_session,
    take_screenshot,
)
from config.operations import OPERATIONS


def run(operation_key, base_dir, headless=True, username=None, password=None):
    """Executa a automacao completa (login + extracao do relatorio) para
    qualquer operacao cadastrada em config/operations.py.

    base_dir e a pasta do SharePoint/OneDrive escolhida pelo usuario nas
    configuracoes do aplicativo; cada operacao salva na sua propria
    subpasta dentro dela. username/password sao os informados na tela de
    login do aplicativo (nunca fixos no codigo).
    """
    config = OPERATIONS[operation_key]

    if not username or not password:
        return {
            "operation": operation_key,
            "success": False,
            "message": "Credenciais nao informadas. Faca login novamente.",
        }

    if not base_dir or not os.path.isdir(base_dir):
        return {
            "operation": operation_key,
            "success": False,
            "message": f"A pasta configurada nao existe ou nao foi definida: {base_dir}",
        }

    folder = config.get("sharepoint_folder") or config["label"]
    download_dir = os.path.join(base_dir, folder)

    def log(step):
        print(f"[{operation_key}] {step}", flush=True)

    log("abrindo o navegador...")
    playwright, browser, page = open_browser_session(headless=headless)
    result = {"operation": operation_key}

    try:
        log("fazendo login...")
        login(page, config["login_url"], username, password)

        log("login OK, abrindo menu Reports...")
        open_reports_menu(page)

        log("localizando o iframe de relatorios...")
        frame = get_report_frame(page)

        log(f"abrindo o relatorio '{config['report_name']}'...")
        open_report(frame, config["report_name"])

        log("preenchendo Date Range...")
        select_combobox(frame, "Date Range", config["date_range_type_text"])

        log("preenchendo Group By 1...")
        select_combobox(
            frame,
            "Group By 1",
            config["group_by_type_text"],
            option_text=config["group_by_option"],
        )

        log("exportando e baixando o arquivo...")
        saved_path = export_report(
            page,
            frame,
            download_dir,
            operation_key=operation_key,
            export_format=config["export_format"],
        )

        log(f"concluido: {saved_path}")
        result["success"] = True
        result["message"] = f"Relatorio salvo em {saved_path}"
        result["file_path"] = saved_path
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da automacao
        log(f"falhou: {exc}")
        result["success"] = False
        result["message"] = str(exc)
        result["screenshot"] = take_screenshot(page, operation_key)
    finally:
        page.context.close()
        browser.close()
        playwright.stop()

    return result
