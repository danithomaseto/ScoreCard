"""Funcoes reutilizaveis de automacao de login (Playwright).

Pensado para ser reaproveitado por todas as operacoes: cada uma so
precisa informar a URL de login e as credenciais.
"""

import os
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")


def _fill_first_match(page, selectors, value):
    for selector in selectors:
        try:
            locator = selector(page)
            locator.wait_for(state="visible", timeout=4000)
            locator.fill(value)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def _click_first_match(page, selectors):
    for selector in selectors:
        try:
            locator = selector(page)
            locator.wait_for(state="visible", timeout=4000)
            locator.click()
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def login_with_user_password(login_url, username, password, operation_key, headless=True):
    """Abre a pagina de login, preenche usuario/senha e clica em Sign In.

    Retorna um dict com o resultado, incluindo o caminho de um screenshot
    tirado apos a tentativa (util para conferir o resultado sem precisar
    estar na rede da operacao).
    """
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = os.path.join(SCREENSHOT_DIR, f"{operation_key}_{timestamp}.png")

    username_selectors = [
        lambda p: p.get_by_label("Username", exact=False),
        lambda p: p.locator("input[name='Username' i]"),
        lambda p: p.locator("input[id='Username' i]"),
        lambda p: p.get_by_placeholder("Username", exact=False),
    ]
    password_selectors = [
        lambda p: p.get_by_label("Password", exact=False),
        lambda p: p.locator("input[name='Password' i]"),
        lambda p: p.locator("input[id='Password' i]"),
        lambda p: p.get_by_placeholder("Password", exact=False),
        lambda p: p.locator("input[type='password']"),
    ]
    sign_in_selectors = [
        lambda p: p.get_by_role("button", name="Sign In", exact=False),
        lambda p: p.get_by_role("button", name="Sign in", exact=False),
        lambda p: p.locator("button:has-text('Sign In')"),
        lambda p: p.locator("input[type='submit']"),
    ]

    launch_kwargs = {"headless": headless}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(**launch_kwargs)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()
        result = {"operation": operation_key, "screenshot": screenshot_path}

        try:
            page.goto(login_url, wait_until="load", timeout=30000)

            if not _fill_first_match(page, username_selectors, username):
                raise RuntimeError("Nao foi possivel localizar o campo Username na pagina.")

            if not _fill_first_match(page, password_selectors, password):
                raise RuntimeError("Nao foi possivel localizar o campo Password na pagina.")

            if not _click_first_match(page, sign_in_selectors):
                raise RuntimeError("Nao foi possivel localizar o botao Sign In na pagina.")

            page.wait_for_load_state("networkidle", timeout=15000)

            result["success"] = True
            result["message"] = "Login realizado (verifique o screenshot para confirmar)."
            result["final_url"] = page.url
        except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha da automacao
            result["success"] = False
            result["message"] = str(exc)
            result["final_url"] = page.url
        finally:
            page.screenshot(path=screenshot_path, full_page=True)
            context.close()
            browser.close()

        return result
