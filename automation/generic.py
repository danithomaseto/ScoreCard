import logging
import os
import time
from datetime import date, datetime, timedelta

from automation.base import (
    disable_grouping_level,
    enable_grouping_level,
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
from config.operations import (
    DEFAULT_DATE_RANGE, OPERATIONS, PASTAS_DO_PERIODO, ROTULOS_DO_PERIODO, agrupamento, e_semanal,
)

# Quantos niveis de Group By o relatorio tem.
NIVEIS_DO_RELATORIO = 3

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

    period define o tipo de extracao, o agrupamento e a subpasta da
    operacao onde o arquivo e salvo (config.operations: AGRUPAMENTOS e
    PASTAS_DO_PERIODO): "week" (Week > Supervisor > User ID), "month",
    "peak" (Report Date), "indiretas" (Week > Job Code) e os de Gestor e
    Turno, com Week e Month cada um. group_by, o texto exato de uma das
    opcoes de "Group By 1" (config.operations.GROUP_BY_OPTIONS), so vale
    no Month, no lugar do padrao "User ID" da operacao; nos outros tipos
    o agrupamento e fixo, venha o que vier da tela.

    navegador, se informado, e um Navegador ja aberto (fila do Extrair
    Multiplos): a operacao usa uma sessao nova dele e nao o fecha no fim.
    """
    config = OPERATIONS[operation_key]

    if not username or not password:
        return {
            "operation": operation_key,
            "success": False,
            "message": "Credenciais não informadas. Faça login novamente.",
        }

    if not base_dir or not os.path.isdir(base_dir):
        return {
            "operation": operation_key,
            "success": False,
            "message": f"A pasta configurada não existe ou não foi definida: {base_dir}",
        }

    tipo = (period or "week").lower()
    if tipo not in PASTAS_DO_PERIODO:
        tipo = "week"
    period_folder = PASTAS_DO_PERIODO[tipo]

    folder = config.get("sharepoint_folder") or config["label"]
    # "Gestor/Week" vira duas pastas, uma dentro da outra.
    download_dir = os.path.join(base_dir, folder, *period_folder.split("/"))

    semanal = e_semanal(tipo)
    # Sem Week no agrupamento o export nao traz data nenhuma: o mes vem
    # de quem pediu a extracao. O pico e do mes do calendario.
    default_range = DEFAULT_DATE_RANGE["week" if semanal else "month"]

    if date_range:
        period_label = (
            f"{_to_site_date_format(date_range['from_date'])} - "
            f"{_to_site_date_format(date_range['to_date'])}"
        )
        origem = "digitado"
    else:
        period_label = default_range
        origem = default_range.lower().replace(" ", "_")
    niveis = agrupamento(tipo, group_by, config["group_by_option"])

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
        log("abrindo uma sessão nova no navegador...")
    page = navegador.nova_pagina()
    result = {
        "operation": operation_key,
        "operation_label": config["label"],
        "period_label": period_label,
        # E sempre o nivel de detalhe (uma linha por pessoa quando e
        # User ID): o ultimo Group By.
        "group_by": niveis[-1],
        "agrupamento": " › ".join(niveis),
        "tipo": tipo,
        "period_type": ROTULOS_DO_PERIODO[tipo],
        "origem": origem,
        "date_from": date_range["from_date"] if date_range else None,
        "date_to": date_range["to_date"] if date_range else None,
        "month_key": None if semanal else _month_key(date_range),
    }

    try:
        log("fazendo login...")
        login(page, config["login_url"], username, password)

        log("login OK, abrindo menu Reports...")
        open_reports_menu(page)

        log("localizando o iframe de relatórios...")
        frame = get_report_frame(page)

        log(f"abrindo o relatório '{config['report_name']}'...")
        open_report(frame, config["report_name"])

        if date_range:
            log(f"selecionando período específico ({date_range['from_date']} a {date_range['to_date']})...")
            select_custom_date_range(
                frame,
                from_date=_to_site_date_format(date_range["from_date"]),
                to_date=_to_site_date_format(date_range["to_date"]),
            )
        else:
            log(f"preenchendo Date Range ({default_range})...")
            select_default_date_range(frame, default_range)

        # Um Group By por nivel, do primeiro ao ultimo. Os niveis que nao
        # entram sao desmarcados: o relatorio guarda o que ficou marcado
        # da extracao anterior.
        for nivel in range(NIVEIS_DO_RELATORIO, len(niveis), -1):
            disable_grouping_level(frame, nivel)
        for nivel, campo in enumerate(niveis, start=1):
            if nivel > 1:
                log(f"marcando o {'segundo' if nivel == 2 else 'terceiro'} nível de agrupamento...")
                enable_grouping_level(frame, nivel)
            log(f"preenchendo Group By {nivel} ({campo})...")
            select_combobox(frame, f"Group By {nivel}", campo, option_text=campo)

        log("exportando e baixando o arquivo...")
        saved_path = export_report(
            page,
            frame,
            download_dir,
            operation_key=operation_key,
            export_format=config["export_format"],
        )

        log(f"concluído: {saved_path}")
        result["success"] = True
        result["message"] = f"Relatório salvo em {saved_path}"
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
