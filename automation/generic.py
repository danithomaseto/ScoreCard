import logging
import os
import time
from datetime import date, datetime, timedelta

from automation.base import (
    enable_second_grouping,
    export_report,
    get_report_frame,
    login,
    open_report,
    open_reports_menu,
    select_combobox,
    select_custom_date_range,
    select_default_date_range,
    Navegador,
    take_screenshot,
)
from config.operations import DEFAULT_DATE_RANGE, OPERATIONS

# Tipo de extracao -> subpasta da operacao onde o arquivo e salvo. Os
# nomes precisam bater com as pastas do SharePoint.
PASTAS_DO_PERIODO = {
    "week": "Week",
    "month": "Month",
    "peak": "Dias de Pico",
}

# Dias de pico: uma linha por dia do mes, sem quebra por pessoa — so a
# hora direta sai daqui; efetividade e dispersao vem do mensal.
GROUP_BY_DO_PICO = "Report Date"

registro = logging.getLogger("scorecard.automacao")


def _to_site_date_format(iso_date):
    """Converte yyyy-mm-dd (formato do <input type="date"> do navegador)
    pro formato dd/mm/yyyy que o campo do Summary espera."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")


def _month_key(date_range, hoje=None):
    """Chave do mes (2026-09) no arquivo de indicadores.

    O export mensal nao traz coluna de data nenhuma — o unico
    agrupamento e o User ID —, entao o mes vem de quem pediu a
    extracao: do intervalo digitado, ou do mes anterior quando se usa o
    "Last Month" do relatorio.
    """
    if date_range:
        return date_range["from_date"][:7]
    hoje = hoje or date.today()
    ultimo_dia_do_mes_anterior = hoje.replace(day=1) - timedelta(days=1)
    return ultimo_dia_do_mes_anterior.strftime("%Y-%m")


def run(
    operation_key,
    base_dir,
    headless=True,
    username=None,
    password=None,
    on_progress=None,
    date_range=None,
    group_by=None,
    period=None,
    navegador=None,
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
    no lugar do padrao "User ID" da operacao. period ("week", "month" ou
    "peak") define em qual subpasta da operacao o arquivo e salvo -
    "Week", "Month" ou "Dias de Pico" (PASTAS_DO_PERIODO). No pico o
    Group By 1 e sempre Report Date, e o escolhido na tela e ignorado.
    navegador, se informado, e um Navegador ja
    aberto (fila do Extrair Multiplos): a operacao usa uma sessao nova
    dele e nao o fecha no fim.
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

    tipo = (period or "week").lower()
    if tipo not in PASTAS_DO_PERIODO:
        tipo = "week"
    period_folder = PASTAS_DO_PERIODO[tipo]

    folder = config.get("sharepoint_folder") or config["label"]
    download_dir = os.path.join(base_dir, folder, period_folder)

    is_month = tipo == "month"
    is_peak = tipo == "peak"
    # O pico e do mes do calendario: sem datas digitadas, "Last Month".
    default_range = DEFAULT_DATE_RANGE["week" if tipo == "week" else "month"]

    if date_range:
        period_label = (
            f"{_to_site_date_format(date_range['from_date'])} - "
            f"{_to_site_date_format(date_range['to_date'])}"
        )
        origem = "digitado"
    else:
        period_label = default_range
        origem = default_range.lower().replace(" ", "_")
    group_by_option = GROUP_BY_DO_PICO if is_peak else (group_by or config["group_by_option"])

    def log(step):
        print(f"[{operation_key}] {step}", flush=True)
        registro.info("[%s] %s", operation_key, step)
        if on_progress:
            try:
                on_progress(step)
            except Exception:
                pass  # nunca deixa um erro de UI derrubar a automacao

    start_time = time.monotonic()
    proprio = navegador is None
    if proprio:
        log("abrindo o navegador...")
        navegador = Navegador(headless=headless)
    else:
        log("abrindo uma sessao nova no navegador...")
    page = navegador.nova_pagina()
    result = {
        "operation": operation_key,
        "operation_label": config["label"],
        "period_label": period_label,
        # E sempre o nivel de detalhe (uma linha por pessoa quando e
        # User ID): Group By 2 na semana, Group By 1 no mes.
        "group_by": group_by_option,
        "period_type": period_folder,
        "origem": origem,
        "date_from": date_range["from_date"] if date_range else None,
        "date_to": date_range["to_date"] if date_range else None,
        "month_key": _month_key(date_range) if (is_month or is_peak) else None,
    }

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
            log(f"preenchendo Date Range ({default_range})...")
            select_default_date_range(frame, default_range)

        if is_month or is_peak:
            # O mensal vem consolidado (e o pico, por dia): um nivel so, sem quebra por
            # semana. Uma linha por pessoa com os totais do periodo.
            log(f"preenchendo Group By 1 ({group_by_option})...")
            select_combobox(frame, "Group By 1", group_by_option, option_text=group_by_option)
        else:
            # Semanal: a quebra por semana fica fixa no primeiro nivel e
            # o campo escolhido na tela vai pro segundo.
            log("preenchendo Group By 1 (Week)...")
            select_combobox(frame, "Group By 1", "Week", option_text="Week")

            log("marcando o segundo nivel de agrupamento...")
            enable_second_grouping(frame)

            log(f"preenchendo Group By 2 ({group_by_option})...")
            select_combobox(frame, "Group By 2", group_by_option, option_text=group_by_option)

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
        try:
            page.context.close()
        except Exception:
            pass
        if proprio:
            navegador.fechar()

    result["duration_seconds"] = round(time.monotonic() - start_time, 1)
    return result
