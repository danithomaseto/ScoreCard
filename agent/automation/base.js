// Funcoes reutilizaveis de automacao (Playwright): login, navegacao no
// menu de relatorios e exportacao. Pensado para ser reaproveitado por
// todas as operacoes: cada uma so precisa informar URL, credenciais e os
// parametros do relatorio (config/operations.js).

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const SCREENSHOT_DIR = path.join(__dirname, '..', 'screenshots');

async function fillFirstMatch(page, selectors, value) {
  for (const selector of selectors) {
    try {
      const locator = selector(page);
      await locator.waitFor({ state: 'visible', timeout: 4000 });
      await locator.fill(value);
      return true;
    } catch (err) {
      // tenta o proximo seletor
    }
  }
  return false;
}

async function clickFirstMatch(page, selectors, timeout = 4000) {
  for (const selector of selectors) {
    try {
      const locator = selector(page);
      await locator.waitFor({ state: 'visible', timeout });
      await locator.click();
      return true;
    } catch (err) {
      // tenta o proximo seletor
    }
  }
  return false;
}

async function openBrowserSession(headless = true) {
  const launchOptions = { headless };
  if (process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE) {
    launchOptions.executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
  }
  const browser = await chromium.launch(launchOptions);
  const context = await browser.newContext({ ignoreHTTPSErrors: true, acceptDownloads: true });
  const page = await context.newPage();
  return { browser, context, page };
}

async function takeScreenshot(page, operationKey, suffix = 'falha') {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const filePath = path.join(SCREENSHOT_DIR, `${operationKey}_${suffix}_${timestamp}.png`);
  try {
    await page.screenshot({ path: filePath, fullPage: true });
    return filePath;
  } catch (err) {
    return null;
  }
}

async function login(page, loginUrl, username, password) {
  const usernameSelectors = [
    (p) => p.getByLabel('Username', { exact: false }),
    (p) => p.locator("input[name='Username' i]"),
    (p) => p.locator("input[id='Username' i]"),
    (p) => p.getByPlaceholder('Username', { exact: false }),
  ];
  const passwordSelectors = [
    (p) => p.getByLabel('Password', { exact: false }),
    (p) => p.locator("input[name='Password' i]"),
    (p) => p.locator("input[id='Password' i]"),
    (p) => p.getByPlaceholder('Password', { exact: false }),
    (p) => p.locator("input[type='password']"),
  ];
  const signInSelectors = [
    (p) => p.getByRole('button', { name: 'Sign In', exact: false }),
    (p) => p.getByRole('button', { name: 'Sign in', exact: false }),
    (p) => p.locator("button:has-text('Sign In')"),
    (p) => p.locator("input[type='submit']"),
  ];

  await page.goto(loginUrl, { waitUntil: 'load', timeout: 30000 });

  if (!(await fillFirstMatch(page, usernameSelectors, username))) {
    throw new Error('Nao foi possivel localizar o campo Username na pagina de login.');
  }
  if (!(await fillFirstMatch(page, passwordSelectors, password))) {
    throw new Error('Nao foi possivel localizar o campo Password na pagina de login.');
  }
  if (!(await clickFirstMatch(page, signInSelectors))) {
    throw new Error('Nao foi possivel localizar o botao Sign In na pagina de login.');
  }

  await page.waitForLoadState('networkidle', { timeout: 15000 });
}

async function openReportsMenu(page) {
  let reportsItems = page.getByText('Reports', { exact: true });
  if ((await reportsItems.count()) === 0) {
    throw new Error('Nao foi possivel localizar a aba Reports no menu superior.');
  }

  await reportsItems.first().click();
  await page.waitForTimeout(500);

  reportsItems = page.getByText('Reports', { exact: true });
  if ((await reportsItems.count()) > 1) {
    await reportsItems.nth(1).click();
  }

  await page.waitForLoadState('networkidle', { timeout: 15000 });
}

async function openReport(page, reportName) {
  const linkSelectors = [
    (p) => p.getByRole('link', { name: reportName, exact: true }),
    (p) => p.locator(`a:has-text('${reportName}')`),
  ];
  if (!(await clickFirstMatch(page, linkSelectors, 8000))) {
    throw new Error(`Nao foi possivel localizar o relatorio '${reportName}' na lista.`);
  }
  await page.waitForLoadState('networkidle', { timeout: 15000 });
}

async function selectDropdown(page, label, optionText) {
  try {
    const selectEl = page.getByLabel(label, { exact: false });
    await selectEl.waitFor({ state: 'visible', timeout: 3000 });
    await selectEl.selectOption({ label: optionText });
    return;
  } catch (err) {
    // tenta a proxima estrategia
  }

  const labelLocator = page.getByText(label, { exact: false }).first();

  try {
    const selectEl = labelLocator.locator('xpath=following::select[1]');
    await selectEl.waitFor({ state: 'visible', timeout: 3000 });
    await selectEl.selectOption({ label: optionText });
    return;
  } catch (err) {
    // tenta a proxima estrategia
  }

  try {
    const opener = labelLocator.locator(
      'xpath=following::*[self::button or self::input or self::div][1]'
    );
    await opener.click({ timeout: 3000 });
    await page.getByText(optionText, { exact: true }).click({ timeout: 3000 });
    return;
  } catch (err) {
    throw new Error(`Nao foi possivel selecionar '${optionText}' no campo '${label}': ${err.message}`);
  }
}

async function exportReport(page, downloadDir, operationKey, exportFormat = 'EXCEL') {
  const exportButtonSelectors = [
    (p) => p.getByRole('button', { name: 'Export', exact: true }),
    (p) => p.locator("button:has-text('Export')"),
  ];
  if (!(await clickFirstMatch(page, exportButtonSelectors, 8000))) {
    throw new Error('Nao foi possivel localizar o botao Export na pagina do relatorio.');
  }

  const formatSelectors = [
    (p) => p.getByLabel(exportFormat, { exact: false }),
    (p) => p.locator(`label:has-text('${exportFormat}')`),
    (p) => p.getByText(exportFormat, { exact: true }),
  ];
  if (!(await clickFirstMatch(page, formatSelectors, 5000))) {
    throw new Error(`Nao foi possivel selecionar o formato ${exportFormat} na tela de exportacao.`);
  }

  const okSelectors = [
    (p) => p.getByRole('button', { name: 'Ok', exact: true }),
    (p) => p.getByRole('button', { name: 'OK', exact: true }),
  ];

  let clickError = null;
  const [download] = await Promise.all([
    page.waitForEvent('download', { timeout: 60000 }),
    (async () => {
      const clicked = await clickFirstMatch(page, okSelectors, 5000);
      if (!clicked) {
        clickError = new Error('Nao foi possivel localizar o botao Ok na tela de exportacao.');
        throw clickError;
      }
    })(),
  ]);

  fs.mkdirSync(downloadDir, { recursive: true });
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
  const suggested = download.suggestedFilename();
  const extension = path.extname(suggested) || '.xlsx';
  const filename = `ScoreCard_${operationKey}_${timestamp}${extension}`;
  const destPath = path.join(downloadDir, filename);
  await download.saveAs(destPath);
  return { destPath, filename };
}

module.exports = {
  openBrowserSession,
  takeScreenshot,
  login,
  openReportsMenu,
  openReport,
  selectDropdown,
  exportReport,
};
