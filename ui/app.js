const loginView = document.getElementById('login-view');
const appView = document.getElementById('app-view');

const loginUsername = document.getElementById('login-username');
const loginPassword = document.getElementById('login-password');
const loginBtn = document.getElementById('login-btn');
const loginStatus = document.getElementById('login-status');

const operationSelect = document.getElementById('operation');
const fromDateInput = document.getElementById('from-date');
const toDateInput = document.getElementById('to-date');
const groupBySelect = document.getElementById('group-by');
const periodOptionEls = document.querySelectorAll('#period-options .period-option');
const runBtn = document.getElementById('run-btn');
const runStatus = document.getElementById('run-status');
const runActions = document.getElementById('run-actions');

const logoutBtn = document.getElementById('logout-btn');
const folderPathEl = document.getElementById('folder-path');
const chooseFolderBtn = document.getElementById('choose-folder-btn');
const homeOperationSelect = document.getElementById('home-operation');
const homeLastRunEl = document.getElementById('home-last-run');
const indicatorsHead = document.getElementById('indicators-head');
const indicatorsBody = document.getElementById('indicators-body');
const indicatorsWrap = document.getElementById('indicators-wrap');
const indicatorsEmpty = document.getElementById('indicators-empty');
const indicatorsLegend = document.getElementById('indicators-legend');

const progressBadgeEl = document.getElementById('progress-badge');
const progressDetailEl = document.getElementById('progress-detail');
const progressPercentEl = document.getElementById('progress-percent');
const stepEls = document.querySelectorAll('#progress-steps .step');
const historyTableBody = document.getElementById('history-table-body');

const multiOperationsEl = document.getElementById('multi-operations');
const multiSelectAllBtn = document.getElementById('multi-select-all');
const multiClearBtn = document.getElementById('multi-clear');
const multiFromDateInput = document.getElementById('multi-from-date');
const multiToDateInput = document.getElementById('multi-to-date');
const multiGroupBySelect = document.getElementById('multi-group-by');
const multiPeriodOptionEls = document.querySelectorAll('#multi-period-options .period-option');
const multiRunBtn = document.getElementById('multi-run-btn');
const multiStopBtn = document.getElementById('multi-stop-btn');
const multiRunStatus = document.getElementById('multi-run-status');
const multiRunActions = document.getElementById('multi-run-actions');
const multiProgressBadgeEl = document.getElementById('multi-progress-badge');
const multiProgressDetailEl = document.getElementById('multi-progress-detail');
const multiProgressPercentEl = document.getElementById('multi-progress-percent');
const multiStepsEl = document.getElementById('multi-progress-steps');
const multiHistoryTableBody = document.getElementById('multi-history-table-body');

const navItems = document.querySelectorAll('.nav-item[data-page]');
const pages = document.querySelectorAll('.page');

// Uma etapa pra cada mensagem que automation/generic.py emite via
// on_progress, na mesma ordem em que acontecem.
const PROGRESS_STEPS = [
  { key: 'browser', match: (t) => t.includes('abrindo o navegador') },
  { key: 'login', match: (t) => t.includes('fazendo login') },
  { key: 'menu', match: (t) => t.includes('abrindo menu') },
  { key: 'frame', match: (t) => t.includes('localizando o iframe') },
  { key: 'report', match: (t) => t.includes('abrindo o relatorio') },
  { key: 'period', match: (t) => t.includes('periodo especifico') || t.includes('date range') },
  // "group by 1" cobre tanto o Week fixo da semana quanto o User ID do
  // mes; o segundo nivel so existe no fluxo semanal, e quando nao
  // acontece o passo simplesmente nao acende.
  { key: 'groupby1', match: (t) => t.includes('group by 1') },
  { key: 'groupby2', match: (t) => t.includes('segundo nivel') || t.includes('group by 2') },
  { key: 'export', match: (t) => t.includes('exportando e baixando') },
  { key: 'save', match: (t) => t.includes('concluido') },
];

function showStatus(el, message, kind) {
  el.textContent = message;
  el.className = 'status' + (kind ? ' ' + kind : '');
  el.hidden = false;
}

// Botoes que aparecem depois de uma extracao: abrir a pasta onde o
// arquivo caiu e, quando algo falha, o print da tela do erro (que a
// automacao ja salva, mas ate agora ninguem via).
function showRunActions(container, { houveSucesso, houveFalha }) {
  container.innerHTML = '';

  const adicionar = (texto, acao) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.textContent = texto;
    btn.addEventListener('click', async () => {
      const result = await acao();
      if (result && !result.success) {
        alert(result.message || 'Nao foi possivel abrir.');
      }
    });
    container.appendChild(btn);
  };

  if (houveSucesso) {
    adicionar('📂 Abrir pasta', () => pywebview.api.open_last_folder());
  }
  if (houveFalha) {
    adicionar('🖼 Ver print do erro', () => pywebview.api.open_error_screenshot());
  }

  container.hidden = container.childElementCount === 0;
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
    await loadHome();
  } else if (pageName === 'extract') {
    await loadHistoryTable(historyTableBody);
  } else if (pageName === 'multi') {
    await loadHistoryTable(multiHistoryTableBody);
  } else if (pageName === 'settings') {
    const check = await pywebview.api.validate_sharepoint_folder();
    folderPathEl.textContent = check.valid ? check.folder : 'Nenhuma pasta configurada ainda.';
  }
}

async function loadHome() {
  await loadLastRun();
  await loadIndicators();
}

async function loadLastRun() {
  const history = await pywebview.api.get_report_history();
  if (!history.length) {
    homeLastRunEl.textContent = 'Nenhuma extracao ainda';
    return;
  }
  const last = history[0];
  // Entradas gravadas antes deste campo existir nao tem "status", mas so
  // eram criadas quando a extracao dava certo - entao a ausencia do campo
  // conta como sucesso, nao falha.
  const ok = last.status ? last.status === 'success' : true;
  const quando = new Date(last.timestamp).toLocaleString('pt-BR');
  homeLastRunEl.textContent = ok
    ? `Ultima extracao: ${last.operation}, ${quando}`
    : `Ultima extracao: ${last.operation}, ${quando} (falhou)`;
}

// O texto e a cor de cada celula vem prontos do Python: as faixas sao
// regra de negocio, e regra repetida em dois lugares vira duas regras
// diferentes na primeira mudanca.
async function loadIndicators() {
  const operacao = homeOperationSelect.value;
  if (!operacao) return;

  const tabela = await pywebview.api.get_indicator_table(operacao);
  const temDados = tabela.colunas.length > 0;

  indicatorsEmpty.hidden = temDados;
  indicatorsWrap.hidden = !temDados;
  indicatorsLegend.hidden = !temDados;
  if (!temDados) return;

  desenharCabecalho(tabela);
  desenharLinhas(tabela);
}

function desenharCabecalho(tabela) {
  indicatorsHead.innerHTML = '';

  // O canto leva o nome da operacao: num print levado pra reuniao o
  // filtro costuma ficar fora do recorte, e a tabela precisa dizer de
  // quem ela e.
  const canto = document.createElement('th');
  canto.scope = 'col';
  canto.className = 'indicator-corner';
  const rotulo = document.createElement('div');
  rotulo.className = 'corner-label';
  rotulo.textContent = 'Operacao';
  const nome = document.createElement('div');
  nome.className = 'corner-operation';
  nome.textContent = tabela.operacao;
  canto.appendChild(rotulo);
  canto.appendChild(nome);
  indicatorsHead.appendChild(canto);

  tabela.colunas.forEach((coluna, indice) => {
    const th = document.createElement('th');
    th.scope = 'col';
    th.className = 'indicator-col' + (coluna.periodo === 'month' ? ' month-col' : '');

    const titulo = document.createElement('div');
    titulo.className = 'col-title';
    titulo.textContent = coluna.titulo;
    th.appendChild(titulo);

    const subtitulo = document.createElement('div');
    subtitulo.className = 'col-subtitle';
    subtitulo.textContent = coluna.subtitulo;
    th.appendChild(subtitulo);

    if (coluna.parcial) {
      const aviso = document.createElement('div');
      aviso.className = 'col-warning';
      aviso.textContent = 'semana incompleta';
      th.appendChild(aviso);
    }

    th.appendChild(botaoCopiar(indice, coluna.titulo));
    indicatorsHead.appendChild(th);
  });
}

function desenharLinhas(tabela) {
  indicatorsBody.innerHTML = '';
  for (const linha of tabela.linhas) {
    const tr = document.createElement('tr');

    const th = document.createElement('th');
    th.scope = 'row';
    th.className = 'indicator-name';
    const nome = document.createElement('div');
    nome.className = 'indicator-label';
    nome.textContent = linha.rotulo;
    const meta = document.createElement('div');
    meta.className = 'indicator-meta';
    meta.textContent = linha.meta;
    th.appendChild(nome);
    th.appendChild(meta);
    tr.appendChild(th);

    linha.celulas.forEach((celula, indice) => {
      const td = document.createElement('td');
      const coluna = tabela.colunas[indice];
      td.className = 'indicator-cell' + (coluna.periodo === 'month' ? ' month-col' : '');
      if (celula.texto) {
        const valor = document.createElement('span');
        valor.className = 'indicator-value ' + (celula.cor || '');
        valor.textContent = celula.texto;
        td.appendChild(valor);
      } else {
        // Sem numero e traco, nunca zero: zero e um numero ruim, traco
        // e "ainda nao temos".
        td.classList.add('sem-numero');
        td.textContent = '\u2014';
      }
      tr.appendChild(td);
    });

    indicatorsBody.appendChild(tr);
  }
}

function botaoCopiar(indice, titulo) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'copy-btn';
  btn.setAttribute('aria-label', `Copiar os numeros de ${titulo}`);
  btn.textContent = 'Copiar';
  btn.addEventListener('click', () => copiarColuna(indice, btn));
  return btn;
}

// Um valor por linha, na ordem dos indicadores: colando no Excel cada
// um cai numa celula, descendo a coluna. Indicador sem numero vira linha
// vazia, pra nenhum valor subir de lugar.
function textoDaColuna(indice) {
  return Array.from(indicatorsBody.querySelectorAll('tr'))
    .map((tr) => {
      const celula = tr.querySelectorAll('td')[indice];
      if (!celula) return '';
      const valor = celula.querySelector('.indicator-value');
      return valor ? valor.textContent : '';
    })
    .join('\n');
}

async function copiarColuna(indice, btn) {
  const texto = textoDaColuna(indice);
  const copiado = await copiarTexto(texto);

  const original = btn.textContent;
  btn.textContent = copiado ? 'Copiado' : 'Nao deu';
  btn.classList.toggle('copiado', copiado);
  setTimeout(() => {
    btn.textContent = original;
    btn.classList.remove('copiado');
  }, 2000);
}

async function copiarTexto(texto) {
  // O WebView2 aceita a area de transferencia do navegador em contexto
  // seguro; o textarea escondido cobre o caso de nao aceitar.
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch (err) {
    // cai no plano B
  }
  try {
    const area = document.createElement('textarea');
    area.value = texto;
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(area);
    return ok;
  } catch (err) {
    return false;
  }
}

homeOperationSelect.addEventListener('change', loadIndicators);

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// As duas abas de extracao mostram o mesmo historico, cada uma com o
// seu <tbody>.
async function loadHistoryTable(tbody = historyTableBody) {
  const history = await pywebview.api.get_report_history();
  tbody.innerHTML = '';
  if (!history.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 7;
    cell.className = 'empty-history-msg';
    cell.textContent = 'Nenhuma extracao registrada ainda.';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }
  for (const entry of history) {
    const row = document.createElement('tr');
    row.appendChild(makeCell(new Date(entry.timestamp).toLocaleString('pt-BR')));
    row.appendChild(makeCell(entry.operation || '-'));
    row.appendChild(makeCell(entry.period_type || '-'));
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

    tbody.appendChild(row);
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
  homeOperationSelect.innerHTML = '';
  multiOperationsEl.innerHTML = '';
  for (const op of operations) {
    const opt = document.createElement('option');
    opt.value = op.key;
    opt.textContent = op.label;
    operationSelect.appendChild(opt);

    const homeOpt = opt.cloneNode(true);
    homeOperationSelect.appendChild(homeOpt);

    // Mesma lista, em forma de checkbox, na aba Extrair Multiplos.
    const item = document.createElement('label');
    item.className = 'ops-item';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = op.key;
    checkbox.addEventListener('change', () => {
      item.classList.toggle('selected', checkbox.checked);
      refreshMultiQueue();
    });
    const name = document.createElement('span');
    name.textContent = op.label;
    item.appendChild(checkbox);
    item.appendChild(name);
    multiOperationsEl.appendChild(item);
  }
}

async function loadGroupByOptions() {
  const options = await pywebview.api.get_group_by_options();
  for (const select of [groupBySelect, multiGroupBySelect]) {
    select.innerHTML = '';
    for (const value of options) {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = value;
      select.appendChild(opt);
    }
    // "User ID" e o padrao usado ate hoje em todas as operacoes.
    select.value = 'User ID';
  }
}

periodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => {
    periodOptionEls.forEach((el) => el.classList.remove('active'));
    btn.classList.add('active');
  });
});

multiPeriodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => {
    multiPeriodOptionEls.forEach((el) => el.classList.remove('active'));
    btn.classList.add('active');
  });
});

function getSelectedMultiPeriod() {
  const active = document.querySelector('#multi-period-options .period-option.active');
  return active ? active.dataset.period : 'week';
}

function getSelectedOperations() {
  const selected = [];
  multiOperationsEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    if (checkbox.checked) {
      selected.push({ key: checkbox.value, label: checkbox.parentElement.textContent.trim() });
    }
  });
  return selected;
}

function setMultiChecked(checked) {
  multiOperationsEl.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
    checkbox.checked = checked;
    checkbox.parentElement.classList.toggle('selected', checked);
  });
  refreshMultiQueue();
}

multiSelectAllBtn.addEventListener('click', () => setMultiChecked(true));
multiClearBtn.addEventListener('click', () => setMultiChecked(false));

// Monta a fila do painel "Andamento" com uma linha por operacao
// selecionada, reaproveitando o visual das etapas da outra aba.
function refreshMultiQueue() {
  const selected = getSelectedOperations();
  multiStepsEl.innerHTML = '';

  if (!selected.length) {
    const empty = document.createElement('p');
    empty.className = 'subtitle';
    empty.textContent = 'Selecione as operacoes ao lado para ver a fila aqui.';
    multiStepsEl.appendChild(empty);
    multiProgressDetailEl.textContent = 'Nenhuma extracao em andamento';
    multiProgressPercentEl.textContent = '0%';
    return;
  }

  selected.forEach((op, index) => {
    const step = document.createElement('div');
    step.className = 'step';
    step.dataset.opKey = op.key;

    const number = document.createElement('div');
    number.className = 'step-number';
    number.textContent = String(index + 1);

    const content = document.createElement('div');
    content.className = 'step-content';
    const title = document.createElement('div');
    title.className = 'step-title';
    title.textContent = op.label;
    const subtitle = document.createElement('div');
    subtitle.className = 'step-subtitle';
    subtitle.textContent = 'Na fila';
    content.appendChild(title);
    content.appendChild(subtitle);

    step.appendChild(number);
    step.appendChild(content);
    multiStepsEl.appendChild(step);
  });

  multiProgressDetailEl.textContent = `${selected.length} operacao(oes) na fila`;
  multiProgressPercentEl.textContent = '0%';
}

function setMultiBadge(kind, text) {
  multiProgressBadgeEl.textContent = text;
  multiProgressBadgeEl.className = 'badge' + (kind ? ' ' + kind : '');
}

// Chamado pelo Python (api.py) a cada etapa de cada operacao da fila.
window.updateMultiProgress = function (data) {
  const steps = multiStepsEl.querySelectorAll('.step');
  const step = steps[data.index];
  if (!step) return;

  const subtitle = step.querySelector('.step-subtitle');
  step.classList.remove('active', 'done', 'error');

  if (data.status === 'running') {
    step.classList.add('active');
    subtitle.textContent = data.step;
    multiProgressPercentEl.textContent = `${Math.round((data.index / data.total) * 100)}%`;
  } else {
    const classePorStatus = { success: 'done', cancelled: 'cancelled' };
    step.classList.add(classePorStatus[data.status] || 'error');
    subtitle.textContent = data.status === 'success' ? 'Concluida' : data.step;
    multiProgressPercentEl.textContent = `${Math.round(((data.index + 1) / data.total) * 100)}%`;
  }

  multiProgressDetailEl.textContent = `${data.index + 1} de ${data.total} - ${data.operation_label}`;
};

// yyyy-mm-dd no fuso local. Nao da pra usar toISOString() aqui: ele
// converte pra UTC e, dependendo da hora, joga a data um dia pra tras.
function toInputDate(date) {
  const mes = String(date.getMonth() + 1).padStart(2, '0');
  const dia = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${mes}-${dia}`;
}

// Semana passada = domingo a sabado da semana anterior a atual. A
// semana comeca no domingo pra bater com o fechamento de semana do
// Summary (o "Medium Level Group" vem com o domingo como data de
// inicio), senao o intervalo extraido fica desalinhado com a semana
// dos indicadores.
function lastWeekRange() {
  const hoje = new Date();
  const inicio = new Date(hoje);
  inicio.setDate(hoje.getDate() - hoje.getDay() - 7);
  const fim = new Date(inicio);
  fim.setDate(inicio.getDate() + 6);
  return [inicio, fim];
}

// Mes passado = do dia 1 ao ultimo dia do mes anterior.
function lastMonthRange() {
  const hoje = new Date();
  const inicio = new Date(hoje.getFullYear(), hoje.getMonth() - 1, 1);
  const fim = new Date(hoje.getFullYear(), hoje.getMonth(), 0);
  return [inicio, fim];
}

// Os atalhos tambem ajustam Week/Month, que e a combinacao esperada em
// cada caso (e da pra trocar depois clicando no outro card).
document.querySelectorAll('[data-date-shortcuts]').forEach((group) => {
  const isMulti = group.dataset.dateShortcuts === 'multi';
  const fromInput = isMulti ? multiFromDateInput : fromDateInput;
  const toInput = isMulti ? multiToDateInput : toDateInput;
  const periodButtons = isMulti ? multiPeriodOptionEls : periodOptionEls;

  group.querySelectorAll('button[data-range]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const mensal = btn.dataset.range === 'last-month';
      const [inicio, fim] = mensal ? lastMonthRange() : lastWeekRange();
      fromInput.value = toInputDate(inicio);
      toInput.value = toInputDate(fim);

      const alvo = mensal ? 'month' : 'week';
      periodButtons.forEach((el) => el.classList.toggle('active', el.dataset.period === alvo));
    });
  });
});

function getSelectedPeriod() {
  const active = document.querySelector('#period-options .period-option.active');
  return active ? active.dataset.period : 'week';
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

document.getElementById('login-form').addEventListener('submit', async (event) => {
  // Botao e type="submit" dentro de um <form>, entao apertar Enter em
  // qualquer campo (inclusive Senha) dispara isso, igual clicar em
  // Entrar - sem o preventDefault o navegador tentaria recarregar a
  // pagina.
  event.preventDefault();
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

runBtn.addEventListener('click', async () => {
  runStatus.hidden = true;
  runActions.hidden = true;

  if (!fromDateInput.value || !toDateInput.value) {
    showStatus(runStatus, 'Preencha a Data inicial e a Data final.', 'error');
    return;
  }
  if (fromDateInput.value > toDateInput.value) {
    showStatus(runStatus, 'A "Data inicial" nao pode ser depois da "Data final".', 'error');
    return;
  }
  // yyyy-mm-dd (formato nativo do <input type="date">) - a conversao
  // pro formato que o Summary espera (dd/mm/yyyy) acontece no Python,
  // perto de onde o campo de verdade e preenchido.
  const dateRange = { from_date: fromDateInput.value, to_date: toDateInput.value };

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
    const result = await pywebview.api.run_extraction(operationSelect.value, dateRange, groupBySelect.value, getSelectedPeriod());
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
    showRunActions(runActions, { houveSucesso: result.success, houveFalha: !result.success });
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

multiRunBtn.addEventListener('click', async () => {
  multiRunStatus.hidden = true;
  multiRunActions.hidden = true;

  const selected = getSelectedOperations();
  if (!selected.length) {
    showStatus(multiRunStatus, 'Selecione pelo menos uma operacao.', 'error');
    return;
  }
  if (!multiFromDateInput.value || !multiToDateInput.value) {
    showStatus(multiRunStatus, 'Preencha a Data inicial e a Data final.', 'error');
    return;
  }
  if (multiFromDateInput.value > multiToDateInput.value) {
    showStatus(multiRunStatus, 'A "Data inicial" nao pode ser depois da "Data final".', 'error');
    return;
  }
  const dateRange = { from_date: multiFromDateInput.value, to_date: multiToDateInput.value };

  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(multiRunStatus, 'E necessario selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  refreshMultiQueue();
  setMultiBadge('running', 'Em andamento');
  multiProgressDetailEl.textContent = 'Iniciando a fila...';
  multiProgressPercentEl.textContent = '0%';
  multiRunBtn.disabled = true;
  multiRunBtn.textContent = 'Executando...';
  multiStopBtn.hidden = false;
  multiStopBtn.disabled = false;
  multiStopBtn.textContent = 'Parar apos a atual';
  try {
    const result = await pywebview.api.run_multi_extraction(
      selected.map((op) => op.key),
      dateRange,
      multiGroupBySelect.value,
      getSelectedMultiPeriod(),
    );
    let badgeTexto = 'Concluida';
    if (result.cancelled) badgeTexto = 'Interrompida';
    else if (!result.success) badgeTexto = 'Com falhas';
    setMultiBadge(result.success ? 'success' : 'error', badgeTexto);
    multiProgressPercentEl.textContent = '100%';
    multiProgressDetailEl.textContent = result.message;
    showStatus(multiRunStatus, result.message, result.success ? 'success' : 'error');
    showRunActions(multiRunActions, {
      houveSucesso: (result.succeeded || 0) > 0,
      houveFalha: (result.failed || 0) > 0,
    });
    await loadHistoryTable(multiHistoryTableBody);
  } catch (err) {
    setMultiBadge('error', 'Falha');
    showStatus(multiRunStatus, 'Erro inesperado: ' + err.message, 'error');
  } finally {
    multiRunBtn.disabled = false;
    multiRunBtn.textContent = '▶ Iniciar extracao';
    multiStopBtn.hidden = true;
  }
});

multiStopBtn.addEventListener('click', async () => {
  multiStopBtn.disabled = true;
  multiStopBtn.textContent = 'Parando...';
  // A operacao em andamento termina normalmente; a fila para antes da
  // proxima, pra nao deixar um download pela metade.
  multiProgressDetailEl.textContent = 'Vai parar quando a operacao atual terminar...';
  await pywebview.api.cancel_multi_extraction();
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
