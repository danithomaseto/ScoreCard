const os = require('os');
const path = require('path');
const OPERATIONS = require('../config/operations');
const {
  openBrowserSession,
  login,
  openReportsMenu,
  openReport,
  selectDropdown,
  exportReport,
  takeScreenshot,
} = require('./base');

const OPERATION_KEY = 'hugo_boss';

function defaultDownloadDir() {
  if (process.env.DOWNLOAD_DIR) return process.env.DOWNLOAD_DIR;
  return path.join(os.tmpdir(), 'scorecard-downloads');
}

async function run({ headless = true } = {}) {
  const config = OPERATIONS[OPERATION_KEY];
  const username = process.env[config.usernameEnv];
  const password = process.env[config.passwordEnv];

  if (!username || !password) {
    return {
      operation: OPERATION_KEY,
      success: false,
      message: `Credenciais nao configuradas. Defina ${config.usernameEnv} e ${config.passwordEnv} no .env do agente.`,
    };
  }

  const downloadDir = defaultDownloadDir();
  const { browser, context, page } = await openBrowserSession(headless);
  const result = { operation: OPERATION_KEY };

  try {
    await login(page, config.loginUrl, username, password);
    await openReportsMenu(page);
    await openReport(page, config.reportName);

    await selectDropdown(page, 'Date Range', config.dateRangeOption);
    await selectDropdown(page, 'Group By 1', config.groupByOption);

    const { destPath, filename } = await exportReport(
      page,
      downloadDir,
      OPERATION_KEY,
      config.exportFormat
    );

    result.success = true;
    result.message = `Relatorio gerado: ${filename}`;
    result.filePath = destPath;
    result.fileName = filename;
  } catch (err) {
    result.success = false;
    result.message = err.message;
    result.screenshot = await takeScreenshot(page, OPERATION_KEY);
  } finally {
    await context.close();
    await browser.close();
  }

  return result;
}

module.exports = { run, OPERATION_KEY, defaultDownloadDir };
