"""Cadastro das operacoes disponiveis para extracao do Score Card.

Para adicionar uma nova operacao no futuro:
1. Adicione uma entrada no dicionario OPERATIONS abaixo com o link de login.
2. Adicione as variaveis de usuario/senha correspondentes no .env (e no .env.example).
3. Crie o modulo de automacao em automation/<operacao>.py seguindo o
   padrao de automation/hugo_boss.py.
"""

OPERATIONS = {
    "hugo_boss": {
        "label": "Hugo Boss",
        "login_url": "https://czcholspc003138.prg-dc.dhl.com:11217/rp/login",
        "username_env": "HUGO_BOSS_USERNAME",
        "password_env": "HUGO_BOSS_PASSWORD",
        "report_name": "rptLMUserSummaryRaw",
        "date_range_option": "Last Week",
        "group_by_option": "User ID",
        "export_format": "EXCEL",
    },
}
