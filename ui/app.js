const loginView = document.getElementById('login-view');
const appView = document.getElementById('app-view');
const settingsModal = document.getElementById('settings-modal');

const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginBtn = document.getElementById('login-btn');
const loginStatus = document.getElementById('login-status');

const operationSelect = document.getElementById('operation');
const runBtn = document.getElementById('run-btn');
const runStatus = document.getElementById('run-status');

const settingsBtn = document.getElementById('settings-btn');
const logoutBtn = document.getElementById('logout-btn');
const folderPathEl = document.getElementById('folder-path');
const chooseFolderBtn = document.getElementById('choose-folder-btn');
const closeSettingsBtn = document.getElementById('close-settings-btn');

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

runBtn.addEventListener('click', async () => {
  runStatus.hidden = true;
  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(runStatus, 'E necessario selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  runBtn.disabled = true;
  runBtn.textContent = 'Executando...';
  showStatus(runStatus, 'Executando a automacao, aguarde...', '');
  try {
    const result = await pywebview.api.run_extraction(operationSelect.value);
    showStatus(runStatus, result.message, result.success ? 'success' : 'error');
  } catch (err) {
    showStatus(runStatus, 'Erro inesperado: ' + err.message, 'error');
  } finally {
    runBtn.disabled = false;
    runBtn.textContent = 'Executar';
  }
});

settingsBtn.addEventListener('click', async () => {
  const check = await pywebview.api.validate_sharepoint_folder();
  folderPathEl.textContent = check.valid ? check.folder : 'Nenhuma pasta configurada ainda.';
  settingsModal.hidden = false;
});

closeSettingsBtn.addEventListener('click', () => {
  settingsModal.hidden = true;
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
