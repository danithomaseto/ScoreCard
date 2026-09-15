import os
from datetime import datetime

from automation.base import (
    export_report,
    get_report_frame,
    login,
    open_report,
    open_reports_menu,
    select_combobox,
    select_custom_date_range,
    open_browser_session,
    take_screenshot,
)
from config.operations import OPERATIONS


def _to_site_date_format(iso_date):
    """Converte yyyy-mm-dd (formato do <input type="date"> do navegador)
    pro formato dd/mm/yyyy que o campo do Summary espera."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")


def run(
    operation_key,
    base_dir,
    headless=True,
    username=None,
    password=None,
    on_progress=None,
    date_range=None,
    group_by=None,
):
    """Executa a automacao completa (login + extracao do relatorio) para
    qualquer operacao cadastrada em config/operations.py.

    base_dir e a pasta do SharePoint/OneDrive escolhida pelo usuario nas
    configuracoes do aplicativo; cada operacao salva na sua propria
    subpasta dentro dela. username/password sao os informados na tela de
    login do aplicativo (nunca fixos no codigo). on_progress, se
    informado, e chamado com uma frase curta a cada etapa (usado pra
    atualizar a tela do app em tempo real). date_range, se informado, e
    um dict {"from_date": "yyyy-mm-dd", "to_date": "yyyy-mm-dd"} pra usar
    um periodo especifico em vez do padrao (Ultima semana) da operacao.
    group_by, se informado, e o texto exato de uma das opcoes de "Group
    By 1" (config.operations.GROUP_BY_OPTIONS) escolhida na tela, usado
    no lugar do padrao "User ID" da operacao.
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
        if on_progress:
            try:
                on_progress(step)
            except Exception:
                pass  # nunca deixa um erro de UI derrubar a automacao

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

        if date_range:
            log(f"selecionando periodo especifico ({date_range['from_date']} a {date_range['to_date']})...")
            select_custom_date_range(
                frame,
                from_date=_to_site_date_format(date_range["from_date"]),
                to_date=_to_site_date_format(date_range["to_date"]),
            )
        else:
            log("preenchendo Date Range...")
            select_combobox(frame, "Date Range", config["date_range_type_text"])

        group_by_option = group_by or config["group_by_option"]
        group_by_type_text = group_by if group_by else config["group_by_type_text"]
        log(f"preenchendo Group By 1 ({group_by_option})...")
        select_combobox(
            frame,
            "Group By 1",
            group_by_type_text,
            option_text=group_by_option,
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
