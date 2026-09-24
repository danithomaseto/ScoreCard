"""Testes dos filtros do Summary contra a pagina de mock.

Os testes de automacao cobrem o fluxo inteiro, mas nao olham **o que**
ficou selecionado nos campos. Aqui os helpers sao chamados direto na
pagina, e o que se confere e o valor que sobrou em cada filtro — que e
o que define se o relatorio extraido e o certo.
"""

import pytest

from automation.base import (
    enable_second_grouping,
    open_browser_session,
    select_combobox,
    select_default_date_range,
)
from conftest import fixture_url


@pytest.fixture
def report_page():
    playwright, browser, page = open_browser_session(headless=True)
    page.goto(fixture_url("report.html"))
    yield page
    page.context.close()
    browser.close()
    playwright.stop()


def valor(page, campo):
    return page.locator(campo).input_value()


def test_default_date_range_escolhe_a_opcao_exata(report_page):
    """O codigo antigo digitava so "Las" e confirmava com Enter, o que
    pegava a primeira da lista — podia ser Last Month, Last Week ou
    Last Year conforme o que o relatorio oferecesse."""
    select_default_date_range(report_page, "Last Month")

    assert valor(report_page, "#dateRange") == "Last Month"
    assert report_page.locator("#defaultdaterange_radio-inputEl").is_checked()


def test_default_date_range_last_week(report_page):
    select_default_date_range(report_page, "Last Week")

    assert valor(report_page, "#dateRange") == "Last Week"


def test_segundo_nivel_habilita_o_group_by_2(report_page):
    assert report_page.locator("#groupBy2").is_disabled()

    enable_second_grouping(report_page)

    assert report_page.locator("#groupinglvl2_check-inputEl").is_checked()
    assert report_page.locator("#groupBy2").is_enabled()


def test_marcar_o_segundo_nivel_duas_vezes_nao_desmarca(report_page):
    """O checkbox guarda estado entre execucoes: um clique cego no que
    ja esta marcado desmarcaria e o Group By 2 ficaria inacessivel."""
    enable_second_grouping(report_page)
    enable_second_grouping(report_page)

    assert report_page.locator("#groupinglvl2_check-inputEl").is_checked()
    assert report_page.locator("#groupBy2").is_enabled()


def test_semana_fixa_week_no_primeiro_nivel_e_a_escolha_no_segundo(report_page):
    select_combobox(report_page, "Group By 1", "Week", option_text="Week")
    enable_second_grouping(report_page)
    select_combobox(report_page, "Group By 2", "User ID", option_text="User ID")

    assert valor(report_page, "#groupBy") == "Week"
    assert valor(report_page, "#groupBy2") == "User ID"


def test_group_by_2_aceita_qualquer_opcao_da_lista(report_page):
    enable_second_grouping(report_page)
    select_combobox(report_page, "Group By 2", "Work Team", option_text="Work Team")

    assert valor(report_page, "#groupBy2") == "Work Team"
