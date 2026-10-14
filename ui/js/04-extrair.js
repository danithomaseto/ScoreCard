// As duas abas de extracao mostram o mesmo historico, cada uma com o
// seu <tbody>.
// O historico vem uma vez do Python e os filtros (operacao, tipo e
// resultado) so escolhem o que aparece.
let historicoCompleto = [];

async function loadHistoryTable(tbody = historyTableBody) {
  historicoCompleto = await comEsqueleto(tbody, 7, () => pywebview.api.get_report_history());
  desenharHistorico(tbody);
  desenharRodape();
}

function filtrosDoHistorico(tbody) {
  return document.querySelector(`.historico-filtros[data-historico="${tbody.id}"]`);
}

function preencherFiltrosDoHistorico(caixa) {
  const unicos = (campo) => [...new Set(historicoCompleto.map((h) => h[campo]).filter(Boolean))];
  const ordemDoTipo = (rotulo) => {
    const i = Object.values(ROTULO_DO_TIPO).indexOf(rotulo === 'Indiretas' ? 'Horas Indiretas' : rotulo);
    return i < 0 ? 99 : i;
  };
  const listas = {
    operacao: unicos('operation').sort((a, b) => a.localeCompare(b, 'pt-BR')),
    tipo: unicos('period_type').sort((a, b) => ordemDoTipo(a) - ordemDoTipo(b)),
  };
  for (const [filtro, valores] of Object.entries(listas)) {
    const select = caixa.querySelector(`[data-filtro="${filtro}"]`);
    const escolhido = select.value;
    const primeiro = select.options[0];
    select.replaceChildren(primeiro);
    for (const valor of valores) {
      const opcao = document.createElement('option');
      opcao.value = valor;
      opcao.textContent = valor;
      select.appendChild(opcao);
    }
    select.value = valores.includes(escolhido) ? escolhido : '';
  }
}

function desenharHistorico(tbody) {
  const caixa = filtrosDoHistorico(tbody);
  if (caixa) preencherFiltrosDoHistorico(caixa);
  const filtro = (nome) => (caixa ? caixa.querySelector(`[data-filtro="${nome}"]`).value : '');
  const history = historicoCompleto.filter((h) =>
    (!filtro('operacao') || h.operation === filtro('operacao'))
    && (!filtro('tipo') || h.period_type === filtro('tipo'))
    && (!filtro('status') || (h.status || 'success') === filtro('status')));
  const contador = caixa && caixa.parentElement.querySelector('.hc-contador');
  if (contador) {
    contador.textContent = history.length === historicoCompleto.length
      ? plural(historicoCompleto.length, 'extração', 'extrações')
      : `${history.length} de ${historicoCompleto.length}`;
  }
  tbody.innerHTML = '';
  if (!history.length) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 7;
    cell.className = 'empty-history-msg';
    cell.textContent = historicoCompleto.length
      ? 'Nenhuma extração com esses filtros.'
      : 'Nenhuma extração registrada ainda.';
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
    row.appendChild(makeCell(entry.agrupamento || entry.group_by || '-'));
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

document.querySelectorAll('.historico-filtros').forEach((caixa) => {
  caixa.addEventListener('change', () => desenharHistorico(document.getElementById(caixa.dataset.historico)));
});

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

// 84 -> "1 min 24 s": o resumo do fim se le como frase.
function duracaoPorExtenso(segundos) {
  const total = Math.max(0, Math.round(Number(segundos) || 0));
  if (total < 60) return `${total} s`;
  const minutos = Math.floor(total / 60);
  const resto = total % 60;
  return resto ? `${minutos} min ${resto} s` : `${minutos} min`;
}

// O cartao do fim: quanto tempo levou, o que foi extraido e o arquivo.
function mostrarResumoDaExtracao(result, classe) {
  const caixa = document.getElementById('extracao-resumo');
  const segundos = Number(result.duration_seconds) || 0;
  const tempo = duracaoPorExtenso(segundos);
  let titulo = `Concluída em ${tempo}`;
  if (classe === 'warning') titulo = `Concluída em ${tempo}, sem indicador`;
  if (classe === 'error') titulo = segundos ? `Falhou depois de ${tempo}` : 'Não começou';
  const arquivo = result.file_path ? String(result.file_path).split(/[\\/]/).pop() : '';
  document.getElementById('extracao-resumo-titulo').textContent = titulo;
  document.getElementById('extracao-resumo-detalhe').textContent =
    [result.operation_label, result.period_type, result.period_label].filter(Boolean).join(' · ');
  document.getElementById('extracao-resumo-arquivo').textContent = arquivo ? `${arquivo} · arquivo na pasta` : '';
  caixa.className = `extracao-resumo ${classe}`;
  caixa.hidden = false;
  reiniciarAnimacao(caixa, 'entrando');
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
      // "Vários filtros" e de uma operacao so: marcar uma desmarca a outra.
      if (multiModo === 'filtros' && checkbox.checked) {
        multiOperationsEl.querySelectorAll('input[type="checkbox"]').forEach((outro) => {
          if (outro !== checkbox && outro.checked) {
            outro.checked = false;
            outro.parentElement.classList.remove('selected');
          }
        });
      }
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

// Agrupamento de cada tipo de extracao, fixo pelo sistema (o mesmo de
// config/operations.py, AGRUPAMENTOS). So o Month usa o Group By 1
// escolhido no campo; nos outros o campo some e fica a nota com o
// agrupamento e a pasta.
const AGRUPAMENTO_FIXO = {
  week: ['Week', 'Supervisor', 'User ID'],
  peak: ['Report Date'],
  indiretas: ['Week', 'Job Code'],
  gestor_week: ['Week', 'Supervisor', 'User ID'],
  gestor_month: ['Supervisor', 'User ID'],
  turno_week: ['Week', 'Shift', 'User ID'],
  turno_month: ['Shift', 'User ID'],
};
const PASTA_DO_TIPO = {
  week: 'Week', month: 'Month', peak: 'Dias de Pico', indiretas: 'Indiretas',
  gestor_week: 'Gestor › Week', gestor_month: 'Gestor › Month',
  turno_week: 'Turno › Week', turno_month: 'Turno › Month',
};
const ROTULO_DO_TIPO = {
  week: 'Week', month: 'Month', peak: 'Dias de Pico', indiretas: 'Horas Indiretas',
  gestor_week: 'Gestor · Week', gestor_month: 'Gestor · Month',
  turno_week: 'Turno · Week', turno_month: 'Turno · Month',
};
// Os tipos na ordem da tela (e da fila do "Vários filtros").
const ORDEM_DOS_TIPOS = Object.keys(ROTULO_DO_TIPO);

// Mostra o campo de Group By (so no Month) ou a nota do agrupamento fixo.
// tipos e a lista de tipos escolhidos: um so no modo normal, varios no
// "Vários filtros".
function mostrarAgrupamento(select, tipos) {
  const rotulo = document.querySelector(`label[for="${select.id}"]`);
  const nota = select.nextElementSibling;
  const comMonth = tipos.includes('month');
  select.hidden = !comMonth;
  select.disabled = !comMonth;
  if (rotulo) {
    rotulo.textContent = comMonth
      ? (tipos.length > 1 ? 'Group By 1 do Month' : 'Group By 1')
      : 'Agrupamento';
  }
  if (!nota || !nota.classList.contains('nota-agrupamento-fixo')) return;
  const fixos = tipos.filter((t) => AGRUPAMENTO_FIXO[t]);
  nota.hidden = !fixos.length;
  const texto = nota.querySelector('.nota-agrupamento-texto');
  if (tipos.length === 1 && fixos.length === 1) {
    const tipo = fixos[0];
    texto.textContent = `Agrupamento fixo: ${AGRUPAMENTO_FIXO[tipo].join(' › ')}. O arquivo vai para a pasta ${PASTA_DO_TIPO[tipo]}.`;
  } else if (fixos.length) {
    texto.textContent = comMonth
      ? 'Os outros tipos têm agrupamento fixo e cada um vai para a sua pasta.'
      : 'Todos com agrupamento fixo; cada tipo vai para a sua pasta.';
  }
}

function escolherPeriodo(botoes, select, periodo) {
  botoes.forEach((el) => el.classList.toggle('active', el.dataset.period === periodo));
  mostrarAgrupamento(select, [periodo]);
}

periodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => escolherPeriodo(periodOptionEls, groupBySelect, btn.dataset.period));
});

// ---------------------------------------------------------------
// Extrair Multiplos: varias operacoes ou varios filtros
// ---------------------------------------------------------------
// "Várias operações": o mesmo tipo de extracao para as operacoes
// marcadas. "Vários filtros": uma operacao e varios tipos (Week, Month,
// Gestor...) em sequencia, com as mesmas datas.

let multiModo = 'operacoes';
const multiModoEl = document.getElementById('multi-modo');

function tiposEscolhidosNoMulti() {
  return ORDEM_DOS_TIPOS.filter((tipo) =>
    Array.from(multiPeriodOptionEls).some((b) => b.dataset.period === tipo && b.classList.contains('active')));
}

multiPeriodOptionEls.forEach((btn) => {
  btn.addEventListener('click', () => {
    if (multiModo === 'filtros') {
      // Varios de uma vez; o ultimo marcado nao desmarca (fila vazia).
      const ativos = tiposEscolhidosNoMulti();
      if (btn.classList.contains('active') && ativos.length === 1) return;
      btn.classList.toggle('active');
      btn.setAttribute('aria-pressed', btn.classList.contains('active'));
      mostrarAgrupamento(multiGroupBySelect, tiposEscolhidosNoMulti());
      refreshMultiQueue();
    } else {
      escolherPeriodo(multiPeriodOptionEls, multiGroupBySelect, btn.dataset.period);
    }
  });
});

function trocarModoMulti(modo) {
  if (modo === multiModo) return;
  multiModo = modo;
  const filtros = modo === 'filtros';
  multiModoEl.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b.dataset.modo === modo));
  moverDestaque(multiModoEl);
  document.getElementById('page-multi').classList.toggle('modo-filtros', filtros);
  document.getElementById('multi-subtitulo').textContent = filtros
    ? 'Escolha uma operação e marque vários tipos de extração (Week, Month, Gestor...): todos rodam em sequência, com as mesmas datas.'
    : 'Selecione várias operações e extraia todas em sequência, usando os mesmos filtros.';
  document.getElementById('multi-operacoes-rotulo').textContent = filtros ? 'Operação' : 'Operações';
  document.getElementById('multi-operacoes-acoes').hidden = filtros;
  document.getElementById('multi-periodo-rotulo').textContent = filtros
    ? 'Tipos de extração (marque quantos quiser)' : 'Período do indicador';

  // Operacoes: no modo filtros fica so uma (a primeira marcada).
  if (filtros) {
    const marcadas = multiOperationsEl.querySelectorAll('input[type="checkbox"]:checked');
    marcadas.forEach((c, i) => {
      if (i > 0) { c.checked = false; c.parentElement.classList.remove('selected'); }
    });
  }
  multiOperationsEl.querySelectorAll('input[type="checkbox"]').forEach((c) => {
    c.setAttribute('role', filtros ? 'radio' : 'checkbox');
  });
  // Tipos: no modo operacoes volta a ficar um so (o primeiro marcado).
  if (!filtros) {
    const primeiro = tiposEscolhidosNoMulti()[0] || 'week';
    escolherPeriodo(multiPeriodOptionEls, multiGroupBySelect, primeiro);
    multiPeriodOptionEls.forEach((b) => b.removeAttribute('aria-pressed'));
  } else {
    multiPeriodOptionEls.forEach((b) => b.setAttribute('aria-pressed', b.classList.contains('active')));
    mostrarAgrupamento(multiGroupBySelect, tiposEscolhidosNoMulti());
  }
  refreshMultiQueue();
}

multiModoEl.addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (botao) trocarModoMulti(botao.dataset.modo);
});
window.addEventListener('resize', () => moverDestaque(multiModoEl));

function getSelectedMultiPeriod() {
  const active = document.querySelector('#multi-period-options .period-option.active');
  return active ? active.dataset.period : 'week';
}

// Estado inicial dos dois campos de agrupamento: Week, fixo.
mostrarAgrupamento(groupBySelect, ['week']);
mostrarAgrupamento(multiGroupBySelect, ['week']);

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
  const filtros = multiModo === 'filtros';

  if (!selected.length) {
    const empty = document.createElement('p');
    empty.className = 'subtitle';
    empty.textContent = filtros
      ? 'Escolha a operação ao lado para ver a fila aqui.'
      : 'Selecione as operações ao lado para ver a fila aqui.';
    multiStepsEl.appendChild(empty);
    multiProgressDetailEl.textContent = 'Nenhuma extração em andamento';
    multiProgressPercentEl.textContent = '0%';
    return;
  }

  // No "Vários filtros" a fila e de tipos de extracao da operacao escolhida.
  const fila = filtros
    ? tiposEscolhidosNoMulti().map((tipo) => ({ titulo: ROTULO_DO_TIPO[tipo], nota: `${selected[0].label} · pasta ${PASTA_DO_TIPO[tipo]}` }))
    : selected.map((op) => ({ titulo: op.label, nota: 'Na fila' }));

  fila.forEach((item, index) => {
    const step = document.createElement('div');
    step.className = 'step entrando';
    step.style.animationDelay = `${index * 40}ms`;

    const number = document.createElement('div');
    number.className = 'step-number';
    number.textContent = String(index + 1);

    const content = document.createElement('div');
    content.className = 'step-content';
    const title = document.createElement('div');
    title.className = 'step-title';
    title.textContent = item.titulo;
    const subtitle = document.createElement('div');
    subtitle.className = 'step-subtitle';
    subtitle.textContent = item.nota;
    content.appendChild(title);
    content.appendChild(subtitle);

    step.appendChild(number);
    step.appendChild(content);
    multiStepsEl.appendChild(step);
  });

  multiProgressDetailEl.textContent = filtros
    ? `${plural(fila.length, 'extração', 'extrações')} de ${selected[0].label} na fila`
    : `${selected.length} operação(ões) na fila`;
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
    subtitle.textContent = data.status === 'success' ? 'Concluída' : data.step;
    multiProgressPercentEl.textContent = `${Math.round(((data.index + 1) / data.total) * 100)}%`;
  }

  multiProgressDetailEl.textContent = `${data.index + 1} de ${data.total} - ${data.operation_label}`;
  const feitas = data.status === 'running' ? data.index : data.index + 1;
  extracaoAndou(`${data.index + 1} de ${data.total} · ${data.operation_label}`, feitas / data.total);
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
      // No "Vários filtros" os tipos sao escolhidos a mao: so as datas mudam.
      if (isMulti && multiModo === 'filtros') return;

      // "Mes passado" com Dias de Pico escolhido continua no pico: o pico
      // tambem e de um mes inteiro.
      const atual = Array.from(periodButtons).find((el) => el.classList.contains('active'));
      const noPico = atual && atual.dataset.period === 'peak';
      const tipo = atual ? atual.dataset.period : 'week';
      // Gestor e Turno trocam so entre Week e Month deles.
      const grupo = tipo.startsWith('gestor') ? 'gestor_' : tipo.startsWith('turno') ? 'turno_' : null;
      const alvo = grupo ? `${grupo}${mensal ? 'month' : 'week'}`
        : mensal ? (noPico ? 'peak' : 'month') : 'week';
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

  const escolha = await perguntar({
    icone: 'pasta',
    titulo: 'Escolha a pasta do SharePoint',
    texto: 'Antes de extrair, escolha a pasta do SharePoint/OneDrive onde os relatórios vão ser salvos.\n'
      + 'Cada operação usa a sua subpasta dentro dela. Dá para trocar depois em Configurações.',
    botoes: [{ rotulo: 'Agora não', valor: false }, { rotulo: 'Escolher pasta', valor: true, principal: true }],
  });
  if (!escolha) return false;
  const result = await pywebview.api.choose_sharepoint_folder();
  if (result.success) {
    folderPathEl.textContent = result.folder;
    sincronizarSharePoint({ forcar: true });
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
    showStatus(loginStatus, 'Preencha usuário e senha.', 'error');
    tremerLogin();
    return;
  }

  loginBtn.disabled = true;
  loginBtn.classList.add('carregando');
  loginBtn.setAttribute('aria-busy', 'true');
  try {
    const result = await pywebview.api.login(username, password);
    if (!result.success) {
      showStatus(loginStatus, result.message || 'Falha no login.', 'error');
      tremerLogin();
      return;
    }
    loginPassword.value = '';
    loginPassword.type = 'password';
    document.getElementById('login-olho').setAttribute('aria-pressed', 'false');
    await entrarNoApp(showApp);
    avisar(`${periodoDoDia().texto}, ${username}`, 'ok', 'A senha fica só na memória enquanto o app está aberto.');
    await ensureFolderConfigured();
  } finally {
    loginBtn.disabled = false;
    loginBtn.classList.remove('carregando');
    loginBtn.removeAttribute('aria-busy');
  }
});

// Chamado pelo Python (api.py) a cada etapa da automacao, em tempo
// real, enquanto run_extraction ainda esta rodando. Mapeia a frase
// recebida pra uma das 4 etapas do painel "Andamento".
window.updateProgress = function (text) {
  // Extracao disparada da aba Horas Indiretas: o andamento aparece la.
  if (indExtraindo) progressoIndiretas(text);
  progressDetailEl.textContent = text;
  const lower = semAcento(text);

  if (lower.startsWith('falhou')) {
    markStepsError();
    setBadge('error', 'Falha');
    return;
  }

  const stepIndex = PROGRESS_STEPS.findIndex((def) => def.match(lower));
  if (stepIndex === -1) return;
  extracaoAndou(stepEls[stepIndex].querySelector('.step-title').textContent,
    (stepIndex + 1) / PROGRESS_STEPS.length);

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
    showStatus(runStatus, 'A "Data inicial" não pode ser depois da "Data final".', 'error');
    return;
  }
  // yyyy-mm-dd (formato nativo do <input type="date">) - a conversao
  // pro formato que o Summary espera (dd/mm/yyyy) acontece no Python,
  // perto de onde o campo de verdade e preenchido.
  const dateRange = { from_date: fromDateInput.value, to_date: toDateInput.value };

  if (outraExtracaoRodando()) return;
  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(runStatus, 'É necessário selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  extracaoComecou('extract', `${operationSelect.selectedOptions[0]?.text || ''} · ${ROTULO_DO_TIPO[getSelectedPeriod()] || ''}`);
  runBtn.disabled = true;
  runBtn.querySelector('.btn-texto').textContent = 'Executando...';
  resetSteps();
  document.getElementById('extracao-resumo').hidden = true;
  setBadge('running', 'Em andamento');
  progressDetailEl.textContent = 'Iniciando a extração...';
  progressPercentEl.textContent = '0%';
  try {
    const result = await pywebview.api.run_extraction(operationSelect.value, dateRange, groupBySelect.value, getSelectedPeriod());
    conferirSenhaRecusada(result);
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
    mostrarResumoDaExtracao(result, desfecho.classe);
    extracaoTerminou(desfecho.classe, desfecho.rotulo);
    await loadHistoryTable();
  } catch (err) {
    markStepsError();
    setBadge('error', 'Falha');
    showStatus(runStatus, 'Erro inesperado: ' + err.message, 'error');
    extracaoTerminou('error', 'Falha');
  } finally {
    runBtn.disabled = false;
    runBtn.querySelector('.btn-texto').textContent = 'Iniciar extração';
  }
});

multiRunBtn.addEventListener('click', async () => {
  multiRunStatus.hidden = true;
  multiRunActions.hidden = true;

  const selected = getSelectedOperations();
  const filtros = multiModo === 'filtros';
  if (!selected.length) {
    showStatus(multiRunStatus, filtros ? 'Escolha a operação.' : 'Selecione pelo menos uma operação.', 'error');
    return;
  }
  if (!multiFromDateInput.value || !multiToDateInput.value) {
    showStatus(multiRunStatus, 'Preencha a Data inicial e a Data final.', 'error');
    return;
  }
  if (multiFromDateInput.value > multiToDateInput.value) {
    showStatus(multiRunStatus, 'A "Data inicial" não pode ser depois da "Data final".', 'error');
    return;
  }
  const dateRange = { from_date: multiFromDateInput.value, to_date: multiToDateInput.value };

  if (outraExtracaoRodando()) return;
  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(multiRunStatus, 'É necessário selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  extracaoComecou('multi', filtros ? selected[0].label : 'Fila');
  refreshMultiQueue();
  setMultiBadge('running', 'Em andamento');
  multiProgressDetailEl.textContent = 'Iniciando a fila...';
  multiProgressPercentEl.textContent = '0%';
  multiRunBtn.disabled = true;
  multiRunBtn.querySelector('.btn-texto').textContent = 'Executando...';
  multiStopBtn.hidden = false;
  multiStopBtn.disabled = false;
  multiStopBtn.textContent = 'Parar após a atual';
  try {
    const result = filtros
      ? await pywebview.api.run_multi_filters(selected[0].key, tiposEscolhidosNoMulti(), dateRange, multiGroupBySelect.value)
      : await pywebview.api.run_multi_extraction(
        selected.map((op) => op.key),
        dateRange,
        multiGroupBySelect.value,
        getSelectedMultiPeriod(),
      );
    conferirSenhaRecusada(result);
    // Tres desfechos, como na extracao unica: falha em vermelho; parada a
    // pedido ou arquivo salvo sem indicador em amarelo; o resto em verde.
    let badgeTexto = 'Concluída';
    let classe = 'success';
    if ((result.failed || 0) > 0 || (!result.success && !result.cancelled)) {
      badgeTexto = 'Com falhas';
      classe = 'error';
    } else if (result.cancelled) {
      badgeTexto = 'Interrompida';
      classe = 'warning';
    } else if ((result.sem_indicador || 0) > 0) {
      badgeTexto = 'Sem indicador';
      classe = 'warning';
    }
    setMultiBadge(classe, badgeTexto);
    multiProgressPercentEl.textContent = '100%';
    multiProgressDetailEl.textContent = result.message;
    showStatus(multiRunStatus, result.message, classe);
    extracaoTerminou(classe, badgeTexto);
    showRunActions(multiRunActions, {
      houveSucesso: (result.succeeded || 0) > 0,
      houveFalha: (result.failed || 0) > 0,
    });
    await loadHistoryTable(multiHistoryTableBody);
  } catch (err) {
    setMultiBadge('error', 'Falha');
    showStatus(multiRunStatus, 'Erro inesperado: ' + err.message, 'error');
    extracaoTerminou('error', 'Falha');
  } finally {
    multiRunBtn.disabled = false;
    multiRunBtn.querySelector('.btn-texto').textContent = 'Iniciar extração';
    multiStopBtn.hidden = true;
  }
});

multiStopBtn.addEventListener('click', async () => {
  multiStopBtn.disabled = true;
  multiStopBtn.textContent = 'Parando...';
  // A operacao em andamento termina normalmente; a fila para antes da
  // proxima, pra nao deixar um download pela metade.
  multiProgressDetailEl.textContent = 'Vai parar quando a operação atual terminar...';
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
  const doLogin = document.getElementById('login-versao');
  if (doLogin) doLogin.textContent = info.versao;
}

chooseFolderBtn.addEventListener('click', async () => {
  const result = await pywebview.api.choose_sharepoint_folder();
  if (result.success) {
    folderPathEl.textContent = result.folder;
    sincronizarSharePoint({ forcar: true }); // pasta nova: le o que ja tem nela
  }
});

// Sair fica no menu da conta (canto direito da barra amarela).
async function sairDaConta() {
  await pywebview.api.logout();
  loginUsername.value = '';
  loginPassword.value = '';
  showLogin();
}

window.addEventListener('pywebviewready', async () => {
  window.pywebview.api = comBarraDeCarregamento(window.pywebview.api);
  carregarVersao();
  await carregarPreferencias();
  showLogin();
  encerrarAbertura();
});
