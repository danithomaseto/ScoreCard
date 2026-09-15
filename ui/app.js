const loginView = document.getElementById('login-view');
const appView = document.getElementById('app-view');

const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginBtn = document.getElementById('login-btn');
const loginStatus = document.getElementById('login-status');

const operationSelect = document.getElementById('operation');
const dateRangeMode = document.getElementById('date-range-mode');
const customDateFields = document.getElementById('custom-date-fields');
const fromDateInput = document.getElementById('from-date');
const toDateInput = document.getElementById('to-date');
const groupBySelect = document.getElementById('group-by');
const runBtn = document.getElementById('run-btn');
const runStatus = document.getElementById('run-status');

const logoutBtn = document.getElementById('logout-btn');
const folderPathEl = document.getElementById('folder-path');
const chooseFolderBtn = document.getElementById('choose-folder-btn');
const reportsListEl = document.getElementById('reports-list');

const navItems = document.querySelectorAll('.nav-item[data-page]');
const pages = document.querySelectorAll('.page');

function showStatus(el, message, kind) {
  el.textContent = message;
  el.className = 'status' + (kind ? ' ' + kind : '');
  el.hidden = false;
}

function showLogin() {
  loginView.hidden = false;
  appView.hidden = true;
}

async function showApp() {
  loginView.hidden = true;
  appView.hidden = false;
  await loadOperations();
  await loadGroupByOptions();
  await showPage('home');
}

async function showPage(pageName) {
  for (const btn of navItems) {
    btn.classList.toggle('active', btn.dataset.page === pageName);
  }
  for (const page of pages) {
    page.hidden = page.id !== `page-${pageName}`;
  }
  if (pageName === 'reports') {
    await loadReportHistory();
  } else if (pageName === 'settings') {
    const check = await pywebview.api.validate_sharepoint_folder();
    folderPathEl.textContent = check.valid ? check.folder : 'Nenhuma pasta configurada ainda.';
  }
}

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

async function loadReportHistory() {
  const history = await pywebview.api.get_report_history();
  reportsListEl.innerHTML = '';
  if (!history.length) {
    const empty = document.createElement('p');
    empty.className = 'subtitle';
    empty.textContent = 'Nenhum relatorio extraido ainda.';
    reportsListEl.appendChild(empty);
    return;
  }
  for (const entry of history) {
    const row = document.createElement('div');
    row.className = 'report-row';

    const main = document.createElement('div');
    main.className = 'report-row-main';

    const opLabel = document.createElement('strong');
    opLabel.textContent = entry.operation;

    const when = document.createElement('span');
    when.className = 'report-row-date';
    when.textContent = new Date(entry.timestamp).toLocaleString('pt-BR');

    main.appendChild(opLabel);
    main.appendChild(when);

    const path = document.createElement('div');
    path.className = 'report-row-path';
    path.textContent = entry.file_path;

    row.appendChild(main);
    row.appendChild(path);
    reportsListEl.appendChild(row);
  }
}

async function loadOperations() {
  const operations = await pywebview.api.get_operations();
  operationSelect.innerHTML = '';
  for (const op of operations) {
    const opt = document.createElement('option');
    opt.value = op.key;
    opt.textContent = op.label;
    operationSelect.appendChild(opt);
  }
}

async function loadGroupByOptions() {
  const options = await pywebview.api.get_group_by_options();
  groupBySelect.innerHTML = '';
  for (const value of options) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = value;
    groupBySelect.appendChild(opt);
  }
  // "User ID" e o padrao usado ate hoje em todas as operacoes.
  groupBySelect.value = 'User ID';
}

async function ensureFolderConfigured() {
  const check = await pywebview.api.validate_sharepoint_folder();
  if (check.valid) {
    folderPathEl.textContent = check.folder;
    return true;
  }

  alert(
    'Antes de comecar, selecione a pasta do SharePoint/OneDrive onde os ' +
    'relatorios extraidos serao salvos.'
  );
  const result = await pywebview.api.choose_sharepoint_folder();
  if (result.success) {
    folderPathEl.textContent = result.folder;
    return true;
  }
  return false;
}

loginBtn.addEventListener('click', async () => {
  const username = loginUsername.value.trim();
  const password = loginPassword.value;
  loginStatus.hidden = true;

  if (!username || !password) {
    showStatus(loginStatus, 'Preencha usuario e senha.', 'error');
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = 'Entrando...';
  try {
    const result = await pywebview.api.login(username, password);
    if (!result.success) {
      showStatus(loginStatus, result.message || 'Falha no login.', 'error');
      return;
    }
    loginPassword.value = '';
    await showApp();
    await ensureFolderConfigured();
  } finally {
    loginBtn.disabled = false;
    loginBtn.textContent = 'Entrar';
  }
});

// Chamado pelo Python (api.py) a cada etapa da automacao, em tempo
// real, enquanto run_extraction ainda esta rodando.
window.updateProgress = function (text) {
  showStatus(runStatus, text, '');
};

dateRangeMode.addEventListener('change', () => {
  customDateFields.hidden = dateRangeMode.value !== 'custom';
});

runBtn.addEventListener('click', async () => {
  runStatus.hidden = true;

  let dateRange = null;
  if (dateRangeMode.value === 'custom') {
    if (!fromDateInput.value || !toDateInput.value) {
      showStatus(runStatus, 'Preencha as datas De e Ate.', 'error');
      return;
    }
    if (fromDateInput.value > toDateInput.value) {
      showStatus(runStatus, 'A data "De" nao pode ser depois da data "Ate".', 'error');
      return;
    }
    // yyyy-mm-dd (formato nativo do <input type="date">) - a conversao
    // pro formato que o Summary espera (dd/mm/yyyy) acontece no Python,
    // perto de onde o campo de verdade e preenchido.
    dateRange = { from_date: fromDateInput.value, to_date: toDateInput.value };
  }

  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(runStatus, 'E necessario selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  runBtn.disabled = true;
  runBtn.textContent = 'Executando...';
  showStatus(runStatus, 'Executando a automacao, aguarde...', '');
  try {
    const result = await pywebview.api.run_extraction(operationSelect.value, dateRange, groupBySelect.value);
    showStatus(runStatus, result.message, result.success ? 'success' : 'error');
  } catch (err) {
    showStatus(runStatus, 'Erro inesperado: ' + err.message, 'error');
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = 'Executar';
  }
});

chooseFolderBtn.addEventListener('click', async () => {
  const result = await pywebview.api.choose_sharepoint_folder();
  if (result.success) {
    folderPathEl.textContent = result.folder;
  }
});

logoutBtn.addEventListener('click', async () => {
  await pywebview.api.logout();
  loginUsername.value = '';
  loginPassword.value = '';
  showLogin();
});

window.addEventListener('pywebviewready', () => {
  showLogin();
});
