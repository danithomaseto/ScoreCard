"""Agente local: fica de olho no painel (Vercel), pega as tarefas
pendentes, roda a automacao Playwright (automation/generic.py) e envia o
relatorio de volta para o painel.

Precisa rodar numa maquina com acesso a rede da operacao (VPN da DHL).
Configuracao em .env (veja .env.example): DASHBOARD_URL, APP_TOKEN,
DHL_USERNAME, DHL_PASSWORD.
"""

import os
import time

import requests
from dotenv import load_dotenv

from automation import generic
from config.operations import OPERATIONS

load_dotenv()

DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "").rstrip("/")
APP_TOKEN = os.environ.get("APP_TOKEN")
POLL_INTERVAL_SECONDS = float(os.environ.get("POLL_INTERVAL_SECONDS", "5"))

if not DASHBOARD_URL or not APP_TOKEN:
    raise SystemExit(
        "Configure DASHBOARD_URL e APP_TOKEN no arquivo .env do agente (veja .env.example)."
    )


def auth_headers(extra=None):
    headers = {"Authorization": f"Bearer {APP_TOKEN}"}
    if extra:
        headers.update(extra)
    return headers


def fetch_pending_jobs():
    resp = requests.get(
        f"{DASHBOARD_URL}/api/jobs",
        params={"status": "pending"},
        headers=auth_headers(),
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def claim_job(job_id):
    resp = requests.post(
        f"{DASHBOARD_URL}/api/jobs/{job_id}/claim", headers=auth_headers(), timeout=30
    )
    return resp.ok


def report_failure(job_id, message):
    requests.post(
        f"{DASHBOARD_URL}/api/jobs/{job_id}/complete",
        headers=auth_headers({"Content-Type": "application/json"}),
        json={"status": "failed", "message": message},
        timeout=30,
    )


def upload_result(job_id, file_path, file_name):
    with open(file_path, "rb") as fh:
        data = fh.read()
    resp = requests.post(
        f"{DASHBOARD_URL}/api/jobs/{job_id}/complete",
        params={"filename": file_name},
        headers=auth_headers({"Content-Type": "application/octet-stream"}),
        data=data,
        timeout=120,
    )
    resp.raise_for_status()


def process_job(job):
    operation_key = job["operation"]
    if operation_key not in OPERATIONS:
        print(f"[{job['id']}] Operacao '{operation_key}' nao cadastrada em config/operations.py.")
        report_failure(job["id"], f"Operacao '{operation_key}' nao cadastrada neste agente.")
        return

    print(f"[{job['id']}] Reservando tarefa '{operation_key}'...")
    if not claim_job(job["id"]):
        print(f"[{job['id']}] Nao foi possivel reservar (outro agente pode ja ter pegado).")
        return

    print(f"[{job['id']}] Executando automacao...")
    result = generic.run(operation_key, headless=True)

    if not result.get("success"):
        message = result.get("message", "Falha desconhecida.")
        print(f"[{job['id']}] Falhou: {message}")
        report_failure(job["id"], message)
        return

    file_path = result["file_path"]
    file_name = os.path.basename(file_path)
    print(f"[{job['id']}] Automacao concluida, enviando arquivo para o painel...")
    upload_result(job["id"], file_path, file_name)
    print(f"[{job['id']}] Concluido.")


def poll_once():
    for job in fetch_pending_jobs():
        try:
            process_job(job)
        except Exception as exc:  # noqa: BLE001 - reporta qualquer falha e segue pra proxima tarefa
            print(f"[{job['id']}] Erro inesperado: {exc}")
            try:
                report_failure(job["id"], str(exc))
            except Exception:
                pass


def main():
    print(f"Agente do Score Card rodando. Painel: {DASHBOARD_URL}")
    print(f"Verificando novas tarefas a cada {POLL_INTERVAL_SECONDS:.0f}s. Ctrl+C para parar.")
    while True:
        try:
            poll_once()
        except Exception as exc:  # noqa: BLE001 - nao deixa o loop morrer por falha de rede
            print(f"Erro ao consultar o painel: {exc}")
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
