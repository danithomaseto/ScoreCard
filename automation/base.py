"""Funcoes reutilizaveis de automacao (Playwright): login, navegacao no menu
de relatorios e exportacao. Pensado para ser reaproveitado por todas as
operacoes: cada uma so precisa informar URL, credenciais e os parametros do
relatorio (config/operations.py).
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


def _click_first_match(page, selectors, timeout=4000):
    for selector in selectors:
        try:
            locator = selector(page)
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def open_browser_session(headless=True):
    """Abre o Playwright, o browser e um context com download habilitado.

    Retorna (playwright, browser, page). Quem chamar e responsavel por
    fechar context/browser/playwright ao final.
    """
    launch_kwargs = {"headless": headless}
    if os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE"):
        launch_kwargs["executable_path"] = os.environ["PLAYWRIGHT_CHROMIUM_EXECUTABLE"]

    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(**launch_kwargs)
    context = browser.new_context(ignore_https_errors=True, accept_downloads=True)
    page = context.new_page()
    return playwright, browser, page


def take_screenshot(page, operation_key, suffix="falha"):
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"{operation_key}_{suffix}_{timestamp}.png")
    try:
        page.screenshot(path=path, full_page=True)
        return path
    except Exception:
        return None


def login(page, login_url, username, password):
    """Abre a pagina de login e preenche usuario/senha/Sign In."""
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

    page.goto(login_url, wait_until="load", timeout=30000)

    if not _fill_first_match(page, username_selectors, username):
        raise RuntimeError("Nao foi possivel localizar o campo Username na pagina de login.")

    if not _fill_first_match(page, password_selectors, password):
        raise RuntimeError("Nao foi possivel localizar o campo Password na pagina de login.")

    if not _click_first_match(page, sign_in_selectors):
        raise RuntimeError("Nao foi possivel localizar o botao Sign In na pagina de login.")

    page.wait_for_load_state("networkidle", timeout=15000)


def open_reports_menu(page):
    """Clica na aba 'Reports' do menu superior e depois no item 'Reports'
    do submenu que aparece."""
    reports_items = page.get_by_text("Reports", exact=True)

    if reports_items.count() == 0:
        raise RuntimeError("Nao foi possivel localizar a aba Reports no menu superior.")

    reports_items.first.click()
    page.wait_for_timeout(500)

    reports_items = page.get_by_text("Reports", exact=True)
    if reports_items.count() > 1:
        reports_items.nth(1).click()

    page.wait_for_load_state("networkidle", timeout=15000)


def open_report(page, report_name):
    """Clica no link do relatorio (ex: rptLMUserSummaryRaw) na lista de
    Operations."""
    link_selectors = [
        lambda p: p.get_by_role("link", name=report_name, exact=True),
        lambda p: p.locator(f"a:has-text('{report_name}')"),
    ]
    if not _click_first_match(page, link_selectors, timeout=8000):
        raise RuntimeError(f"Nao foi possivel localizar o relatorio '{report_name}' na lista.")

    page.wait_for_load_state("networkidle", timeout=15000)


def select_dropdown(page, label, option_text):
    """Seleciona 'option_text' num campo identificado por 'label'.

    Tenta, em ordem: <select> nativo associado ao label, <select> logo
    apos o texto do label, e por ultimo um dropdown customizado (clica
    para abrir e depois clica na opcao pelo texto).
    """
    try:
        select_el = page.get_by_label(label, exact=False)
        select_el.wait_for(state="visible", timeout=3000)
        select_el.select_option(label=option_text)
        return
    except Exception:
        pass

    label_locator = page.get_by_text(label, exact=False).first

    try:
        select_el = label_locator.locator("xpath=following::select[1]")
        select_el.wait_for(state="visible", timeout=3000)
        select_el.select_option(label=option_text)
        return
    except Exception:
        pass

    try:
        opener = label_locator.locator(
            "xpath=following::*[self::button or self::input or self::div][1]"
        )
        opener.click(timeout=3000)
        page.get_by_text(option_text, exact=True).click(timeout=3000)
        return
    except Exception as exc:
        raise RuntimeError(
            f"Nao foi possivel selecionar '{option_text}' no campo '{label}': {exc}"
        )


def export_report(page, download_dir, operation_key, export_format="EXCEL"):
    """Clica em Export, escolhe o formato e salva o arquivo baixado em
    download_dir. Retorna o caminho completo do arquivo salvo."""
    export_button_selectors = [
        lambda p: p.get_by_role("button", name="Export", exact=True),
        lambda p: p.locator("button:has-text('Export')"),
    ]
    if not _click_first_match(page, export_button_selectors, timeout=8000):
        raise RuntimeError("Nao foi possivel localizar o botao Export na pagina do relatorio.")

    format_selectors = [
        lambda p: p.get_by_label(export_format, exact=False),
        lambda p: p.locator(f"label:has-text('{export_format}')"),
        lambda p: p.get_by_text(export_format, exact=True),
    ]
    if not _click_first_match(page, format_selectors, timeout=5000):
        raise RuntimeError(f"Nao foi possivel selecionar o formato {export_format} na tela de exportacao.")

    ok_selectors = [
        lambda p: p.get_by_role("button", name="Ok", exact=True),
        lambda p: p.get_by_role("button", name="OK", exact=True),
    ]

    with page.expect_download(timeout=60000) as download_info:
        if not _click_first_match(page, ok_selectors, timeout=5000):
            raise RuntimeError("Nao foi possivel localizar o botao Ok na tela de exportacao.")

    download = download_info.value

    os.makedirs(download_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = os.path.splitext(download.suggested_filename)[1] or ".xlsx"
    filename = f"ScoreCard_{operation_key}_{timestamp}{extension}"
    dest_path = os.path.join(download_dir, filename)
    download.save_as(dest_path)
    return dest_path
