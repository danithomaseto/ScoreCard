"""Cadastro das operacoes disponiveis para extracao do Score Card.

Todas usam a mesma automacao generica (automation/generic.py): login,
Reports > Reports, abrir o relatorio, aplicar filtros e exportar em
Excel. Para adicionar uma nova operacao, basta uma entrada aqui.

"sharepoint_folder" e o nome exato da subpasta (dentro da pasta do
SharePoint sincronizada via OneDrive) onde o relatorio dessa operacao e
salvo. Precisa bater com o nome da pasta que aparece no SharePoint.
"""

# Opcoes reais do combobox "Group By 1" do Summary, na mesma ordem em
# que aparecem no dropdown do site. Usado pra popular o select da tela
# e como lista de valores validos vindos da UI.
GROUP_BY_OPTIONS = [
    "Aisle Area",
    "Aisle Area Desc.",
    "Client",
    "Customer",
    "Fiscal Month",
    "Fiscal Week",
    "Job Code",
    "Job Code Desc.",
    "Learning Curve",
    "Month",
    "Observation State",
    "Reference ID",
    "Report By Hour",
    "Report Date",
    "Report Group",
    "Route Number",
    "Shift",
    "Shift Category",
    "Supervisor",
    "User",
    "User Group",
    "User ID",
    "User Name",
    "User Pin",
    "Warehouse",
    "Week",
    "Work Area",
    "Work Category",
    "Work Team",
]

# Opcao do "Date Range" (bloco "Default Date Range" do relatorio) usada
# quando nao se digita um intervalo na tela. O nome vai completo de
# proposito: digitar so um pedaco ("Las") deixaria o combobox escolher
# a primeira opcao que sobrar na lista, que pode ser Last Week, Last
# Month ou Last Year conforme o relatorio.
DEFAULT_DATE_RANGE = {
    "week": "Last Week",
    "month": "Last Month",
}

# "escala_espanhola": a operacao trabalha os dois ultimos sabados de cada
# mes (e folga os primeiros). Esses sabados contam como dia util no
# presenteismo e podem entrar nos dias de pico. Domingo nunca entra.
OPERATIONS = {
    "hugo_boss": {
        "label": "Hugo Boss",
        "login_url": "https://czcholspc003138.prg-dc.dhl.com:11217/rp/login",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Hugo Boss",
    },
    "hughes": {
        "label": "Hughes",
        "login_url": "https://czcholspc003008.prg-dc.dhl.com:11205/portal?siteId=CST#Menu-DEawt68KTrSaeNwjNA6mGg/reporting-ReportOpr////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Hughes",
    },
    "swa": {
        "label": "Swa",
        "login_url": "https://czcholspc003008.prg-dc.dhl.com:11205/portal?siteId=WH02#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "SWA",
    },
    "nike_fisia": {
        "label": "Nike/Fisia",
        "login_url": "https://czcholspc000211.prg-dc.dhl.com:11217/portal?siteId=LOU#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Nike",
        "escala_espanhola": True,
    },
    "sumup": {
        "label": "Sumup",
        "login_url": "https://czcholspc002995.prg-dc.dhl.com:11205/portal?siteId=BR_0087&subsite=BR_5041_RED#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "SumUp",
    },
    "rede": {
        "label": "Rede",
        "login_url": "https://czcholspc002995.prg-dc.dhl.com:11205/portal?siteId=BR_5041_RED&subsite=BR_5041_RED#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Rede",
        "escala_espanhola": True,
    },
    "jcb": {
        "label": "JCB",
        "login_url": "https://czcholspc002995.prg-dc.dhl.com:11205/portal?siteId=BR_5041_JCB&subsite=BR_5041_RED#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "JCB",
        "escala_espanhola": True,
    },
    "lego": {
        "label": "Lego",
        "login_url": "https://czcholspc001643.prg-dc.dhl.com:11213/portal?siteId=BR_0087_1#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Lego",
    },
    "spacex": {
        "label": "SpaceX",
        "login_url": "https://czcholspc001643.prg-dc.dhl.com:11213/portal?siteId=BR_0087_8#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "SpaceX",
    },
    "hpe": {
        "label": "HPE",
        "login_url": "https://czcholspc001643.prg-dc.dhl.com:11213/portal?siteId=BR_0087_5#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "HPE",
        "escala_espanhola": True,
    },
    "armani": {
        "label": "Armani",
        "login_url": "https://czcholspc001643.prg-dc.dhl.com:11213/portal?siteId=BR_5039#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "Armani",
    },
    "abb": {
        "label": "ABB",
        "login_url": "https://czcholspc001643.prg-dc.dhl.com:11213/portal?siteId=BR_0087_3#Menu-DEawt68KTrSaeNwjNA6mGg/mcs-Users////",
        "username_env": "DHL_USERNAME",
        "password_env": "DHL_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
        "sharepoint_folder": "ABB",
    },
}


def escala_espanhola(operation_key):
    return bool(OPERATIONS.get(operation_key, {}).get("escala_espanhola"))
