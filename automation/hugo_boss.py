import os

from automation.base import (
    export_report,
    login,
    open_report,
    open_reports_menu,
    select_dropdown,
    open_browser_session,
    take_screenshot,
)
from config.operations import OPERATIONS

OPERATION_KEY = "hugo_boss"


def default_download_dir():
    override = os.environ.get("DOWNLOAD_DIR")
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), "Desktop")


def run(headless=True):
    config = OPERATIONS[OPERATION_KEY]
    username = os.environ.get(config["username_env"])
    password = os.environ.get(config["password_env"])

    if not username or not password:
        return {
            "operation": OPERATION_KEY,
            "success": False,
            "message": (
                f"Credenciais nao configuradas. Defina {config['username_env']} e "
                f"{config['password_env']} no arquivo .env."
            ),
        }

    download_dir = default_download_dir()

    playwright, browser, page = open_browser_session(headless=headless)
    result = {"operation": OPERATION_KEY}

    try:
        login(page, config["login_url"], username, password)
        open_reports_menu(page)
        open_report(page, config["report_name"])

        select_dropdown(page, "Date Range", config["date_range_option"])
        select_dropdown(page, "Group By 1", config["group_by_option"])

        saved_path = export_report(
            page,
            download_dir,
            operation_key=OPERATION_KEY,
            export_format=config["export_format"],
        )

        result["success"] = True
        result["message"] = f"Relatorio salvo em {saved_path}"
        result["file_path"] = saved_path
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da automacao
        result["success"] = False
        result["message"] = str(exc)
        result["screenshot"] = take_screenshot(page, OPERATION_KEY)
    finally:
        page.context.close()
        browser.close()
        playwright.stop()

    return result
