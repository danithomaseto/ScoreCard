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
const homeMes = document.getElementById('home-mes');
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

// Esqueleto de carregamento: linhas cinza no formato da tabela enquanto
// o Python responde. So aparece se a resposta passar de 150 ms — abaixo
// disso ele so piscaria na tela, o que parece mais lento, nao menos.
const ESPERA_DO_ESQUELETO = 150;

// As linhas aparecem uma apos a outra (30 ms de diferenca), so no
// primeiro desenho da tabela; nas atualizacoes elas so trocam o valor.
function entrarEmSequencia(tbody) {
  if (SEM_ANIMACAO) return;
  Array.from(tbody.rows).forEach((tr, i) => {
    tr.classList.add('linha-entrando');
    tr.style.animationDelay = `${i * 30}ms`;
  });
}

function desenharEsqueleto(tbody, colunas, linhas = 4) {
  tbody.innerHTML = '';
  for (let i = 0; i < linhas; i += 1) {
    const tr = document.createElement('tr');
    tr.className = 'linha-esqueleto';
    for (let c = 0; c < colunas; c += 1) {
      const td = document.createElement('td');
      const barra = document.createElement('span');
      barra.className = 'esqueleto';
      td.appendChild(barra);
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
}

async function comEsqueleto(tbody, colunas, carregar, antesDeMostrar) {
  // Voltando a uma aba que ja tem dados, eles ficam na tela enquanto a
  // atualizacao chega: trocar por barras cinza pareceria mais lento.
  if (tbody.querySelector('tr:not(.linha-esqueleto)')) {
    return carregar();
  }
  const timer = setTimeout(() => {
    if (antesDeMostrar) antesDeMostrar();
    desenharEsqueleto(tbody, colunas);
  }, ESPERA_DO_ESQUELETO);
  try {
    return await carregar();
  } finally {
    clearTimeout(timer);
  }
}

const navItems = document.querySelectorAll('.nav-item[data-page]');
const pages = document.querySelectorAll('.page');

// Uma etapa pra cada mensagem que automation/generic.py emite via
// on_progress, na mesma ordem em que acontecem.
const PROGRESS_STEPS = [
  // Na fila, so a primeira operacao abre o navegador; as seguintes
  // abrem uma sessao nova nele.
  { key: 'browser', match: (t) => t.includes('abrindo o navegador') || t.includes('no navegador') },
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

// Uma extracao tem tres desfechos, nao dois: concluida, concluida sem
// indicador (o arquivo salvou mas o calculo nao rodou) e falha. Tratar
// o do meio como sucesso foi o que escondeu o problema do .xls.
const DESFECHOS = {
  success: { rotulo: 'Concluida', classe: 'success' },
  warning: { rotulo: 'Sem indicador', classe: 'warning' },
  error: { rotulo: 'Falha', classe: 'error' },
};

function desfechoDe(entrada) {
  // Entradas gravadas antes deste campo existir nao tem "status", mas
  // so eram criadas quando a extracao dava certo - entao a ausencia do
  // campo conta como sucesso, nao falha.
  const status = entrada.status || 'success';
  return DESFECHOS[status] || DESFECHOS.success;
}

function showStatus(el, message, kind) {
  el.textContent = message;
  el.className = 'status' + (kind ? ' ' + kind : '');
  el.hidden = false;
}

// Botoes que aparecem depois de uma extracao: abrir a pasta onde o
// arquivo caiu e, quando algo falha, o print da tela do erro (que a
// automacao ja salva, mas ate agora ninguem via).
// Mesmo desenho de traco dos icones da barra lateral.
const ICONE_PASTA = '<svg class="btn-icone" viewBox="0 0 24 24" aria-hidden="true">' +
  '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>';
const ICONE_IMAGEM = '<svg class="btn-icone" viewBox="0 0 24 24" aria-hidden="true">' +
  '<rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle>' +
  '<polyline points="21 15 16 10 5 21"></polyline></svg>';

function showRunActions(container, { houveSucesso, houveFalha }) {
  container.innerHTML = '';

  const adicionar = (texto, acao, icone) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.innerHTML = icone;
    const rotulo = document.createElement('span');
    rotulo.textContent = texto;
    btn.appendChild(rotulo);
    btn.addEventListener('click', async () => {
      const result = await acao();
      if (result && !result.success) {
        alert(result.message || 'Nao foi possivel abrir.');
      }
    });
    container.appendChild(btn);
  };

  if (houveSucesso) {
    adicionar('Abrir pasta', () => pywebview.api.open_last_folder(), ICONE_PASTA);
  }
  if (houveFalha) {
    adicionar('Ver print do erro', () => pywebview.api.open_error_screenshot(), ICONE_IMAGEM);
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
  preCarregar();
}

// Depois que o Inicio abriu, as outras abas carregam em segundo plano:
// a primeira visita a elas ja encontra a tela montada.
function preCarregar() {
  const quandoOcioso = window.requestIdleCallback || ((fn) => setTimeout(fn, 300));
  quandoOcioso(async () => {
    try {
      await loadHistoryTable(historyTableBody);
      await loadHistoryTable(multiHistoryTableBody);
      await carregarHeadcount();
    } catch (err) {
      // pre-carregar e so um adiantamento; a aba carrega de novo ao abrir
    }
  });
}

// ---------------------------------------------------------------
// Transicoes e fluidez
// ---------------------------------------------------------------
// So apresentacao: nada aqui muda o que e calculado ou mostrado.

const SEM_ANIMACAO = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const TEM_VIEW_TRANSITION = typeof document.startViewTransition === 'function' && !SEM_ANIMACAO;
if (TEM_VIEW_TRANSITION) document.documentElement.classList.add('vt');

const contentArea = document.querySelector('.content-area');
const navIndicador = document.getElementById('nav-indicador');

// A barra amarela do menu desliza ate o item ativo, em vez de pular.
function moverIndicadorDoMenu() {
  const ativo = document.querySelector('.nav-item.active');
  if (!ativo || !navIndicador) return;
  navIndicador.style.transform = `translateY(${ativo.offsetTop}px)`;
  navIndicador.style.height = `${ativo.offsetHeight}px`;
  ligarTransicaoDepois(navIndicador, 'visivel');
}

// Na primeira vez o elemento aparece ja no lugar; a animacao so vale a
// partir do quadro seguinte (senao ele deslizaria vindo do topo).
function ligarTransicaoDepois(elemento, classe) {
  if (elemento.classList.contains(classe)) return;
  elemento.classList.add(classe);
  requestAnimationFrame(() => requestAnimationFrame(() => elemento.classList.add('pronto')));
}
window.addEventListener('resize', moverIndicadorDoMenu);

function trocarPagina(pageName) {
  for (const btn of navItems) {
    btn.classList.toggle('active', btn.dataset.page === pageName);
  }
  for (const page of pages) {
    page.hidden = page.id !== `page-${pageName}`;
  }
  contentArea.scrollTop = 0;
  moverIndicadorDoMenu();
}

// Com a View Transitions API do navegador, a pagina antiga esmaece
// enquanto a nova entra; sem ela, cai na animacao de CSS (.page).
function trocarComTransicao(pageName) {
  const atual = document.querySelector('.page:not([hidden])');
  if (!TEM_VIEW_TRANSITION || !atual || atual.id === `page-${pageName}`) {
    trocarPagina(pageName);
    return;
  }
  document.startViewTransition(() => trocarPagina(pageName));
}

async function showPage(pageName) {
  trocarComTransicao(pageName);
  if (pageName === 'home') {
    await loadHome();
  } else if (pageName === 'extract') {
    await loadHistoryTable(historyTableBody);
  } else if (pageName === 'multi') {
    await loadHistoryTable(multiHistoryTableBody);
  } else if (pageName === 'headcount') {
    await carregarHeadcount();
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
  const desfecho = desfechoDe(last);
  const quando = new Date(last.timestamp).toLocaleString('pt-BR');
  const sufixo = desfecho.classe === 'success' ? '' : ` (${desfecho.rotulo.toLowerCase()})`;
  homeLastRunEl.textContent = `Ultima extracao: ${last.operation}, ${quando}${sufixo}`;
}

// O texto e a cor de cada celula vem prontos do Python: as faixas sao
// regra de negocio, e regra repetida em dois lugares vira duas regras
// diferentes na primeira mudanca.
async function loadIndicators() {
  const operacao = homeOperationSelect.value;
  if (!operacao) return;

  const tabela = await comEsqueleto(
    indicatorsBody, 6,
    () => pywebview.api.get_indicator_table(operacao, homeMes.value || null),
    () => { indicatorsEmpty.hidden = true; indicatorsWrap.hidden = false; },
  );
  preencherSelect(homeMes, tabela.meses || [], tabela.mes);
  const temDados = tabela.colunas.length > 0;

  indicatorsEmpty.hidden = temDados;
  indicatorsWrap.hidden = !temDados;
  indicatorsLegend.hidden = !temDados;
  if (!temDados) return;

  const primeiraVez = !indicatorsBody.querySelector('tr:not(.linha-esqueleto)');
  desenharCabecalho(tabela);
  desenharLinhas(tabela);
  if (primeiraVez) entrarEmSequencia(indicatorsBody);
  // Abre mostrando o fim da tabela: o mes e o pico sao o que se olha
  // primeiro, e numa janela estreita eles ficariam escondidos a direita.
  indicatorsWrap.scrollLeft = indicatorsWrap.scrollWidth;
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
    th.className = 'indicator-col' + classeDaColuna(coluna);
    if (coluna.dica) th.title = coluna.dica;

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
      aviso.textContent = coluna.aviso || 'semana incompleta';
      th.appendChild(aviso);
    }

    th.appendChild(botaoCopiar(indice, coluna.titulo));
    indicatorsHead.appendChild(th);
  });
}

function classeDaColuna(coluna) {
  if (coluna.periodo === 'month') return ' month-col';
  if (coluna.periodo === 'peak') return ' peak-col';
  return '';
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
      td.className = 'indicator-cell' + classeDaColuna(coluna);
      if (celula.nao_se_aplica) {
        // Indicador que nao existe nesta coluna (coverage no pico): nem
        // traco, que quer dizer "ainda sem numero".
        td.classList.add('nao-se-aplica');
      } else if (celula.texto) {
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

// Os valores da coluna, na ordem dos indicadores. Indicador sem numero
// vira posicao vazia, pra nenhum valor subir de lugar. Indicador que
// nao existe na coluna (coverage no pico) fica de fora: o pico copia
// cinco valores, do cubo a dispersao.
function valoresDaColuna(indice) {
  return Array.from(indicatorsBody.querySelectorAll('tr'))
    .map((tr) => tr.querySelectorAll('td')[indice])
    .filter((celula) => !(celula && celula.classList.contains('nao-se-aplica')))
    .map((celula) => {
      if (!celula) return '';
      const valor = celula.querySelector('.indicator-value');
      return valor ? valor.textContent : '';
    });
}

function textoDaColuna(indice) {
  return valoresDaColuna(indice).join('\n');
}

// A mesma coluna como tabela de uma coluna por seis linhas. E isso que
// faz cada valor cair numa celula do PowerPoint: texto com quebras de
// linha ele cola inteiro dentro de UMA celula, porque a quebra vira
// linha dentro do paragrafo, nao mudanca de celula.
function tabelaDaColuna(indice) {
  const linhas = valoresDaColuna(indice)
    .map((valor) => `<tr><td>${valor}</td></tr>`)
    .join('');
  return `<table>${linhas}</table>`;
}

async function copiarColuna(indice, btn) {
  const copiado = await copiarTexto(textoDaColuna(indice), tabelaDaColuna(indice));

  const original = btn.textContent;
  btn.textContent = copiado ? 'Copiado' : 'Nao deu';
  btn.classList.toggle('copiado', copiado);
  setTimeout(() => {
    btn.textContent = original;
    btn.classList.remove('copiado');
  }, 2000);
}

// Copia nos dois formatos de uma vez: a tabela (que o PowerPoint e o
// Excel usam pra distribuir os valores entre as celulas) e o texto
// puro (pra quem cola num bloco de notas ou num chat). Quem recebe
// escolhe o que entende.
async function copiarTexto(texto, html) {
  try {
    if (navigator.clipboard && window.ClipboardItem && window.isSecureContext) {
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': new Blob([html], { type: 'text/html' }),
          'text/plain': new Blob([texto], { type: 'text/plain' }),
        }),
      ]);
      return true;
    }
  } catch (err) {
    // cai no plano B
  }

  // Plano B: selecionar uma tabela de verdade fora da tela e mandar
  // copiar. O navegador coloca os dois formatos sozinho — e por isso
  // que aqui vai um elemento editavel, e nao um <textarea>, que so
  // saberia copiar texto puro.
  try {
    const area = document.createElement('div');
    area.contentEditable = 'true';
    area.innerHTML = html;
    area.style.position = 'fixed';
    area.style.left = '-10000px';
    area.style.opacity = '0';
    document.body.appendChild(area);

    const intervalo = document.createRange();
    intervalo.selectNodeContents(area);
    const selecao = window.getSelection();
    selecao.removeAllRanges();
    selecao.addRange(intervalo);

    const ok = document.execCommand('copy');
    selecao.removeAllRanges();
    document.body.removeChild(area);
    return ok;
  } catch (err) {
    return false;
  }
}

homeOperationSelect.addEventListener('change', loadIndicators);
homeMes.addEventListener('change', loadIndicators);

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// As duas abas de extracao mostram o mesmo historico, cada uma com o
// seu <tbody>.
async function loadHistoryTable(tbody = historyTableBody) {
  const history = await comEsqueleto(tbody, 7, () => pywebview.api.get_report_history());
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
    const desfecho = desfechoDe(entry);
    const pill = document.createElement('span');
    pill.className = 'status-pill ' + desfecho.classe;
    pill.textContent = desfecho.rotulo;
    if (entry.indicators_message) {
      pill.title = entry.indicators_message;
    }
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

// Dias de pico: o Group By 1 e sempre Report Date (uma linha por dia),
// entao o campo trava nesse valor enquanto o pico estiver escolhido e
// volta ao que estava ao trocar de novo.
const GROUP_BY_DO_PICO = 'Report Date';

function escolherPeriodo(botoes, select, periodo) {
  botoes.forEach((el) => el.classList.toggle('active', el.dataset.period === periodo));
  const pico = periodo === 'peak';
  if (pico && !select.disabled) {
    select.dataset.anterior = select.value;
    select.value = GROUP_BY_DO_PICO;
  } else if (!pico && select.disabled) {
    select.value = select.dataset.anterior || 'User ID';
  }
  select.disabled = pico;
  select.title = pico ? 'Nos dias de pico o Group By 1 e sempre Report Date.' : '';
}

periodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => escolherPeriodo(periodOptionEls, groupBySelect, btn.dataset.period));
});

multiPeriodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => escolherPeriodo(multiPeriodOptionEls, multiGroupBySelect, btn.dataset.period));
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
  step.classList.remove('active', 'done', 'error', 'warning', 'cancelled');

  if (data.status === 'running') {
    step.classList.add('active');
    subtitle.textContent = data.step;
    multiProgressPercentEl.textContent = `${Math.round((data.index / data.total) * 100)}%`;
  } else {
    const classePorStatus = { success: 'done', warning: 'warning', cancelled: 'cancelled' };
    step.classList.add(classePorStatus[data.status] || 'error');
    // Numa fila, "Concluida" nao pode mascarar a operacao que salvou o
    // arquivo sem gerar indicador: ali o motivo e que importa.
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
  const select = isMulti ? multiGroupBySelect : groupBySelect;

  group.querySelectorAll('button[data-range]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const mensal = btn.dataset.range === 'last-month';
      const [inicio, fim] = mensal ? lastMonthRange() : lastWeekRange();
      fromInput.value = toInputDate(inicio);
      toInput.value = toInputDate(fim);

      // "Mes passado" com Dias de Pico escolhido continua no pico: o pico
      // tambem e de um mes inteiro.
      const atual = Array.from(periodButtons).find((el) => el.classList.contains('active'));
      const noPico = atual && atual.dataset.period === 'peak';
      const alvo = mensal ? (noPico ? 'peak' : 'month') : 'week';
      escolherPeriodo(periodButtons, select, alvo);
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
  runBtn.querySelector('.btn-texto').textContent = 'Executando...';
  resetSteps();
  setBadge('running', 'Em andamento');
  progressDetailEl.textContent = 'Iniciando a extracao...';
  progressPercentEl.textContent = '0%';
  try {
    const result = await pywebview.api.run_extraction(operationSelect.value, dateRange, groupBySelect.value, getSelectedPeriod());
    const desfecho = desfechoDe(result);
    if (result.success) {
      markStepsDone();
      progressPercentEl.textContent = '100%';
    } else {
      markStepsError();
    }
    setBadge(desfecho.classe, desfecho.rotulo);

    // O aviso vem na frente da mensagem de sucesso: o que a pessoa
    // precisa saber e que o indicador nao saiu, nao que o arquivo
    // salvou.
    const texto = result.indicators_message || result.message;
    progressDetailEl.textContent = texto;
    showStatus(runStatus, texto, desfecho.classe);
    showRunActions(runActions, { houveSucesso: result.success, houveFalha: !result.success });
    await loadHistoryTable();
  } catch (err) {
    markStepsError();
    setBadge('error', 'Falha');
    showStatus(runStatus, 'Erro inesperado: ' + err.message, 'error');
  } finally {
    runBtn.disabled = false;
    runBtn.querySelector('.btn-texto').textContent = 'Iniciar extracao';
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
  multiRunBtn.querySelector('.btn-texto').textContent = 'Executando...';
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
    multiRunBtn.querySelector('.btn-texto').textContent = 'Iniciar extracao';
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

const diagnosticoBtn = document.getElementById('diagnostico-btn');
const diagnosticoStatus = document.getElementById('diagnostico-status');

diagnosticoBtn.addEventListener('click', async () => {
  diagnosticoStatus.textContent = 'Gerando...';
  const resultado = await comCarregando(diagnosticoBtn, () => pywebview.api.gerar_diagnostico());
  diagnosticoStatus.textContent = resultado.message;
  diagnosticoStatus.classList.toggle('erro', !resultado.success);
});

async function carregarVersao() {
  const info = await pywebview.api.get_app_info();
  const el = document.getElementById('app-versao');
  el.textContent = info.versao;
  el.title = info.build ? `Build ${info.build}${info.commit ? ' · ' + info.commit : ''}` : '';
}

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
  carregarVersao();
  showLogin();
});

// ---------------------------------------------------------------
// Aba Headcount: calculo de presenteismo
// ---------------------------------------------------------------
// O Python entrega a tela montada (filtros, cards, linhas e memoria);
// aqui so se desenha e se devolvem as acoes. As faltas nunca sao
// digitadas: vem da planilha.

const hcOperacao = document.getElementById('hc-operacao');
const hcMes = document.getElementById('hc-mes');
const hcMesLabel = document.getElementById('hc-mes-label');
const hcPeriodo = document.getElementById('hc-periodo');
const hcVisualizacao = document.getElementById('hc-visualizacao');
const hcCorpo = document.getElementById('hc-corpo');
const hcTotal = document.getElementById('hc-total');
const hcVazio = document.getElementById('hc-vazio');
const hcStatus = document.getElementById('hc-status');
const hcContador = document.getElementById('hc-contador');
const hcTabelaTitulo = document.getElementById('hc-tabela-titulo');
const hcFuncoes = document.getElementById('hc-funcoes');
const hcDropzone = document.getElementById('hc-dropzone');
const hcArquivoInput = document.getElementById('hc-arquivo-input');
const hcArquivoInfo = document.getElementById('hc-arquivo-info');

let hcEstado = { operacao: 'todas', visualizacao: 'semanal', mes: null, periodo_id: null };
let hcTela = null;

function plural(numero, singular, plural_) {
  return `${numero} ${numero === 1 ? singular : plural_}`;
}

function hcPercentual(valor) {
  if (valor === null || valor === undefined) return '-';
  return (valor * 100).toFixed(2).replace('.', ',') + '%';
}

async function carregarHeadcount() {
  hcTela = await comEsqueleto(hcCorpo, 7, () => pywebview.api.get_headcount(
    hcEstado.operacao, hcEstado.visualizacao, hcEstado.mes, hcEstado.periodo_id));

  hcEstado.mes = hcTela.mes;
  hcEstado.periodo_id = hcTela.periodo_id;

  desenharFiltrosHc(hcTela);
  desenharCardsHc(hcTela);
  desenharTabelaHc(hcTela);
  desenharFormulaHc(hcTela);
  desenharArquivoHc(hcTela);
  desenharFuncoesHc(hcTela);
}

function preencherSelect(select, itens, selecionado, chave = 'id', rotulo = 'rotulo') {
  select.innerHTML = '';
  for (const item of itens) {
    const opt = document.createElement('option');
    opt.value = item[chave];
    opt.textContent = item[rotulo];
    if (item[chave] === selecionado) opt.selected = true;
    select.appendChild(opt);
  }
}

function desenharFiltrosHc(tela) {
  preencherSelect(hcOperacao, tela.operacoes, tela.operacao, 'key', 'label');

  const noMes = tela.visualizacao === 'mes';
  // No Resultado do Mes o periodo e o ciclo da folha ponto, entao o
  // seletor de mes vira o seletor de ciclo e o de semana nao se aplica.
  hcMesLabel.textContent = noMes ? 'Periodo da Folha Ponto' : 'Mes vigente';
  if (noMes) {
    preencherSelect(hcMes, tela.periodos.map((p) => ({
      id: p.id, rotulo: `${p.rotulo_curto} · ${p.status}`,
    })), tela.periodo_id);
  } else {
    preencherSelect(hcMes, tela.meses, tela.mes);
  }

  // No modo mes o seletor de semana fica desabilitado, e o proprio texto
  // dele explica o porque - uma dica embaixo esticava o card so neste
  // modo e a tela pulava ao alternar.
  if (noMes) {
    preencherSelect(hcPeriodo, [{ id: '', rotulo: 'Nao se aplica ao ciclo da folha' }], '');
  } else {
    preencherSelect(hcPeriodo, tela.periodos, tela.periodo_id);
  }
  hcPeriodo.disabled = noMes;

  for (const botao of hcVisualizacao.querySelectorAll('.seg-opcao')) {
    botao.classList.toggle('active', botao.dataset.visualizacao === tela.visualizacao);
  }
  moverDestaque(hcVisualizacao);
}

// O fundo amarelo do seletor desliza ate a opcao ativa.
function moverDestaque(grupo) {
  const ativo = grupo.querySelector('.seg-opcao.active');
  if (!ativo || !ativo.offsetWidth) return;
  grupo.style.setProperty('--seg-x', `${ativo.offsetLeft}px`);
  grupo.style.setProperty('--seg-w', `${ativo.offsetWidth}px`);
  ligarTransicaoDepois(grupo, 'com-destaque');
}
window.addEventListener('resize', () => moverDestaque(hcVisualizacao));

function desenharCardsHc(tela) {
  const c = tela.cards;
  document.getElementById('hc-card-operacao').textContent = c.operacao;
  document.getElementById('hc-card-periodo').textContent = c.periodo;
  document.getElementById('hc-card-periodo-nota').textContent = c.periodo_nota;
  document.getElementById('hc-card-hc').textContent = c.hc_total;
  document.getElementById('hc-card-faltas').textContent = c.faltas;
  document.getElementById('hc-card-horas').textContent = `${c.horas_perdidas}h perdidas`;
  document.getElementById('hc-card-presenteismo').textContent = hcPercentual(c.presenteismo);
  document.getElementById('hc-card-meta').textContent =
    c.presenteismo === null ? 'Sem HC lancado' : (c.dentro_da_meta ? 'Dentro da meta' : 'Abaixo da meta');
}

// Um numero do quadro (HC, dias uteis, horas/dia ou faltas) de um gestor
// na semana (ou no ciclo) escolhido. Cada periodo tem os seus: o que nao
// foi digitado aparece esmaecido, herdado da semana anterior (HC e
// horas/dia) ou do calendario (dias uteis), e passa a valer so para este
// periodo quando digitado.
const ORIGENS = {
  herdado: (de) => `Veio de ${de}. Digite para mudar a partir desta semana.`,
  cadastro: () => 'Valor do cadastro do gestor. Digite para mudar a partir desta semana.',
  calendario: () => 'Dias uteis do calendario desta semana. Digite para ajustar (feriado, por exemplo).',
};

function campoQuadro(linha, campo, passo) {
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = passo;
  input.inputMode = campo === 'horas_dia' ? 'decimal' : 'numeric';
  input.value = linha[campo];
  input.dataset.gestor = linha.id;
  input.dataset.campo = campo;
  if (campo === 'faltas') input.classList.add('hc-faltas-input');

  const origem = { hc: linha.hc_origem, dias_uteis: linha.dias_origem, horas_dia: linha.horas_origem }[campo];
  if (origem && origem !== 'digitado') {
    input.classList.add('valor-herdado');
    const de = campo === 'horas_dia' ? linha.horas_de : linha.hc_de;
    input.title = ORIGENS[origem](de);
  }
  if (!linha.editavel) {
    input.disabled = true;
    return input;
  }
  const bloqueadas = campo === 'horas_dia' ? ['-', '+', 'e', 'E'] : ['-', '+', 'e', 'E', ',', '.'];
  input.addEventListener('keydown', (evento) => {
    if (bloqueadas.includes(evento.key)) evento.preventDefault();
  });
  input.addEventListener('change', async () => {
    const resposta = await pywebview.api.set_quadro(linha.id, linha.periodo_id, campo, input.value);
    if (!resposta.success) {
      hcStatus.textContent = resposta.message;
      input.value = linha[campo];
      return;
    }
    await redesenharMantendoFoco();
    hcStatus.textContent = input.value === ''
      ? 'Valor apagado: volta a valer o herdado. A aba Inicio ja reflete a mudanca.'
      : 'Salvo so para este periodo. A aba Inicio ja reflete a mudanca.';
  });
  return input;
}

// Faltas em dias, digitadas por gestor na semana (ou no ciclo) escolhido.
// Com "Todas as semanas" o campo mostra a soma e fica travado: nao da pra
// saber em qual semana lancar.
function campoFaltas(linha, periodoId) {
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = '1';
  input.inputMode = 'numeric';
  input.className = 'hc-faltas-input';
  input.value = linha.faltas;
  input.dataset.gestor = linha.id;
  input.dataset.campo = 'faltas';
  if (!linha.faltas_editavel) {
    input.disabled = true;
    input.title = 'Soma das semanas. Escolha uma semana do mes para lancar as faltas.';
    return input;
  }
  // So digito: sinal, virgula, ponto e "e" (notacao cientifica) ficam de fora.
  input.addEventListener('keydown', (evento) => {
    if (['-', '+', 'e', 'E', ',', '.'].includes(evento.key)) evento.preventDefault();
  });
  input.addEventListener('change', async () => {
    const resposta = await pywebview.api.set_faltas(linha.id, periodoId, input.value);
    if (!resposta.success) {
      hcStatus.textContent = resposta.message;
      input.value = linha.faltas;
      return;
    }
    await redesenharMantendoFoco();
    hcStatus.textContent = 'Faltas lancadas. A aba Inicio ja reflete a mudanca.';
  });
  return input;
}

// Redesenha a tabela e devolve o cursor ao campo em que ele estava (o
// "change" dispara ao sair do campo; nessa hora o foco ja foi pro proximo).
async function redesenharMantendoFoco() {
  const foco = document.activeElement;
  const destino = foco && foco.dataset && foco.dataset.gestor
    ? { gestor: foco.dataset.gestor, campo: foco.dataset.campo } : null;
  await carregarHeadcount();
  if (destino) {
    const alvo = hcCorpo.querySelector(
      `input[data-gestor="${destino.gestor}"][data-campo="${destino.campo}"]`);
    if (alvo && !alvo.disabled) { alvo.focus(); alvo.select(); }
  }
}

function campoNumero(valor, gestorId, campo, passo) {
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  if (passo) input.step = passo;
  input.value = valor;
  input.dataset.gestor = gestorId;
  input.dataset.campo = campo;
  input.addEventListener('change', async () => {
    // A tabela e redesenhada com os numeros novos; quem ja tinha ido pro
    // proximo campo (Tab) continua nele, sem perder o cursor.
    // O "change" dispara antes de o cursor chegar no proximo campo; depois
    // da gravacao ele ja esta la, e e ele que se guarda.
    await pywebview.api.update_gestor(gestorId, { [campo]: input.value });
    const foco = document.activeElement;
    const destino = foco && foco.dataset && foco.dataset.gestor
      ? { gestor: foco.dataset.gestor, campo: foco.dataset.campo } : null;
    await carregarHeadcount();
    if (destino) {
      const alvo = hcCorpo.querySelector(
        `input[data-gestor="${destino.gestor}"][data-campo="${destino.campo}"]`);
      if (alvo) { alvo.focus(); alvo.select(); }
    }
    hcStatus.textContent = 'Quadro atualizado. A aba Inicio ja reflete a mudanca.';
  });
  return input;
}

// ---- Editar e excluir gestor ----
// Os dois abrem uma faixa acima da tabela, no mesmo estilo das de
// adicionar; a linha do gestor fica destacada enquanto isso.

let hcEdicao = null;

const ICONE_EDITAR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>';
const ICONE_EXCLUIR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>';

function acoesDoGestor(linha) {
  const acoes = document.createElement('div');
  acoes.className = 'hc-gestor-acoes';
  for (const [tipo, icone, rotulo] of [
    ['editar', ICONE_EDITAR, `Editar ${linha.gestor}`],
    ['excluir', ICONE_EXCLUIR, `Excluir ${linha.gestor}`],
  ]) {
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = `hc-icone hc-icone-${tipo}`;
    botao.innerHTML = icone;
    botao.title = rotulo;
    botao.setAttribute('aria-label', rotulo);
    botao.addEventListener('click', () => abrirEdicao(tipo, linha));
    acoes.appendChild(botao);
  }
  return acoes;
}

function marcarLinhaEmEdicao() {
  hcCorpo.querySelectorAll('tr').forEach((tr) => {
    tr.classList.toggle('em-edicao', Boolean(hcEdicao) && tr.dataset.gestor === hcEdicao.id);
  });
}

function abrirEdicao(tipo, linha) {
  abrirFaixa(tipo);
  hcEdicao = { id: linha.id, nome: linha.gestor, operacao: linha.operacao_key, rotulo: linha.operacao };
  marcarLinhaEmEdicao();
  const faixa = document.getElementById(`hc-inline-${tipo}`);
  if (tipo === 'editar') {
    const operacoes = (hcTela ? hcTela.operacoes : []).filter((o) => o.key !== 'todas');
    preencherSelect(document.getElementById('hc-editar-op'), operacoes, linha.operacao_key, 'key', 'label');
    const campo = document.getElementById('hc-editar-nome');
    campo.value = linha.gestor;
    campo.focus();
    campo.select();
  } else {
    const texto = document.getElementById('hc-excluir-texto');
    texto.textContent = '';
    texto.append('Excluir ');
    const nome = document.createElement('strong');
    nome.textContent = linha.gestor;
    texto.append(nome, ` (${linha.operacao})?`);
    document.getElementById('hc-confirmar-excluir').focus();
  }
  faixa.scrollIntoView({ block: 'nearest', behavior: SEM_ANIMACAO ? 'auto' : 'smooth' });
}

async function salvarEdicao() {
  if (!hcEdicao) return;
  const nome = document.getElementById('hc-editar-nome').value.trim();
  const seletor = document.getElementById('hc-editar-op');
  if (!nome) {
    hcStatus.textContent = 'Informe o nome do gestor.';
    document.getElementById('hc-editar-nome').focus();
    return;
  }
  const resposta = await pywebview.api.edit_gestor(hcEdicao.id, nome, seletor.value);
  if (!resposta.success) {
    hcStatus.textContent = resposta.message;
    return;
  }
  const mudouOperacao = seletor.value !== hcEdicao.operacao;
  const novaOperacao = seletor.options[seletor.selectedIndex]?.text || seletor.value;
  const saiDaLista = mudouOperacao && hcEstado.operacao !== 'todas';
  abrirFaixa(null);
  await carregarHeadcount();
  hcStatus.textContent = saiDaLista
    ? `${nome} foi para ${novaOperacao} e sai desta lista. O HC digitado foi junto.`
    : mudouOperacao
      ? `${nome} agora esta em ${novaOperacao}. O HC digitado foi junto.`
      : `${nome} atualizado. As faltas da planilha ja sao ligadas pelo nome novo.`;
}

async function confirmarExclusao() {
  if (!hcEdicao) return;
  const { id, nome } = hcEdicao;
  const resposta = await pywebview.api.remove_gestor(id);
  if (!resposta.success) {
    hcStatus.textContent = resposta.message;
    return;
  }
  abrirFaixa(null);
  await carregarHeadcount();
  hcStatus.textContent = `${nome} excluido. A aba Inicio ja reflete a mudanca.`;
}

function desenharTabelaHc(tela) {
  hcTabelaTitulo.textContent = tela.visualizacao === 'mes'
    ? 'Resultado do mes por gestor · folha ponto'
    : 'Resultado semanal por gestor';
  hcContador.textContent = plural(tela.linhas.length, 'linha', 'linhas');
  // Sem gestor, a tabela so teria cabecalhos soltos: fica so a mensagem.
  hcVazio.hidden = tela.linhas.length > 0;
  document.getElementById('hc-tabela-wrap').hidden = tela.linhas.length === 0;

  hcCorpo.innerHTML = '';
  for (const linha of tela.linhas) {
    const tr = document.createElement('tr');
    if (linha.abaixo_da_meta) tr.classList.add('abaixo');

    const tdGestor = document.createElement('td');
    const caixa = document.createElement('div');
    caixa.className = 'hc-gestor';
    const avatar = document.createElement('span');
    avatar.className = 'hc-avatar';
    avatar.textContent = linha.iniciais;
    const nomes = document.createElement('div');
    const nome = document.createElement('div');
    nome.className = 'hc-gestor-nome';
    nome.textContent = linha.gestor;
    const nota = document.createElement('div');
    nota.className = 'hc-gestor-nota';
    // Com faltas digitadas nao ha "usuarios na planilha" para mostrar.
    nota.textContent = tela.faltas_manuais
      ? ''
      : `${plural(linha.usuarios, 'usuario', 'usuarios')} na planilha`;
    nota.hidden = tela.faltas_manuais;
    nomes.appendChild(nome);
    nomes.appendChild(nota);
    caixa.appendChild(avatar);
    caixa.appendChild(nomes);
    caixa.appendChild(acoesDoGestor(linha));
    tdGestor.appendChild(caixa);
    tr.appendChild(tdGestor);
    tr.dataset.gestor = linha.id;
    if (hcEdicao && hcEdicao.id === linha.id) tr.classList.add('em-edicao');

    const tdOperacao = document.createElement('td');
    const op = document.createElement('div');
    op.className = 'hc-operacao';
    op.textContent = linha.operacao;
    const per = document.createElement('div');
    per.className = 'hc-periodo';
    per.textContent = linha.periodo;
    tdOperacao.appendChild(op);
    tdOperacao.appendChild(per);
    tr.appendChild(tdOperacao);

    for (const [campo, passo] of [['hc', '1'], ['dias_uteis', '1'], ['horas_dia', '0.5']]) {
      const td = document.createElement('td');
      td.className = 'num';
      td.appendChild(tela.faltas_manuais
        ? campoQuadro(linha, campo, passo)
        : campoNumero(linha[campo], linha.id, campo, passo));
      tr.appendChild(td);
    }

    const tdFaltas = document.createElement('td');
    tdFaltas.className = 'num';
    if (tela.faltas_manuais) {
      tdFaltas.appendChild(campoQuadro(linha, 'faltas', '1'));
      tr.appendChild(tdFaltas);
    } else {
    const faltas = document.createElement('span');
    faltas.className = 'hc-faltas';
    const valorFaltas = document.createElement('span');
    valorFaltas.className = 'hc-faltas-valor';
    valorFaltas.textContent = linha.faltas;
    const selo = document.createElement('span');
    selo.className = 'hc-selo';
    selo.textContent = 'XLS';
    selo.title = 'Veio da planilha de faltas, nao e digitado';
    faltas.appendChild(valorFaltas);
    faltas.appendChild(selo);
    tdFaltas.appendChild(faltas);
    tr.appendChild(tdFaltas);
    }

    const tdResultado = document.createElement('td');
    tdResultado.className = 'num';
    const resultado = document.createElement('span');
    resultado.className = 'hc-resultado';
    const bolinha = document.createElement('span');
    bolinha.className = 'hc-bolinha';
    resultado.appendChild(bolinha);
    resultado.appendChild(document.createTextNode(hcPercentual(linha.presenteismo)));
    tdResultado.appendChild(resultado);
    tr.appendChild(tdResultado);

    hcCorpo.appendChild(tr);
  }

  hcTotal.innerHTML = '';
  if (!tela.linhas.length) return;
  const t = tela.total;
  const tr = document.createElement('tr');
  // Gestores de escalas diferentes (a espanhola trabalha os dois
  // ultimos sabados) tem dias uteis diferentes no mesmo periodo: um
  // numero so no total seria o de uma escala e nao o da linha de cima.
  // O mesmo vale para dias ou horas digitados so para um gestor na semana.
  const unicoOuVaria = (campo) => {
    const valores = new Set(tela.linhas.map((l) => l[campo]));
    return valores.size > 1 ? 'varia' : [...valores][0];
  };
  const celulas = [
    'TOTAL CONSOLIDADO',
    plural(t.gestores, 'gestor', 'gestores'),
    t.hc, unicoOuVaria('dias_uteis'), unicoOuVaria('horas_dia'), t.faltas,
  ];
  celulas.forEach((texto, indice) => {
    const td = document.createElement('td');
    if (indice >= 2) td.className = 'num';
    td.textContent = texto;
    if (texto === 'varia') {
      td.classList.add('hc-varia');
      td.title = 'Os gestores tem numeros diferentes nesta semana (escala ou valor digitado).';
    }
    tr.appendChild(td);
  });
  const tdTotal = document.createElement('td');
  tdTotal.className = 'num';
  const pill = document.createElement('span');
  pill.className = 'hc-total-pill';
  pill.textContent = hcPercentual(t.presenteismo);
  tdTotal.appendChild(pill);
  tr.appendChild(tdTotal);
  hcTotal.appendChild(tr);
}

function desenharFormulaHc(tela) {
  const m = tela.memoria;
  document.getElementById('hc-mem-disponiveis').textContent = `${m.horas_disponiveis} h`;
  document.getElementById('hc-mem-perdidas').textContent = `${m.horas_perdidas} h`;
  document.getElementById('hc-mem-efetivas').textContent = `${m.horas_efetivas} h`;
  document.getElementById('hc-mem-resultado').textContent = hcPercentual(m.presenteismo);
  document.getElementById('hc-mem-meta').textContent = hcPercentual(m.meta);
}

function desenharFuncoesHc(tela) {
  hcFuncoes.innerHTML = '';
  // Funcoes filtram a planilha de faltas; com faltas digitadas, nao se
  // aplicam (a planilha volta numa melhoria futura).
  hcFuncoes.hidden = tela.faltas_manuais || !tela.funcoes.length;
  if (tela.faltas_manuais) return;
  for (const funcao of tela.funcoes) {
    const chip = document.createElement('span');
    chip.className = 'hc-funcao-chip';
    chip.appendChild(document.createTextNode(funcao.nome));
    const operacao = document.createElement('span');
    operacao.className = 'hc-funcao-op';
    operacao.textContent = funcao.operacao_label;
    chip.appendChild(operacao);
    const remover = document.createElement('button');
    remover.type = 'button';
    remover.textContent = '×';
    remover.setAttribute('aria-label', `Remover ${funcao.nome} de ${funcao.operacao_label}`);
    remover.addEventListener('click', async () => {
      await pywebview.api.remove_funcao(funcao.nome, funcao.operacao);
      await carregarHeadcount();
    });
    chip.appendChild(remover);
    hcFuncoes.appendChild(chip);
  }
}

function desenharArquivoHc(tela) {
  if (tela.faltas_manuais) return;
  const arquivo = tela.arquivo;
  if (!arquivo) {
    hcArquivoInfo.innerHTML =
      '<p class="hc-arquivo-vazio">Sem planilha, as faltas ficam zeradas e o ' +
      'presenteismo aparece como 100%.</p>';
    hcStatus.textContent = 'Nenhuma planilha de faltas carregada.';
    return;
  }

  const r = arquivo.resumo;
  const kb = Math.max(1, Math.round(arquivo.tamanho / 1024));
  const quando = new Date(arquivo.importado_em).toLocaleString('pt-BR');

  const partes = [];
  partes.push(`<div class="hc-arquivo-nome">${arquivo.nome}</div>`);
  partes.push(`<div class="hc-arquivo-meta">${kb} KB · lido em ${quando}</div>`);
  if (arquivo.cobre_de && arquivo.cobre_ate) {
    // A planilha so tem linha em dia com ausencia; o periodo coberto e
    // deduzido. Mostrar evita a duvida de por que uma semana ficou sem
    // numero na aba Inicio.
    const data = (iso) => iso.split('-').reverse().join('/');
    partes.push(`<div class="hc-arquivo-meta">Cobre de ${data(arquivo.cobre_de)} ` +
      `a ${data(arquivo.cobre_ate)}</div>`);
  }
  partes.push('<div class="hc-contadores">' +
    `<span class="hc-contador-item"><strong>${r.linhas}</strong>linhas lidas</span>` +
    `<span class="hc-contador-item"><strong>${r.consideradas}</strong>faltas validas</span>` +
    `<span class="hc-contador-item"><strong>${r.gestores}</strong>gestores</span>` +
    `<span class="hc-contador-item"><strong>${r.dias}</strong>dias faltados</span>` +
    '</div>');

  // O que foi descartado e tao importante quanto o que entrou: um
  // filtro derrubando o arquivo inteiro precisa aparecer.
  const descartes = [];
  if (r.motivo) descartes.push(`${r.motivo} por motivo (ferias)`);
  if (r.contrato) descartes.push(`${r.contrato} por contrato (temporario)`);
  if (r.funcao) descartes.push(`${r.funcao} por funcao fora do quadro`);
  if (r.sem_data) descartes.push(`${r.sem_data} sem data`);
  if (descartes.length) {
    partes.push(`<p class="hc-descartadas">Fora da conta: ${descartes.join(' · ')}.</p>`);
  }

  if (arquivo.cobertura.length) {
    partes.push('<div class="hc-cobertura">');
    for (const item of arquivo.cobertura) {
      const marca = item.selecionado ? ' selecionado' : '';
      const status = item.status ? ` · ${item.status}` : '';
      partes.push(`<span class="hc-cobertura-item${marca}">` +
        `<span>${item.rotulo}${status}</span>` +
        `<span>${plural(item.linhas, 'linha', 'linhas')} · ${plural(item.dias, 'dia', 'dias')}</span></span>`);
    }
    partes.push('</div>');
  }

  partes.push('<button type="button" class="secondary acao" id="hc-remover-arquivo" ' +
    'style="margin-top:16px;">Remover</button>');

  hcArquivoInfo.innerHTML = partes.join('');
  document.getElementById('hc-remover-arquivo').addEventListener('click', async () => {
    await pywebview.api.clear_faltas();
    await carregarHeadcount();
  });

  hcStatus.textContent =
    `Faltas importadas de ${arquivo.nome} · ${r.linhas} linhas · ultima leitura ${quando}`;
}

// ---------------- Acoes ----------------

hcOperacao.addEventListener('change', async () => {
  hcEstado.operacao = hcOperacao.value;
  await carregarHeadcount();
});

hcMes.addEventListener('change', async () => {
  // No Resultado do Mes este seletor escolhe o ciclo, nao o mes.
  if (hcEstado.visualizacao === 'mes') {
    hcEstado.periodo_id = hcMes.value;
  } else {
    hcEstado.mes = hcMes.value;
    hcEstado.periodo_id = null;
  }
  await carregarHeadcount();
});

hcPeriodo.addEventListener('change', async () => {
  hcEstado.periodo_id = hcPeriodo.value;
  await carregarHeadcount();
});

hcVisualizacao.addEventListener('click', async (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (!botao) return;
  // O destaque anda ja no clique; os numeros chegam logo depois.
  hcVisualizacao.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b === botao));
  moverDestaque(hcVisualizacao);
  hcEstado.visualizacao = botao.dataset.visualizacao;
  hcEstado.periodo_id = null;
  await carregarHeadcount();
});

const hcNovoGestorOp = document.getElementById('hc-novo-gestor-op');
const hcNovaFuncaoOp = document.getElementById('hc-nova-funcao-op');
const SELETOR_DE_OPERACAO = { gestor: hcNovoGestorOp, funcao: hcNovaFuncaoOp };

// A operacao do gestor ou da funcao nova e escolhida na propria faixa.
// Vem marcada com a do filtro; com "Todas as Operacoes" no filtro, fica
// sem escolha e o cadastro so sai depois de escolher - antes ele caia
// calado na primeira operacao da lista.
function preencherOperacaoDaFaixa(select) {
  const operacoes = (hcTela ? hcTela.operacoes : []).filter((o) => o.key !== 'todas');
  const itens = [{ key: '', label: 'Escolha a operacao' }, ...operacoes];
  const doFiltro = hcEstado.operacao !== 'todas' ? hcEstado.operacao : '';
  preencherSelect(select, itens, doFiltro, 'key', 'label');
  select.options[0].disabled = true;
}

function abrirFaixa(qual) {
  // Uma faixa aberta por vez: adicionar gestor, adicionar funcao, editar
  // ou excluir.
  for (const tipo of ['gestor', 'funcao', 'editar', 'excluir']) {
    document.getElementById(`hc-inline-${tipo}`).hidden = qual !== tipo;
  }
  if (qual !== 'editar' && qual !== 'excluir' && hcEdicao) {
    hcEdicao = null;
    marcarLinhaEmEdicao();
  }
  if (qual === 'gestor' || qual === 'funcao') {
    preencherOperacaoDaFaixa(SELETOR_DE_OPERACAO[qual]);
    const campo = document.getElementById(qual === 'gestor' ? 'hc-novo-gestor' : 'hc-nova-funcao');
    campo.value = '';
    campo.focus();
  }
}

document.getElementById('hc-add-gestor').addEventListener('click', () => abrirFaixa('gestor'));
document.getElementById('hc-add-funcao').addEventListener('click', () => abrirFaixa('funcao'));
for (const botao of document.querySelectorAll('[data-cancelar]')) {
  botao.addEventListener('click', () => abrirFaixa(null));
}

// Botao ocupado: desabilita e mostra o giro enquanto o Python responde,
// para ninguem clicar duas vezes achando que nao pegou.
async function comCarregando(botao, acao) {
  botao.disabled = true;
  botao.classList.add('carregando');
  try {
    return await acao();
  } finally {
    botao.disabled = false;
    botao.classList.remove('carregando');
  }
}

async function confirmarFaixa(qual, valor) {
  const seletor = SELETOR_DE_OPERACAO[qual];
  const destino = seletor.value;
  if (!destino) {
    hcStatus.textContent = qual === 'gestor'
      ? 'Escolha a operacao do gestor antes de adicionar.'
      : 'Escolha a operacao da funcao antes de adicionar.';
    seletor.focus();
    return;
  }
  const resposta = qual === 'gestor'
    ? await pywebview.api.add_gestor(valor, destino)
    : await pywebview.api.add_funcao(valor, destino);
  if (!resposta.success) {
    hcStatus.textContent = resposta.message;
    return;
  }
  const nomeOperacao = seletor.options[seletor.selectedIndex]?.text || destino;
  abrirFaixa(null);
  await carregarHeadcount();
  hcStatus.textContent = qual === 'gestor'
    ? `${valor} cadastrado em ${nomeOperacao}. Preencha o HC: as faltas ja vem da planilha carregada.`
    : `${valor} passa a contar como falta em ${nomeOperacao}, ja nesta planilha e na aba Inicio.`;
}

for (const [botao, campo, qual] of [
  ['hc-confirmar-gestor', 'hc-novo-gestor', 'gestor'],
  ['hc-confirmar-funcao', 'hc-nova-funcao', 'funcao'],
]) {
  document.getElementById(botao).addEventListener('click', async () => {
    const valor = document.getElementById(campo).value.trim();
    if (!valor) {
      hcStatus.textContent = qual === 'gestor' ? 'Informe o nome do gestor.' : 'Informe o nome da funcao.';
      document.getElementById(campo).focus();
      return;
    }
    await comCarregando(document.getElementById(botao), () => confirmarFaixa(qual, valor));
  });
}

for (const seletor of [hcNovoGestorOp, hcNovaFuncaoOp, document.getElementById('hc-editar-op')]) {
  seletor.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') abrirFaixa(null);
  });
}

const hcConfirmarEditar = document.getElementById('hc-confirmar-editar');
const hcConfirmarExcluir = document.getElementById('hc-confirmar-excluir');
hcConfirmarEditar.addEventListener('click', () => comCarregando(hcConfirmarEditar, salvarEdicao));
hcConfirmarExcluir.addEventListener('click', () => comCarregando(hcConfirmarExcluir, confirmarExclusao));
document.getElementById('hc-editar-nome').addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter') {
    evento.preventDefault();
    comCarregando(hcConfirmarEditar, salvarEdicao);
  } else if (evento.key === 'Escape') {
    abrirFaixa(null);
  }
});
hcConfirmarExcluir.addEventListener('keydown', (evento) => {
  if (evento.key === 'Escape') abrirFaixa(null);
});

for (const [id, qual] of [['hc-novo-gestor', 'gestor'], ['hc-nova-funcao', 'funcao']]) {
  document.getElementById(id).addEventListener('keydown', async (evento) => {
    if (evento.key === 'Enter') {
      evento.preventDefault();
      const valor = evento.target.value.trim();
      if (valor) await confirmarFaixa(qual, valor);
    } else if (evento.key === 'Escape') {
      abrirFaixa(null);
    }
  });
}

document.getElementById('hc-limpar').addEventListener('click', async () => {
  await pywebview.api.clear_faltas();
  await carregarHeadcount();
  hcStatus.textContent = 'Faltas removidas. Sem planilha, o presenteismo volta a 100%.';
});

// O presenteismo nao precisa mais ser "aplicado": a aba Inicio calcula
// na hora, a partir do quadro e das faltas. O botao leva direto pra la,
// ja na operacao que esta aberta aqui.
document.getElementById('hc-calcular').addEventListener('click', async () => {
  if (hcEstado.operacao && hcEstado.operacao !== 'todas') {
    homeOperationSelect.value = hcEstado.operacao;
  }
  await showPage('home');
});

document.getElementById('hc-toggle-formula').addEventListener('click', (evento) => {
  const corpo = document.getElementById('hc-formula-corpo');
  corpo.hidden = !corpo.hidden;
  evento.target.textContent = corpo.hidden ? 'mostrar' : 'ocultar';
});

document.getElementById('hc-ajuda-faltas').addEventListener('click', () => {
  hcStatus.textContent =
    'As faltas vem da planilha de ausencias: uma linha por dia de falta, com ' +
    'GESTOR_NAME, NOME, FUNCAO, MOTIVO, CONTRACT e ABS_DATE. Ferias, temporarios ' +
    'e funcoes fora do quadro nao entram.';
});

// ---------------- Arquivo ----------------

async function enviarArquivoFaltas(arquivo) {
  if (!arquivo) return;
  hcStatus.textContent = `Lendo ${arquivo.name}...`;

  const base64 = await new Promise((resolve, reject) => {
    const leitor = new FileReader();
    leitor.onload = () => resolve(leitor.result);
    leitor.onerror = () => reject(leitor.error);
    // Vai como conteudo e nao como caminho: dentro da janela do app o
    // navegador nao entrega o caminho do arquivo arrastado.
    leitor.readAsDataURL(arquivo);
  });

  const resposta = await pywebview.api.import_faltas(arquivo.name, base64);
  if (!resposta.success) {
    hcStatus.textContent = resposta.message;
    return;
  }
  await carregarHeadcount();
  hcStatus.textContent =
    `${arquivo.name} lido. O presenteismo de cada semana e de cada ciclo ja esta na aba Inicio.`;
}

hcDropzone.addEventListener('click', () => hcArquivoInput.click());
hcDropzone.addEventListener('keydown', (evento) => {
  if (evento.key === 'Enter' || evento.key === ' ') {
    evento.preventDefault();
    hcArquivoInput.click();
  }
});
hcArquivoInput.addEventListener('change', () => enviarArquivoFaltas(hcArquivoInput.files[0]));

for (const evento of ['dragenter', 'dragover']) {
  hcDropzone.addEventListener(evento, (e) => {
    e.preventDefault();
    hcDropzone.classList.add('arrastando');
  });
}
for (const evento of ['dragleave', 'drop']) {
  hcDropzone.addEventListener(evento, (e) => {
    e.preventDefault();
    hcDropzone.classList.remove('arrastando');
  });
}
hcDropzone.addEventListener('drop', (e) => enviarArquivoFaltas(e.dataTransfer.files[0]));
