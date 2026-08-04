"""Funcoes reutilizaveis de automacao (Playwright): login, navegacao no
menu de relatorios e exportacao. Pensado para ser reaproveitado por todas
as operacoes: cada uma so precisa informar URL, credenciais e os
parametros do relatorio (config/operations.py).

O portal Hugo Boss (BlueYonder RP) carrega a area de relatorios dentro de
um <iframe> cujo nome muda a cada sessao (tem um token/timestamp), entao
localizamos o frame por um trecho fixo do nome em vez do nome completo.
"""

import os
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "screenshots")


def _fill_first_match(target, selectors, value):
    for selector in selectors:
        try:
            locator = selector(target)
            locator.wait_for(state="visible", timeout=4000)
            locator.fill(value)
            return True
        except PlaywrightTimeoutError:
            continue
    return False


def _click_first_match(target, selectors, timeout=4000):
    for selector in selectors:
        try:
            locator = selector(target)
            locator.wait_for(state="visible", timeout=timeout)
            locator.click()
            return True
        except PlaywrightTimeoutError:
            continue
        except Exception:
            # Ex.: "strict mode violation" quando o seletor bate em mais
            # de um elemento. Tenta o proximo seletor em vez de travar.
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
    """Abre a pagina de login, preenche usuario/senha e confirma o Sign In.

    Segue a mesma sequencia gravada com o Playwright Codegen no site real
    (inclui um Tab depois do usuario, que alguns formularios exigem para
    validar o campo antes do proximo passo). Depois confirma que a
    navegacao realmente aconteceu.
    """
    username_selectors = [
        lambda p: p.get_by_role("textbox", name="Username", exact=False),
        lambda p: p.get_by_label("Username", exact=False),
        lambda p: p.locator("input[name='Username' i]"),
        lambda p: p.locator("input[id='Username' i]"),
    ]
    password_selectors = [
        lambda p: p.get_by_role("textbox", name="Password", exact=False),
        lambda p: p.get_by_label("Password", exact=False),
        lambda p: p.locator("input[name='Password' i]"),
        lambda p: p.locator("input[type='password']"),
    ]
    sign_in_selectors = [
        lambda p: p.get_by_role("button", name="Sign In", exact=False),
        lambda p: p.locator("#loginButton"),
        lambda p: p.locator("input[value='Sign In' i]"),
        lambda p: p.locator("button:has-text('Sign In')"),
    ]

    page.goto(login_url, wait_until="load", timeout=30000)

    if not _fill_first_match(page, username_selectors, username):
        raise RuntimeError("Nao foi possivel localizar o campo Username na pagina de login.")

    try:
        page.keyboard.press("Tab")
    except Exception:
        pass

    if not _fill_first_match(page, password_selectors, password):
        raise RuntimeError("Nao foi possivel localizar o campo Password na pagina de login.")

    if not _click_first_match(page, sign_in_selectors):
        raise RuntimeError("Nao foi possivel localizar o botao Sign In na pagina de login.")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    still_on_login = False
    for selector in username_selectors:
        try:
            if selector(page).is_visible(timeout=1000):
                still_on_login = True
                break
        except Exception:
            continue

    if still_on_login:
        raise RuntimeError(
            "Cliquei em Sign In, mas a tela continua sendo a de login (o campo "
            "Username ainda esta visivel). Confira o screenshot."
        )


def open_reports_menu(page):
    """Clica na aba 'Reports' do menu superior."""
    reports_items = page.get_by_text("Reports", exact=True)

    if reports_items.count() == 0:
        raise RuntimeError("Nao foi possivel localizar a aba Reports no menu superior.")

    reports_items.first.click()
    page.wait_for_timeout(500)

    # Alguns layouts mostram um segundo item "Reports" num submenu.
    reports_items = page.get_by_text("Reports", exact=True)
    if reports_items.count() > 1:
        try:
            reports_items.nth(1).click(timeout=2000)
        except Exception:
            pass


def get_report_frame(page, name_contains="reporting-ReportOpr", timeout=15000):
    """Localiza o iframe onde a area de relatorios e carregada. O nome do
    iframe muda a cada sessao (tem um token/timestamp), entao procuramos
    por um trecho fixo do nome."""
    selector = f"iframe[name*='{name_contains}']"
    page.wait_for_selector(selector, timeout=timeout)
    return page.frame_locator(selector).first


def open_report(frame, report_name):
    """Clica no link do relatorio (ex: rptLMUserSummaryRaw) na lista de
    Operations, dentro do iframe de relatorios."""
    link_selectors = [
        lambda f: f.get_by_text(report_name, exact=True),
        lambda f: f.get_by_role("link", name=report_name, exact=True),
        lambda f: f.locator(f"a:has-text('{report_name}')"),
    ]
    if not _click_first_match(frame, link_selectors, timeout=8000):
        raise RuntimeError(f"Nao foi possivel localizar o relatorio '{report_name}' na lista.")


def select_combobox(frame, label, type_text, option_text=None):
    """Preenche um combobox ExtJS: clica pra abrir, digita um trecho do
    valor tecla por tecla e confirma (Enter, ou clicando na opcao que
    aparecer).

    Muitos comboboxes ExtJS classicos so disparam a busca/filtro no
    evento de tecla (keyup/keydown) do campo. O Locator.fill() do
    Playwright NAO dispara esses eventos de teclado (so 'input' e
    'change'), entao o dropdown de opcoes nunca aparece. Por isso aqui
    usamos digitacao caractere a caractere (press_sequentially/type).
    """
    combo_selectors = [
        lambda f: f.get_by_role("combobox", name=label, exact=False),
    ]
    if not _click_first_match(frame, combo_selectors, timeout=5000):
        raise RuntimeError(f"Nao foi possivel abrir o campo '{label}'.")

    combo = frame.get_by_role("combobox", name=label, exact=False)

    try:
        combo.fill("")
    except Exception:
        pass

    try:
        if hasattr(combo, "press_sequentially"):
            combo.press_sequentially(type_text, delay=120)
        else:
            combo.type(type_text, delay=120)
    except Exception as exc:
        raise RuntimeError(f"Nao foi possivel digitar em '{label}': {exc}")

    if option_text:
        try:
            combo.page.wait_for_timeout(400)
        except Exception:
            pass
        option_selectors = [
            lambda f: f.get_by_role("option", name=option_text, exact=True),
        ]
        if not _click_first_match(frame, option_selectors, timeout=6000):
            raise RuntimeError(f"Nao foi possivel selecionar a opcao '{option_text}' em '{label}'.")
    else:
        try:
            combo.press("Enter")
        except Exception as exc:
            raise RuntimeError(f"Nao foi possivel confirmar '{label}' com Enter: {exc}")


def export_report(page, frame, download_dir, operation_key, export_format="EXCEL"):
    """Clica em Export, escolhe o formato e salva o arquivo baixado em
    download_dir. Retorna o caminho completo do arquivo salvo."""
    export_button_selectors = [
        lambda f: f.get_by_role("button", name="Export", exact=True),
        lambda f: f.get_by_text("Export", exact=True),
        lambda f: f.locator("#button-1128"),
    ]
    if not _click_first_match(frame, export_button_selectors, timeout=8000):
        raise RuntimeError("Nao foi possivel localizar o botao Export na pagina do relatorio.")

    format_selectors = [
        lambda f: f.get_by_label(export_format, exact=False),
        lambda f: f.locator(f"label:has-text('{export_format}')"),
        lambda f: f.get_by_text(export_format, exact=True),
    ]
    if not _click_first_match(frame, format_selectors, timeout=5000):
        raise RuntimeError(f"Nao foi possivel selecionar o formato {export_format} na tela de exportacao.")

    ok_selectors = [
        lambda f: f.get_by_role("button", name="Ok", exact=True),
        lambda f: f.get_by_text("Ok", exact=True),
        lambda f: f.locator("#button-1224"),
    ]

    with page.expect_download(timeout=60000) as download_info:
        if not _click_first_match(frame, ok_selectors, timeout=5000):
            raise RuntimeError("Nao foi possivel localizar o botao Ok na tela de exportacao.")

    download = download_info.value

    os.makedirs(download_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = os.path.splitext(download.suggested_filename)[1] or ".xlsx"
    filename = f"ScoreCard_{operation_key}_{timestamp}{extension}"
    dest_path = os.path.join(download_dir, filename)
    download.save_as(dest_path)
    return dest_path
