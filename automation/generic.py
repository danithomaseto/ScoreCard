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


# Pasta do SharePoint "CLM GESTAO CONJUNTA - Automacao Score", sincronizada
# via OneDrive. Cada operacao salva numa subpasta com o nome dela (ex:
# .../Hugo Boss, .../ABB), igual a estrutura que ja existe no SharePoint.
SHAREPOINT_BASE_DIR = r"C:\Users\danitho2\OneDrive - DPDHL\CLM GESTÃO CONJUNTA - Automação Score"


def default_download_dir(config):
    override = os.environ.get("DOWNLOAD_DIR")
    if override:
        return override
    folder = config.get("sharepoint_folder") or config["label"]
    return os.path.join(SHAREPOINT_BASE_DIR, folder)


def run(operation_key, headless=True, username=None, password=None):
    """Executa a automacao completa (login + extracao do relatorio) para
    qualquer operacao cadastrada em config/operations.py. Todas seguem o
    mesmo fluxo: login, Reports > Reports, abrir o relatorio, aplicar os
    filtros e exportar em Excel.

    Se username/password forem passados (ex: vindos do painel, digitados
    pela pessoa que disparou a tarefa), eles tem prioridade. Caso
    contrario, cai para as variaveis de ambiente (uso do app.py local).
    """
    config = OPERATIONS[operation_key]
    username = username or os.environ.get(config["username_env"])
    password = password or os.environ.get(config["password_env"])

    if not username or not password:
        return {
            "operation": operation_key,
            "success": False,
            "message": (
                f"Credenciais nao configuradas. Defina {config['username_env']} e "
                f"{config['password_env']} no arquivo .env, ou informe no painel."
            ),
        }

    download_dir = default_download_dir(config)

    playwright, browser, page = open_browser_session(headless=headless)
    result = {"operation": operation_key}

    try:
        login(page, config["login_url"], username, password)
        open_reports_menu(page)

        frame = get_report_frame(page)
        open_report(frame, config["report_name"])

        select_combobox(frame, "Date Range", config["date_range_type_text"])
        select_combobox(
            frame,
            "Group By 1",
            config["group_by_type_text"],
            option_text=config["group_by_option"],
        )

        saved_path = export_report(
            page,
            frame,
            download_dir,
            operation_key=operation_key,
            export_format=config["export_format"],
        )

        result["success"] = True
        result["message"] = f"Relatorio salvo em {saved_path}"
        result["file_path"] = saved_path
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da automacao
        result["success"] = False
        result["message"] = str(exc)
        result["screenshot"] = take_screenshot(page, operation_key)
    finally:
        page.context.close()
        browser.close()
        playwright.stop()

    return result
