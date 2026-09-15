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
const lastRunValueEl = document.getElementById('last-run-value');
const lastRunStatusEl = document.getElementById('last-run-status');

const progressBadgeEl = document.getElementById('progress-badge');
const progressDetailEl = document.getElementById('progress-detail');
const progressPercentEl = document.getElementById('progress-percent');
const stepEls = document.querySelectorAll('#progress-steps .step');
const historyTableBody = document.getElementById('history-table-body');

const navItems = document.querySelectorAll('.nav-item[data-page]');
const pages = document.querySelectorAll('.page');

const PROGRESS_STEPS = [
  { key: 'login', match: (t) => t.includes('abrindo o navegador') || t.includes('fazendo login') },
  { key: 'report', match: (t) => t.includes('abrindo menu') || t.includes('localizando o iframe') || t.includes('abrindo o relatorio') },
  { key: 'filters', match: (t) => t.includes('date range') || t.includes('periodo especifico') || t.includes('group by') },
  { key: 'export', match: (t) => t.includes('exportando e baixando') || t.includes('concluido') },
];

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
  if (pageName === 'home') {
    await loadLastRun();
  } else if (pageName === 'extract') {
    await loadHistoryTable();
  } else if (pageName === 'settings') {
    const check = await pywebview.api.validate_sharepoint_folder();
    folderPathEl.textContent = check.valid ? check.folder : 'Nenhuma pasta configurada ainda.';
  }
}

async function loadLastRun() {
  const history = await pywebview.api.get_report_history();
  if (!history.length) {
    lastRunValueEl.textContent = 'Nenhuma extracao ainda';
    lastRunStatusEl.textContent = 'Aguardando';
    lastRunStatusEl.className = 'last-run-status empty';
    return;
  }
  const last = history[0];
  const ok = last.status ? last.status === 'success' : true;
  lastRunValueEl.textContent = `${last.operation} - ${new Date(last.timestamp).toLocaleString('pt-BR')}`;
  lastRunStatusEl.textContent = ok ? 'Concluida' : 'Falha';
  lastRunStatusEl.className = 'last-run-status' + (ok ? '' : ' error');
}

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

async function loadHistoryTable() {
  const history = await pywebview.api.get_report_history();
  historyTableBody.innerHTML = '';
  if (!history.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.className = 'empty-history-msg';
    cell.textContent = 'Nenhuma extracao registrada ainda.';
    row.appendChild(cell);
    historyTableBody.appendChild(row);
    return;
  }
  for (const entry of history) {
    const row = document.createElement('tr');
    row.appendChild(makeCell(new Date(entry.timestamp).toLocaleString('pt-BR')));
    row.appendChild(makeCell(entry.operation || '-'));
    row.appendChild(makeCell(entry.period_label || '-'));
    row.appendChild(makeCell(entry.group_by || '-'));
    row.appendChild(makeCell(formatDuration(entry.duration_seconds)));

    const statusCell = document.createElement('td');
    // Entradas gravadas antes deste campo existir nao tem "status", mas
    // so eram criadas quando a extracao dava certo - entao a ausencia do
    // campo conta como sucesso, nao falha.
    const ok = entry.status ? entry.status === 'success' : true;
    const pill = document.createElement('span');
    pill.className = 'status-pill ' + (ok ? 'success' : 'error');
    pill.textContent = ok ? 'Concluida' : 'Falha';
    statusCell.appendChild(pill);
    row.appendChild(statusCell);

    historyTableBody.appendChild(row);
  }
}

function makeCell(text) {
  const td = document.createElement('td');
  td.textContent = text;
  return td;
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '-';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}min ${secs}s`;
}

function setBadge(kind, text) {
  progressBadgeEl.textContent = text;
  progressBadgeEl.className = 'badge' + (kind ? ' ' + kind : '');
}

function resetSteps() {
  stepEls.forEach((el) => el.classList.remove('active', 'done', 'error'));
}

function updateSteps(activeIndex) {
  stepEls.forEach((el, idx) => {
    el.classList.remove('active', 'done', 'error');
    if (idx < activeIndex) el.classList.add('done');
    else if (idx === activeIndex) el.classList.add('active');
  });
}

function markStepsError() {
  stepEls.forEach((el) => {
    if (el.classList.contains('active')) {
      el.classList.remove('active');
      el.classList.add('error');
    }
  });
}

function markStepsDone() {
  stepEls.forEach((el) => {
    el.classList.remove('active', 'error');
    el.classList.add('done');
  });
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
// real, enquanto run_extraction ainda esta rodando. Mapeia a frase
// recebida pra uma das 4 etapas do painel "Andamento".
window.updateProgress = function (text) {
  progressDetailEl.textContent = text;
  const lower = text.toLowerCase();

  if (lower.startsWith('falhou')) {
    markStepsError();
    setBadge('error', 'Falha');
    return;
  }

  const stepIndex = PROGRESS_STEPS.findIndex((def) => def.match(lower));
  if (stepIndex === -1) return;

  setBadge('running', 'Em andamento');
  updateSteps(stepIndex);
  progressPercentEl.textContent = `${Math.round(((stepIndex + 1) / PROGRESS_STEPS.length) * 100)}%`;
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
  resetSteps();
  setBadge('running', 'Em andamento');
  progressDetailEl.textContent = 'Iniciando a extracao...';
  progressPercentEl.textContent = '0%';
  try {
    const result = await pywebview.api.run_extraction(operationSelect.value, dateRange, groupBySelect.value);
    if (result.success) {
      markStepsDone();
      setBadge('success', 'Concluida');
      progressPercentEl.textContent = '100%';
    } else {
      markStepsError();
      setBadge('error', 'Falha');
    }
    progressDetailEl.textContent = result.message;
    showStatus(runStatus, result.message, result.success ? 'success' : 'error');
    await loadHistoryTable();
  } catch (err) {
    markStepsError();
    setBadge('error', 'Falha');
    showStatus(runStatus, 'Erro inesperado: ' + err.message, 'error');
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = '▶ Iniciar extracao';
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
