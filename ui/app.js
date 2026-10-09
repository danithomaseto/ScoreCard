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
    // Os valores da linha "pulam" logo depois dela entrar.
    tr.style.setProperty('--atraso', `${i * 30 + 90}ms`);
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
  // "group by 1" cobre o primeiro nivel de qualquer tipo; o segundo e o
  // terceiro so existem em alguns, e quando nao acontecem o passo
  // simplesmente nao acende.
  { key: 'groupby1', match: (t) => t.includes('group by 1') },
  { key: 'groupby2', match: (t) => t.includes('segundo nivel') || t.includes('group by 2') },
  { key: 'groupby3', match: (t) => t.includes('terceiro nivel') || t.includes('group by 3') },
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
  // Em tela baixa o aviso pode nascer abaixo da dobra (embaixo do botao
  // Iniciar extracao, por exemplo) e ninguem ve.
  requestAnimationFrame(() => el.scrollIntoView({ block: 'nearest', behavior: SEM_ANIMACAO ? 'auto' : 'smooth' }));
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
        alert(result.message || 'Não foi possível abrir.');
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
  (loginUsername.value ? loginPassword : loginUsername).focus();
  // Com a abertura na frente, o card entra quando ela sai.
  if (!document.getElementById('abertura')) animarEntradaDoLogin();
}

// Caps Lock ligado na senha: avisa antes de errar (senha errada repetida
// pode bloquear o usuario no Summary).
function avisarCapsLock(evento) {
  if (typeof evento.getModifierState !== 'function') return;
  document.getElementById('login-caps').hidden = !evento.getModifierState('CapsLock');
}
loginPassword.addEventListener('keydown', avisarCapsLock);
loginPassword.addEventListener('keyup', avisarCapsLock);
loginPassword.addEventListener('blur', () => { document.getElementById('login-caps').hidden = true; });

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
      await carregarCoverage();
    } catch (err) {
      // pre-carregar e so um adiantamento; a aba carrega de novo ao abrir
    }
  });
}

// ---------------------------------------------------------------
// Erros da tela
// ---------------------------------------------------------------
// Um erro de JavaScript ou uma chamada ao Python que falhou nao pode
// sumir em silencio: aparece um aviso no canto e vai para o log (e dali
// para o "Gerar diagnostico").

function avisarErro(texto) {
  avisar(texto, 'erro');
}

// Avisos rapidos no canto inferior direito: copiado, erro... Somem
// sozinhos; no maximo quatro na tela.
const ICONES_DO_AVISO = {
  ok: '<polyline points="20 6 9 17 4 12"></polyline>',
  erro: '<circle cx="12" cy="12" r="9"></circle><line x1="12" y1="8" x2="12" y2="12.5"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>',
  info: '<circle cx="12" cy="12" r="9"></circle><line x1="12" y1="11" x2="12" y2="16"></line><line x1="12" y1="8" x2="12.01" y2="8"></line>',
};

function avisar(texto, tipo = 'info', detalhe = '') {
  const area = document.getElementById('avisos');
  if (!area) return;
  const aviso = document.createElement('div');
  aviso.className = `aviso ${tipo}`;
  aviso.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
  aviso.innerHTML = `<svg class="aviso-icone" viewBox="0 0 24 24" aria-hidden="true">${ICONES_DO_AVISO[tipo] || ICONES_DO_AVISO.info}</svg>`;
  const corpo = document.createElement('div');
  corpo.textContent = texto;
  if (detalhe) {
    const pequeno = document.createElement('span');
    pequeno.className = 'aviso-detalhe';
    pequeno.textContent = detalhe;
    corpo.appendChild(pequeno);
  }
  aviso.appendChild(corpo);
  area.appendChild(aviso);
  while (area.children.length > 4) area.firstElementChild.remove();
  const sair = () => {
    if (!aviso.isConnected || aviso.classList.contains('saindo')) return;
    aviso.classList.add('saindo');
    setTimeout(() => aviso.remove(), SEM_ANIMACAO ? 0 : 260);
  };
  aviso.addEventListener('click', sair);
  setTimeout(sair, tipo === 'erro' ? 6000 : 2800);
}

function registrarErro(origem, erro) {
  const mensagem = (erro && (erro.stack || erro.message)) || String(erro);
  // Avisos do proprio navegador, sem efeito na tela.
  if (/ResizeObserver loop/.test(mensagem)) return;
  avisarErro('Algo deu errado nesta tela. O detalhe foi para o log (Configurações > Gerar diagnóstico).');
  try {
    if (window.pywebview && pywebview.api && pywebview.api.log_erro_tela) {
      pywebview.api.log_erro_tela(origem, String(mensagem).slice(0, 4000));
    }
  } catch (e) {
    // sem ponte com o Python, fica so o aviso
  }
}

window.addEventListener('error', (evento) => registrarErro('erro', evento.error || evento.message));
window.addEventListener('unhandledrejection', (evento) => registrarErro('promessa', evento.reason));

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
  animarEntradaDaPagina(pageName);
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

// ---------------------------------------------------------------
// Animacoes: abertura, login, entrada no app e numeros dos cards
// ---------------------------------------------------------------
// So apresentacao. Com "reduzir movimento" ligado no Windows nada disso
// roda (SEM_ANIMACAO), e a tela funciona igual.

const esperar = (ms) => new Promise((resolver) => setTimeout(resolver, ms));

// A abertura toca enquanto o app carrega: fica no minimo o tempo da
// animacao e sai assim que a ponte com o Python estiver pronta.
const INICIO_DA_ABERTURA = performance.now();
const DURACAO_DA_ABERTURA = 2300;

function encerrarAbertura() {
  const abertura = document.getElementById('abertura');
  if (!abertura || abertura.classList.contains('saindo')) return;
  if (SEM_ANIMACAO) {
    abertura.remove();
    animarEntradaDoLogin();
    return;
  }
  const falta = Math.max(0, DURACAO_DA_ABERTURA - (performance.now() - INICIO_DA_ABERTURA));
  setTimeout(() => {
    abertura.classList.add('saindo');
    // O card do login entra enquanto a abertura sobe.
    setTimeout(animarEntradaDoLogin, 260);
    setTimeout(() => abertura.remove(), 800);
  }, falta);
}
// Se a ponte com o Python demorar demais, a abertura nao prende a tela.
setTimeout(() => {
  const abertura = document.getElementById('abertura');
  if (abertura && !abertura.classList.contains('saindo')) encerrarAbertura();
}, 9000);

const loginCard = document.getElementById('login-card');

function reiniciarAnimacao(elemento, classe) {
  elemento.classList.remove(classe);
  void elemento.offsetWidth; // forca o navegador a recomecar a animacao
  elemento.classList.add(classe);
}

function animarEntradaDoLogin() {
  if (SEM_ANIMACAO || loginView.hidden) return;
  loginCard.classList.remove('confirmado', 'tremendo');
  reiniciarAnimacao(loginCard, 'entrando');
}

function tremerLogin() {
  if (SEM_ANIMACAO) return;
  loginCard.classList.remove('entrando');
  reiniciarAnimacao(loginCard, 'tremendo');
}

// Login aceito: o card confirma, a cortina amarela cobre a tela, o app
// monta por baixo e a cortina sai revelando o app, que entra por partes.
async function entrarNoApp(mostrarApp) {
  const cortina = document.getElementById('cortina');
  if (SEM_ANIMACAO || !cortina) {
    await mostrarApp();
    return;
  }
  loginCard.classList.remove('entrando', 'tremendo');
  loginCard.classList.add('confirmado');
  await esperar(300);
  cortina.className = 'cortina cobrindo';
  await esperar(560);
  try {
    await mostrarApp();
  } finally {
    loginCard.classList.remove('confirmado');
    reiniciarAnimacao(appView, 'app-entrando');
    cortina.className = 'cortina saindo';
    setTimeout(() => { cortina.className = 'cortina'; }, 700);
    setTimeout(() => appView.classList.remove('app-entrando'), 1600);
  }
}

// Cada item do menu entra um pouco depois do anterior.
document.querySelectorAll('.sidebar > *').forEach((item, indice) => item.style.setProperty('--i', indice));

// Os blocos da aba entram um depois do outro ao abrir a aba.
function animarEntradaDaPagina(pageName) {
  if (SEM_ANIMACAO) return;
  const pagina = document.getElementById(`page-${pageName}`);
  if (!pagina) return;
  reiniciarAnimacao(pagina, 'pagina-entrando');
  clearTimeout(pagina.timerEntrada);
  pagina.timerEntrada = setTimeout(() => pagina.classList.remove('pagina-entrando'), 900);
}

// Os numeros dos cards (horas, percentuais) contam ate o valor novo em
// vez de trocar de uma vez. Le e escreve no padrao brasileiro.
const NUMERO_BR = /^(-?\d{1,3}(?:\.\d{3})*(?:,\d+)?|-?\d+(?:,\d+)?)(\s*(?:%|h))?$/;

function lerNumeroBR(texto) {
  const achado = NUMERO_BR.exec((texto || '').trim());
  if (!achado) return null;
  const [, numero, sufixo = ''] = achado;
  const casas = numero.includes(',') ? numero.split(',')[1].length : 0;
  return { valor: Number(numero.replace(/\./g, '').replace(',', '.')), casas, sufixo };
}

// Contagem em andamento de cada card: {escrito} e o ultimo texto que a
// propria contagem escreveu, para separar isso de um valor novo chegando.
const contagens = new WeakMap();

function contarAte(elemento, de, para, final) {
  const contagem = { escrito: null };
  contagens.set(elemento, contagem);
  const inicio = performance.now();
  const duracao = 650;
  const formato = { minimumFractionDigits: para.casas, maximumFractionDigits: para.casas };
  const passo = (agora) => {
    if (contagens.get(elemento) !== contagem) return; // um valor mais novo assumiu
    const t = Math.min(1, (agora - inicio) / duracao);
    const suave = 1 - Math.pow(1 - t, 3);
    const texto = t < 1 ? (de + (para.valor - de) * suave).toLocaleString('pt-BR', formato) + para.sufixo : final;
    contagem.escrito = texto;
    elemento.textContent = texto;
    if (t < 1) requestAnimationFrame(passo);
    else contagens.delete(elemento);
  };
  requestAnimationFrame(passo);
}

function observarNumero(elemento) {
  let anterior = elemento.textContent;
  new MutationObserver(() => {
    const texto = elemento.textContent;
    const emCurso = contagens.get(elemento);
    if (emCurso && texto === emCurso.escrito) return; // e a propria contagem escrevendo
    // De onde a contagem parte: o que estava na tela antes do valor novo.
    const deTexto = emCurso ? emCurso.escrito : anterior;
    anterior = texto;
    if (texto === deTexto) return;
    const novo = lerNumeroBR(texto);
    const velho = lerNumeroBR(deTexto);
    if (SEM_ANIMACAO || !novo || (velho && velho.valor === novo.valor)) {
      contagens.delete(elemento);
      return;
    }
    contarAte(elemento, velho ? velho.valor : 0, novo, texto);
  }).observe(elemento, { childList: true, characterData: true, subtree: true });
}
document.querySelectorAll('.hc-card-valor:not(.texto)').forEach(observarNumero);

// Ondinha no clique dos botoes principais (Entrar, Iniciar extracao,
// Extrair, Aplicar...). Os de apoio (copiar, links, menu) ficam de fora.
document.addEventListener('pointerdown', (evento) => {
  if (SEM_ANIMACAO) return;
  const botao = evento.target.closest('button');
  if (!botao || botao.disabled) return;
  if (botao.matches('.nav-item, .seg-opcao, .link-btn, .copy-btn, .period-option, .hc-ajuda, .hc-icone, .grupo-chip, .resumo-nome button')) return;
  const caixa = botao.getBoundingClientRect();
  const tamanho = Math.max(caixa.width, caixa.height);
  const onda = document.createElement('span');
  onda.className = 'onda';
  onda.style.width = onda.style.height = `${tamanho}px`;
  onda.style.left = `${evento.clientX - caixa.left - tamanho / 2}px`;
  onda.style.top = `${evento.clientY - caixa.top - tamanho / 2}px`;
  // Botao posicionado (absoluto, fixo) nao pode virar "relative": ele
  // mudaria de lugar entre o apertar e o soltar, e o clique se perderia.
  botao.classList.add(getComputedStyle(botao).position === 'static' ? 'com-onda' : 'com-onda-livre');
  botao.appendChild(onda);
  setTimeout(() => onda.remove(), 560);
});

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
  } else if (pageName === 'coverage') {
    await carregarCoverage();
  } else if (pageName === 'indiretas') {
    await carregarIndiretas();
  } else if (pageName === 'gestor') {
    await abaGestor.carregar();
  } else if (pageName === 'turno') {
    await abaTurno.carregar();
  } else if (pageName === 'settings') {
    requestAnimationFrame(() => document.querySelectorAll('.aparencia-opcoes').forEach(moverDestaque));
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
  // A ultima extracao da operacao escolhida no filtro (a de outra
  // operacao nao diz nada sobre estes numeros).
  const operacao = homeOperationSelect.selectedOptions[0]?.text;
  const last = history.find((h) => h.operation === operacao);
  if (!last) {
    homeLastRunEl.textContent = history.length
      ? `Nenhuma extração de ${operacao} ainda`
      : 'Nenhuma extração ainda';
    return;
  }
  const desfecho = desfechoDe(last);
  const quando = new Date(last.timestamp).toLocaleString('pt-BR');
  const sufixo = desfecho.classe === 'success' ? '' : ` (${desfecho.rotulo.toLowerCase()})`;
  homeLastRunEl.textContent = `${last.operation} · ${quando}${sufixo}`;
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
  if (!temDados) {
    document.getElementById('distribuicao-card').hidden = true;
    const nomeDoMes = homeMes.selectedOptions[0]?.text || 'neste mês';
    document.getElementById('indicators-empty-titulo').textContent =
      `Nenhuma extração de ${homeOperationSelect.selectedOptions[0]?.text || 'esta operação'} em ${nomeDoMes} ainda`;
    return;
  }

  desenharDistribuicao(tabela.distribuicao);
  const primeiraVez = !indicatorsBody.querySelector('tr:not(.linha-esqueleto)');
  desenharCabecalho(tabela);
  desenharLinhas(tabela);
  if (primeiraVez) entrarEmSequencia(indicatorsBody);
  // Abre mostrando o fim da tabela: o mes e o pico sao o que se olha
  // primeiro, e numa janela estreita eles ficariam escondidos a direita.
  indicatorsWrap.scrollLeft = indicatorsWrap.scrollWidth;
}

// ---------------------------------------------------------------
// Grafico de distribuicao da dispersao do mes (aba Inicio)
// ---------------------------------------------------------------
// Pessoas por faixa de Var, da extracao Month, com a curva da meta (70%
// na faixa verde, 15% em cada amarela, nenhuma nas vermelhas). As
// contagens e as metas vem prontas do Python; aqui so se desenha.

const SVG_NS = 'http://www.w3.org/2000/svg';
const GRAFICO = { largura: 640, altura: 250, topo: 34, base: 212, lado: 16 };

function elementoSvg(nome, atributos, texto) {
  const el = document.createElementNS(SVG_NS, nome);
  for (const [chave, valor] of Object.entries(atributos)) el.setAttribute(chave, valor);
  if (texto !== undefined) el.textContent = texto;
  return el;
}

// Curva suave pelos pontos (Catmull-Rom em Bezier), como a linha de
// tendencia do Excel.
function caminhoSuave(pontos) {
  let d = `M${pontos[0].x},${pontos[0].y}`;
  for (let i = 0; i < pontos.length - 1; i += 1) {
    const p0 = pontos[i - 1] || pontos[i];
    const p1 = pontos[i];
    const p2 = pontos[i + 1];
    const p3 = pontos[i + 2] || p2;
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 };
    const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 };
    d += ` C${c1.x},${Math.min(c1.y, GRAFICO.base)} ${c2.x},${Math.min(c2.y, GRAFICO.base)} ${p2.x},${p2.y}`;
  }
  return d;
}

function percentualDe(parte, total) {
  return total ? `${(parte / total * 100).toFixed(2).replace('.', ',')}%` : '—';
}

function desenharDistribuicao(dist) {
  const card = document.getElementById('distribuicao-card');
  const aviso = document.getElementById('distribuicao-aviso');
  const corpo = document.getElementById('distribuicao-corpo');
  if (!dist || dist.estado === 'sem_extracao') {
    card.hidden = true;
    return;
  }
  card.hidden = false;
  const nomeDoMes = homeMes.selectedOptions[0]?.text || '';
  document.getElementById('distribuicao-sub').textContent =
    `${nomeDoMes} · pessoas por faixa de Var, da extração Month · meta: 70% na faixa verde`;

  const mensagens = {
    extrair_de_novo: 'Este mês foi extraído antes do gráfico existir. Extraia o mês (Month, com User ID) de novo para montar a distribuição.',
    sem_user_id: 'O mês foi extraído sem User ID no agrupamento: a distribuição conta pessoas e precisa dele.',
  };
  const vazio = dist.estado === 'ok' && !dist.total;
  aviso.hidden = dist.estado === 'ok' && !vazio;
  corpo.hidden = !aviso.hidden;
  if (!aviso.hidden) {
    aviso.textContent = mensagens[dist.estado] || 'Nenhuma pessoa entrou na conta da dispersão neste mês.';
    return;
  }

  const svg = document.getElementById('distribuicao-grafico');
  svg.innerHTML = '';
  const { largura, topo, base, lado } = GRAFICO;
  const maximo = Math.max(1, ...dist.faixas.map((f) => Math.max(f.pessoas, f.meta)));
  const y = (valor) => base - (valor / maximo) * (base - topo);
  const passo = (largura - lado * 2) / dist.faixas.length;
  const larguraBarra = Math.min(64, passo * 0.5);
  const centro = (i) => lado + passo * i + passo / 2;

  svg.appendChild(elementoSvg('line', { x1: lado, x2: largura - lado, y1: base, y2: base, class: 'distribuicao-eixo' }));

  dist.faixas.forEach((faixa, i) => {
    const x = centro(i) - larguraBarra / 2;
    const altura = Math.max(0, base - y(faixa.pessoas));
    const raio = Math.min(4, altura);
    const grupo = elementoSvg('g', { class: 'distribuicao-faixa' });
    grupo.appendChild(elementoSvg('title', {},
      `${faixa.rotulo}: ${plural(faixa.pessoas, 'pessoa', 'pessoas')} `
      + `(${percentualDe(faixa.pessoas, dist.total)}) · meta ${num(faixa.meta)}`));
    // Area de toque maior que a barra, para a dica aparecer facil.
    grupo.appendChild(elementoSvg('rect', { x: centro(i) - passo / 2, y: topo - 20, width: passo, height: base - topo + 20, fill: 'transparent' }));
    if (altura > 0) {
      grupo.appendChild(elementoSvg('path', {
        class: `distribuicao-barra ${faixa.cor}`,
        d: `M${x},${base} V${base - altura + raio} Q${x},${base - altura} ${x + raio},${base - altura} `
          + `H${x + larguraBarra - raio} Q${x + larguraBarra},${base - altura} ${x + larguraBarra},${base - altura + raio} V${base} Z`,
      }));
    }
    grupo.appendChild(elementoSvg('text', { x: centro(i), y: base + 22, class: 'distribuicao-rotulo' }, faixa.rotulo));
    svg.appendChild(grupo);
  });

  // Curva da meta, com o numero da faixa verde no pico.
  const pontos = dist.faixas.map((faixa, i) => ({ x: centro(i), y: y(faixa.meta) }));
  svg.appendChild(elementoSvg('path', { d: caminhoSuave(pontos), class: 'distribuicao-meta' }));
  const verde = dist.faixas.find((f) => f.chave === 'dentro');
  const pico = pontos[dist.faixas.indexOf(verde)];
  svg.appendChild(elementoSvg('circle', { cx: pico.x, cy: pico.y, r: 4, class: 'distribuicao-meta-ponto' }));
  // O numero da meta vai a direita da barra verde, e nao no meio dela:
  // com barra e meta iguais (1 e 1), os dois numeros ficavam encavalados.
  svg.appendChild(elementoSvg('text', {
    x: pico.x + larguraBarra / 2 + 8, y: pico.y + 5, class: 'distribuicao-meta-valor',
  }, `meta ${num(verde.meta)}`));

  // Os numeros das barras por ultimo, por cima da curva, com um contorno
  // da cor do fundo: onde a curva passa perto, o numero continua legivel.
  dist.faixas.forEach((faixa, i) => {
    svg.appendChild(elementoSvg('text', { x: centro(i), y: y(faixa.pessoas) - 8, class: 'distribuicao-valor' },
      num(faixa.pessoas)));
  });

  // A mesma informacao em tabela, como na planilha: pessoas e meta.
  const tabela = document.getElementById('distribuicao-tabela');
  const cabecalho = dist.faixas.map((f) => `<th>${f.rotulo}</th>`).join('');
  const pessoas = dist.faixas.map((f) => `<td>${num(f.pessoas)}</td>`).join('');
  const metas = dist.faixas.map((f) => `<td>${num(f.meta)}</td>`).join('');
  tabela.innerHTML = `<thead><tr><th></th>${cabecalho}<th>Total</th></tr></thead>`
    + `<tbody><tr><th>Pessoas</th>${pessoas}<td>${num(dist.total)}</td></tr>`
    // Total da meta em branco, como na planilha: as metas arredondadas
    // nao somam o total de pessoas (6 + 1 + 1 = 8 de 9).
    + `<tr class="meta"><th>Meta</th>${metas}<td></td></tr></tbody>`;
}

function desenharCabecalho(tabela) {
  desenharCabecalhoEm(indicatorsHead, indicatorsBody, tabela.colunas, 'Operação', tabela.operacao);
}

// O cabecalho de uma tabela de indicadores (Inicio, Resultado Gestor e
// Resultado Turno): o canto com de quem e a tabela, e uma coluna por
// semana ou mes, cada uma com o seu botao Copiar.
function desenharCabecalhoEm(linhaDoCabecalho, corpo, colunas, rotuloDoCanto, nomeDoCanto, notaDoCanto) {
  linhaDoCabecalho.innerHTML = '';

  // O canto leva o nome da operacao: num print levado pra reuniao o
  // filtro costuma ficar fora do recorte, e a tabela precisa dizer de
  // quem ela e.
  const canto = document.createElement('th');
  canto.scope = 'col';
  canto.className = 'indicator-corner';
  const rotulo = document.createElement('div');
  rotulo.className = 'corner-label';
  rotulo.textContent = rotuloDoCanto;
  const nome = document.createElement('div');
  nome.className = 'corner-operation';
  nome.textContent = nomeDoCanto;
  canto.appendChild(rotulo);
  canto.appendChild(nome);
  if (notaDoCanto) {
    const nota = document.createElement('div');
    nota.className = 'corner-nota' + (notaDoCanto.classe ? ` ${notaDoCanto.classe}` : '');
    nota.textContent = notaDoCanto.texto;
    if (notaDoCanto.dica) nota.title = notaDoCanto.dica;
    canto.appendChild(nota);
  }
  linhaDoCabecalho.appendChild(canto);

  colunas.forEach((coluna, indice) => {
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

    th.appendChild(botaoCopiar(indice, coluna.titulo, corpo));
    linhaDoCabecalho.appendChild(th);
  });
}

function classeDaColuna(coluna) {
  if (coluna.periodo === 'month') return ' month-col';
  if (coluna.periodo === 'peak') return ' peak-col';
  return '';
}

function desenharLinhas(tabela) {
  desenharLinhasEm(indicatorsBody, tabela.linhas, tabela.colunas);
}

function desenharLinhasEm(corpo, linhas, colunas) {
  corpo.innerHTML = '';
  for (const linha of linhas) {
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
      const coluna = colunas[indice];
      td.className = 'indicator-cell' + classeDaColuna(coluna);
      if (celula.nao_se_aplica) {
        // Indicador que nao existe nesta coluna (coverage no pico): nem
        // traco, que quer dizer "ainda sem numero".
        td.classList.add('nao-se-aplica');
        // No turno (presenteismo e cubo) a copia guarda a posicao vazia,
        // para o valor de baixo nao subir de linha.
        if (celula.copia_vazia) td.dataset.copiaVazia = '1';
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

    corpo.appendChild(tr);
  }
}

function botaoCopiar(indice, titulo, corpo = indicatorsBody) {
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'copy-btn';
  btn.setAttribute('aria-label', `Copiar os números de ${titulo}`);
  btn.textContent = 'Copiar';
  btn.addEventListener('click', () => copiarColuna(indice, btn, corpo, titulo));
  return btn;
}

// Os valores da coluna, na ordem dos indicadores. Indicador sem numero
// vira posicao vazia, pra nenhum valor subir de lugar. Indicador que
// nao existe na coluna (coverage no pico) fica de fora: o pico copia
// cinco valores, do cubo a dispersao. No turno, presenteismo e cubo nao
// se aplicam mas guardam a posicao (data-copia-vazia).
function valoresDaColuna(indice, corpo = indicatorsBody) {
  return Array.from(corpo.querySelectorAll('tr'))
    .map((tr) => tr.querySelectorAll('td')[indice])
    .filter((celula) => !(celula && celula.classList.contains('nao-se-aplica') && !celula.dataset.copiaVazia))
    .map((celula) => {
      if (!celula) return '';
      const valor = celula.querySelector('.indicator-value');
      return valor ? valor.textContent : '';
    });
}

function textoDaColuna(indice, corpo = indicatorsBody) {
  return valoresDaColuna(indice, corpo).join('\n');
}

// A mesma coluna como tabela de uma coluna por seis linhas. E isso que
// faz cada valor cair numa celula do PowerPoint: texto com quebras de
// linha ele cola inteiro dentro de UMA celula, porque a quebra vira
// linha dentro do paragrafo, nao mudanca de celula.
//
// A celula vai formatada: sem estilo, o PowerPoint aplica a fonte e as
// margens padrao dele, maiores que as da tabela da apresentacao, e com
// duas casas decimais o "%" descia para uma segunda linha ("78,48" / "%").
// Centralizada, sem margem, sem quebra e com fonte compacta, fica numa
// linha so, igual ao numero digitado na propria tabela.
//
// O tamanho tem que ir no proprio texto (span e font), do jeito que o
// Word e o Excel copiam: o PowerPoint ignora o font-size da celula <td>
// e aplica o padrao de tabela dele, 18 pt.
const TAMANHO_DA_FONTE_COPIADA = '10.0pt';

function celulaParaColar(valor, alinhamento = 'center', negrito = false) {
  const estilo = `text-align:${alinhamento};white-space:nowrap;padding:0;margin:0;font-size:${TAMANHO_DA_FONTE_COPIADA}`;
  const texto = negrito ? `<b>${valor}</b>` : valor;
  return `<td nowrap style="${estilo}">`
    + `<p class="MsoNormal" align="${alinhamento}" style="margin:0;text-align:${alinhamento};font-size:${TAMANHO_DA_FONTE_COPIADA}">`
    + `<span style="font-size:${TAMANHO_DA_FONTE_COPIADA};mso-bidi-font-size:${TAMANHO_DA_FONTE_COPIADA}">`
    + `<font size="2">${texto}</font></span></p></td>`;
}

// Uma tabela qualquer para colar: linhas de celulas, cada celula um
// texto ou {texto, alinhamento, negrito}. Os textos vem da propria tela
// (numeros, nomes de atividade) e sao escapados.
function tabelaParaColar(linhas) {
  const corpo = linhas.map((linha) => '<tr>' + linha.map((celula) => {
    const c = typeof celula === 'object' && celula !== null ? celula : { texto: celula };
    return celulaParaColar(escaparHtml(c.texto ?? ''), c.alinhamento || 'center', c.negrito);
  }).join('') + '</tr>').join('');
  return `<table style="border-collapse:collapse">${corpo}</table>`;
}

function textoParaColar(linhas) {
  return linhas.map((linha) => linha.map((celula) =>
    (typeof celula === 'object' && celula !== null ? celula.texto : celula) ?? '').join('\t')).join('\n');
}

function escaparHtml(texto) {
  return String(texto).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function tabelaDaColuna(indice, corpo = indicatorsBody) {
  return tabelaParaColar(valoresDaColuna(indice, corpo).map((valor) => [valor]));
}

async function copiarColuna(indice, btn, corpo = indicatorsBody, titulo = '') {
  const quantos = valoresDaColuna(indice, corpo).length;
  await copiarComAviso(btn, textoDaColuna(indice, corpo), tabelaDaColuna(indice, corpo),
    `${plural(quantos, 'valor', 'valores')}${titulo ? ` de ${titulo}` : ''}`);
}

// Copia, mostra no proprio botao se deu certo e avisa no canto o que foi.
async function copiarComAviso(btn, texto, html, descricao) {
  const copiado = await copiarTexto(texto, html);
  if (copiado) avisar(`Copiado: ${descricao || 'tabela'}`, 'ok', 'Cole no PowerPoint ou no Excel com Ctrl+V.');
  else avisar('Não deu para copiar', 'erro', 'Tente de novo; se continuar, gere o diagnóstico em Configurações.');
  const original = btn.dataset.rotulo || btn.textContent;
  btn.dataset.rotulo = original;
  btn.textContent = copiado ? 'Copiado' : 'Não deu';
  btn.classList.toggle('copiado', copiado);
  clearTimeout(btn.timerCopia);
  btn.timerCopia = setTimeout(() => {
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

homeOperationSelect.addEventListener('change', () => { loadLastRun(); loadIndicators(); });
homeMes.addEventListener('change', loadIndicators);

// Atalho das telas vazias: abre Extrair Dados com a operacao e o tipo de
// extracao ja escolhidos. So preenche a tela; quem extrai e o botao de la.
function irParaExtracao(operacao, periodo, groupBy) {
  if (operacao && [...operationSelect.options].some((o) => o.value === operacao)) {
    operationSelect.value = operacao;
  }
  if (periodo) escolherPeriodo(periodOptionEls, groupBySelect, periodo);
  if (groupBy && !groupBySelect.disabled
      && [...groupBySelect.options].some((o) => o.value === groupBy)) {
    groupBySelect.value = groupBy;
  }
  showPage('extract');
}

document.getElementById('indicators-extrair').addEventListener('click', () => {
  irParaExtracao(homeOperationSelect.value, 'week');
});

// ---------------------------------------------------------------
// Modo apresentacao (aba Inicio)
// ---------------------------------------------------------------
// Tela cheia, sem o menu e sem os botoes de apoio, com a tabela maior
// para projetar. As setas trocam a operacao; Esc sai. So muda a
// apresentacao: os numeros sao os mesmos da tela normal.

const apresentacaoBarra = document.getElementById('apresentacao-barra');
let emApresentacao = false;

async function modoApresentacao(ligar) {
  if (ligar === emApresentacao) return;
  emApresentacao = ligar;
  document.body.classList.toggle('apresentacao', ligar);
  apresentacaoBarra.hidden = !ligar;
  try {
    await pywebview.api.tela_cheia(ligar);
  } catch (erro) {
    registrarErro('tela cheia', erro);
  }
  indicatorsWrap.scrollLeft = indicatorsWrap.scrollWidth;
  if (!ligar) document.getElementById('home-apresentar').focus();
}

function trocarOperacaoNaApresentacao(passo) {
  const total = homeOperationSelect.options.length;
  if (!total) return;
  homeOperationSelect.selectedIndex = (homeOperationSelect.selectedIndex + passo + total) % total;
  homeOperationSelect.dispatchEvent(new Event('change'));
}

document.getElementById('home-apresentar').addEventListener('click', () => modoApresentacao(true));
document.getElementById('apresentacao-sair').addEventListener('click', () => modoApresentacao(false));
document.addEventListener('keydown', (evento) => {
  if (!emApresentacao) return;
  if (evento.key === 'Escape') {
    evento.preventDefault();
    modoApresentacao(false);
    return;
  }
  // Num select aberto as setas ja trocam a opcao sozinhas.
  if (evento.target.closest('select, input, textarea')) return;
  if (evento.key === 'ArrowRight' || evento.key === 'ArrowLeft') {
    evento.preventDefault();
    trocarOperacaoNaApresentacao(evento.key === 'ArrowRight' ? 1 : -1);
  }
});

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});

// As duas abas de extracao mostram o mesmo historico, cada uma com o
// seu <tbody>.
// O historico vem uma vez do Python e os filtros (operacao, tipo e
// resultado) so escolhem o que aparece.
let historicoCompleto = [];

async function loadHistoryTable(tbody = historyTableBody) {
  historicoCompleto = await comEsqueleto(tbody, 7, () => pywebview.api.get_report_history());
  desenharHistorico(tbody);
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

  alert(
    'Antes de comecar, selecione a pasta do SharePoint/OneDrive onde os ' +
    'relatórios extraídos serão salvos.'
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
    showStatus(loginStatus, 'Preencha usuário e senha.', 'error');
    tremerLogin();
    return;
  }

  loginBtn.disabled = true;
  loginBtn.textContent = 'Entrando...';
  try {
    const result = await pywebview.api.login(username, password);
    if (!result.success) {
      showStatus(loginStatus, result.message || 'Falha no login.', 'error');
      tremerLogin();
      return;
    }
    loginPassword.value = '';
    await entrarNoApp(showApp);
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
  // Extracao disparada da aba Horas Indiretas: o andamento aparece la.
  if (indExtraindo) progressoIndiretas(text);
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
    showStatus(runStatus, 'A "Data inicial" não pode ser depois da "Data final".', 'error');
    return;
  }
  // yyyy-mm-dd (formato nativo do <input type="date">) - a conversao
  // pro formato que o Summary espera (dd/mm/yyyy) acontece no Python,
  // perto de onde o campo de verdade e preenchido.
  const dateRange = { from_date: fromDateInput.value, to_date: toDateInput.value };

  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(runStatus, 'É necessário selecionar a pasta do SharePoint antes de executar.', 'error');
    return;
  }

  runBtn.disabled = true;
  runBtn.querySelector('.btn-texto').textContent = 'Executando...';
  resetSteps();
  setBadge('running', 'Em andamento');
  progressDetailEl.textContent = 'Iniciando a extração...';
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

  const folderOk = await ensureFolderConfigured();
  if (!folderOk) {
    showStatus(multiRunStatus, 'É necessário selecionar a pasta do SharePoint antes de executar.', 'error');
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
    const result = filtros
      ? await pywebview.api.run_multi_filters(selected[0].key, tiposEscolhidosNoMulti(), dateRange, multiGroupBySelect.value)
      : await pywebview.api.run_multi_extraction(
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

window.addEventListener('pywebviewready', async () => {
  carregarVersao();
  await carregarPreferencias();
  showLogin();
  encerrarAbertura();
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

// Numero no padrao brasileiro: 8,75 e 1.234 (no lugar de 8.75 e 1234).
function num(valor) {
  if (typeof valor !== 'number') return valor;
  if (valor === 0) valor = 0; // -0 vira 0 (senao a tela mostra "-0")
  return valor.toLocaleString('pt-BR', { maximumFractionDigits: 2 });
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
  hcMesLabel.textContent = noMes ? 'Período da Folha Ponto' : 'Mês vigente';
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
    preencherSelect(hcPeriodo, [{ id: '', rotulo: 'Não se aplica ao ciclo da folha' }], '');
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
  document.getElementById('hc-card-hc').textContent = num(c.hc_total);
  document.getElementById('hc-card-faltas').textContent = c.faltas;
  document.getElementById('hc-card-horas').textContent = `${num(c.horas_perdidas)} h perdidas`;
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
  calendario: () => 'Dias úteis do calendário desta semana. Digite para ajustar (feriado, por exemplo).',
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
  if (campo === 'faltas') {
    input.classList.add('hc-faltas-input');
    // O vermelho so aparece quando ha falta; zero fica neutro.
    input.classList.toggle('tem-falta', Number(linha.faltas) > 0);
  }

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
      ? 'Valor apagado: volta a valer o herdado. A aba Início já reflete a mudança.'
      : 'Salvo só para este período. A aba Início já reflete a mudança.';
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
    hcStatus.textContent = 'Quadro atualizado. A aba Início já reflete a mudança.';
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
    sugerirNomesDoSummary(linha.operacao_key);
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
      : `${nome} atualizado. As faltas da planilha já são ligadas pelo nome novo.`;
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
  hcStatus.textContent = `${nome} excluído. A aba Início já reflete a mudança.`;
}

function desenharTabelaHc(tela) {
  hcTabelaTitulo.textContent = tela.visualizacao === 'mes'
    ? 'Resultado do mês por gestor · folha ponto'
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
    // O nome bate com um supervisor do Summary? So assim o presenteismo
    // dele aparece no Resultado Gestor.
    if (linha.summary) {
      const selo = document.createElement('span');
      selo.className = `hc-summary ${linha.summary}`;
      selo.textContent = linha.summary === 'ligado' ? '✓ no Summary' : 'sem par no Summary';
      selo.title = linha.summary === 'ligado'
        ? 'O nome é igual ao de um supervisor do Summary: o presenteísmo vai para o Resultado Gestor.'
        : 'Nenhum supervisor do Summary desta operação tem este nome. Edite o nome para ficar igual ao da planilha.';
      nomes.appendChild(selo);
    }
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
    // A semana (ou o ciclo) ja esta no filtro e no cartao de periodo;
    // repetir em cada linha so ocupava espaco.
    if (!tela.faltas_manuais) tdOperacao.appendChild(per);
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
    selo.title = 'Veio da planilha de faltas, não é digitado';
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
    num(t.hc), num(unicoOuVaria('dias_uteis')), num(unicoOuVaria('horas_dia')), num(t.faltas),
  ];
  celulas.forEach((texto, indice) => {
    const td = document.createElement('td');
    if (indice >= 2) td.className = 'num';
    td.textContent = texto;
    if (texto === 'varia') {
      td.classList.add('hc-varia');
      td.title = 'Os gestores têm números diferentes nesta semana (escala ou valor digitado).';
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
  document.getElementById('hc-mem-disponiveis').textContent = `${num(m.horas_disponiveis)} h`;
  document.getElementById('hc-mem-perdidas').textContent = `${num(m.horas_perdidas)} h`;
  document.getElementById('hc-mem-efetivas').textContent = `${num(m.horas_efetivas)} h`;
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
      'presenteísmo aparece como 100%.</p>';
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
    `<span class="hc-contador-item"><strong>${r.consideradas}</strong>faltas válidas</span>` +
    `<span class="hc-contador-item"><strong>${r.gestores}</strong>gestores</span>` +
    `<span class="hc-contador-item"><strong>${r.dias}</strong>dias faltados</span>` +
    '</div>');

  // O que foi descartado e tao importante quanto o que entrou: um
  // filtro derrubando o arquivo inteiro precisa aparecer.
  const descartes = [];
  if (r.motivo) descartes.push(`${r.motivo} por motivo (ferias)`);
  if (r.contrato) descartes.push(`${r.contrato} por contrato (temporario)`);
  if (r.funcao) descartes.push(`${r.funcao} por função fora do quadro`);
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
    `Faltas importadas de ${arquivo.nome} · ${r.linhas} linhas · última leitura ${quando}`;
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
  const itens = [{ key: '', label: 'Escolha a operação' }, ...operacoes];
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
  if (qual === 'gestor') sugerirNomesDoSummary(hcNovoGestorOp.value);
}

// O nome do gestor precisa ser igual ao do Summary para o presenteismo
// chegar ao Resultado Gestor: o campo sugere os supervisores que ja
// vieram nas extracoes da operacao (Gestor · Week, Week).
async function sugerirNomesDoSummary(operacao) {
  const lista = document.getElementById('hc-nomes-summary');
  const nota = document.getElementById('hc-nomes-nota');
  lista.innerHTML = '';
  if (!operacao) {
    nota.textContent = 'Escolha a operação para ver os nomes que vieram do Summary.';
    return;
  }
  let nomes = [];
  try {
    nomes = await pywebview.api.get_nomes_do_summary(operacao);
  } catch (erro) {
    registrarErro('nomes do Summary', erro);
  }
  for (const nome of nomes) {
    const opcao = document.createElement('option');
    opcao.value = nome;
    lista.appendChild(opcao);
  }
  nota.textContent = nomes.length
    ? `${plural(nomes.length, 'nome', 'nomes')} do Summary para escolher: use o nome igual ao da planilha para o presenteísmo ir para o Resultado Gestor.`
    : 'Ainda sem extração com o Supervisor desta operação: digite o nome igual ao do Summary (ex.: SOBRENOME,NOME).';
}

document.getElementById('hc-add-gestor').addEventListener('click', () => abrirFaixa('gestor'));
document.getElementById('hc-novo-gestor-op').addEventListener('change', (evento) => sugerirNomesDoSummary(evento.target.value));
document.getElementById('hc-editar-op').addEventListener('change', (evento) => sugerirNomesDoSummary(evento.target.value));
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
      ? 'Escolha a operação do gestor antes de adicionar.'
      : 'Escolha a operação da função antes de adicionar.';
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
    ? `${valor} cadastrado em ${nomeOperacao}. Preencha o HC: as faltas já vêm da planilha carregada.`
    : `${valor} passa a contar como falta em ${nomeOperacao}, já nesta planilha e na aba Início.`;
}

for (const [botao, campo, qual] of [
  ['hc-confirmar-gestor', 'hc-novo-gestor', 'gestor'],
  ['hc-confirmar-funcao', 'hc-nova-funcao', 'funcao'],
]) {
  document.getElementById(botao).addEventListener('click', async () => {
    const valor = document.getElementById(campo).value.trim();
    if (!valor) {
      hcStatus.textContent = qual === 'gestor' ? 'Informe o nome do gestor.' : 'Informe o nome da função.';
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
  hcStatus.textContent = 'Faltas removidas. Sem planilha, o presenteísmo volta a 100%.';
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
    'As faltas vêm da planilha de ausências: uma linha por dia de falta, com ' +
    'GESTOR_NAME, NOME, FUNCAO, MOTIVO, CONTRACT e ABS_DATE. Ferias, temporarios ' +
    'e funções fora do quadro não entram.';
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
    `${arquivo.name} lido. O presenteísmo de cada semana e de cada ciclo já está na aba Início.`;
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


// ---------------------------------------------------------------
// Aba Coverage
// ---------------------------------------------------------------
// Uma linha por usuario, com as horas que vieram do Summary (Horas LMS
// e diretas sem meta) e o que se digita aqui: dias, horas, sinergia
// cedida e recebida. O Python calcula; aqui so se desenha.

const cvOperacao = document.getElementById('cv-operacao');
const cvMes = document.getElementById('cv-mes');
const cvPeriodo = document.getElementById('cv-periodo');
const cvVisualizacao = document.getElementById('cv-visualizacao');
const cvCorpo = document.getElementById('cv-corpo');
const cvTotal = document.getElementById('cv-total');
const cvStatus = document.getElementById('cv-status');
const cvVazio = document.getElementById('cv-vazio');
const cvGestor = document.getElementById('cv-gestor');

let cvEstado = { operacao: 'todas', visualizacao: 'semanal', mes: null, periodo_id: null, gestor: '' };
let cvTela = null;

function pct(valor) {
  if (valor === null || valor === undefined) return '—';
  return `${(valor * 100).toFixed(2).replace('.', ',')}%`;
}

async function carregarCoverage() {
  cvTela = await comEsqueleto(cvCorpo, 11, () => pywebview.api.get_coverage(
    cvEstado.operacao, cvEstado.visualizacao, cvEstado.mes, cvEstado.periodo_id, cvEstado.gestor || null));
  cvEstado.mes = cvTela.mes;
  cvEstado.periodo_id = cvTela.periodo_id;
  cvEstado.gestor = cvTela.gestor || '';
  desenharFiltrosCv(cvTela);
  desenharCardsCv(cvTela);
  desenharTabelaCv(cvTela);
  ajustarAlturaCv();
}

// A lista de usuarios ganha a altura que sobra na janela, e rola sozinha
// quando nao cabe: o resto da tela fica parado. Com poucos usuarios a
// tabela fica do tamanho dela, sem barra.
const cvWrap = document.getElementById('cv-tabela-wrap');
const ESPACO_ABAIXO_DA_LISTA = 104; // formula, linha de status e fim do cartao
// Cabecalho, TOTAL e umas quatro linhas de usuario. Numa tela baixa
// (notebook com zoom de 150%) a lista ficava com linha e meia: abaixo
// disso, quem rola e a pagina.
const ALTURA_MINIMA_DA_LISTA = 320;

function ajustarAlturaCv() {
  if (!cvWrap || cvWrap.hidden || !cvWrap.offsetParent) return;
  const topoNaArea = cvWrap.getBoundingClientRect().top
    - contentArea.getBoundingClientRect().top + contentArea.scrollTop;
  const disponivel = contentArea.clientHeight - topoNaArea - ESPACO_ABAIXO_DA_LISTA;
  cvWrap.style.maxHeight = `${Math.max(ALTURA_MINIMA_DA_LISTA, disponivel)}px`;
  // Se ainda sobrou rolagem na pagina (margens, linha de status que
  // quebrou), a lista encolhe esse tanto: quem rola e so ela.
  const sobra = contentArea.scrollHeight - contentArea.clientHeight;
  if (sobra > 0 && cvWrap.scrollHeight > cvWrap.clientHeight) {
    cvWrap.style.maxHeight = `${Math.max(ALTURA_MINIMA_DA_LISTA, cvWrap.clientHeight - sobra)}px`;
  }
  cvWrap.classList.toggle('com-rolagem', cvWrap.scrollHeight > cvWrap.clientHeight);
}
window.addEventListener('resize', ajustarAlturaCv);

function desenharFiltrosCv(tela) {
  preencherSelect(cvOperacao, tela.operacoes, tela.operacao, 'key', 'label');
  preencherSelect(cvMes, tela.meses, tela.mes);
  const noMes = tela.visualizacao === 'mes';
  if (noMes) {
    preencherSelect(cvPeriodo, [{ id: '', rotulo: 'Não se aplica ao resultado do mês' }], '');
  } else if (!tela.periodos.length) {
    preencherSelect(cvPeriodo, [{ id: '', rotulo: 'Nenhuma semana extraída neste mês' }], '');
  } else {
    preencherSelect(cvPeriodo, tela.periodos, tela.periodo_id);
  }
  cvPeriodo.disabled = noMes || !tela.periodos.length;
  // Gestor: o de cada usuario vem do Supervisor da extracao Week.
  preencherSelect(cvGestor, tela.gestores, tela.gestor || '');
  cvGestor.disabled = tela.gestores.length <= 1;
  cvGestor.title = tela.gestores.length <= 1
    ? 'Sem gestor nesta extração: extraia a Week de novo (agora ela vem com o Supervisor).' : '';
  for (const botao of cvVisualizacao.querySelectorAll('.seg-opcao')) {
    botao.classList.toggle('active', botao.dataset.visualizacao === tela.visualizacao);
  }
  moverDestaque(cvVisualizacao);
}

function desenharCardsCv(tela) {
  const c = tela.cards;
  document.getElementById('cv-card-operacao').textContent = c.operacao;
  document.getElementById('cv-card-operacao-nota').textContent = c.operacao_nota || '';
  document.getElementById('cv-card-periodo').textContent = c.periodo;
  document.getElementById('cv-card-periodo-nota').textContent = c.periodo_nota;
  document.getElementById('cv-card-lms').textContent = `${num(c.lms)} h`;
  document.getElementById('cv-card-usuarios').textContent = plural(tela.total.usuarios, 'usuário', 'usuários');
  document.getElementById('cv-card-metrics').textContent = `${num(c.metrics)} h`;
  document.getElementById('cv-card-coverage').textContent = pct(c.coverage);
}

function campoCoverage(linha, campo, passo) {
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = passo;
  input.value = linha[campo];
  input.dataset.usuario = linha.usuario;
  input.dataset.operacao = linha.operacao_key;
  input.dataset.campo = campo;
  const origem = { dias: linha.dias_origem, horas: linha.horas_origem }[campo];
  if (origem && origem !== 'digitado') {
    input.classList.add('valor-herdado');
    input.title = campo === 'dias'
      ? 'Dias úteis do período. Digite para ajustar só este usuário.'
      : `Padrão de ${num(cvTela.horas_padrao)} h por dia. Digite para ajustar só este usuário.`;
  }
  if (campo === 'dias') {
    input.addEventListener('keydown', (evento) => {
      if (['-', '+', 'e', 'E', ',', '.'].includes(evento.key)) evento.preventDefault();
    });
  }
  input.addEventListener('change', async () => {
    const resposta = await pywebview.api.set_coverage(
      linha.operacao_key, linha.chave_periodo, linha.usuario, campo, input.value);
    if (!resposta.success) {
      cvStatus.textContent = resposta.message;
      input.value = linha[campo];
      return;
    }
    await redesenharCoverageMantendoFoco();
    cvStatus.textContent = 'Salvo. A linha COVERAGE da aba Início já reflete a mudança.';
  });
  return input;
}

async function redesenharCoverageMantendoFoco() {
  const foco = document.activeElement;
  const destino = foco && foco.dataset && foco.dataset.usuario
    ? { usuario: foco.dataset.usuario, operacao: foco.dataset.operacao, campo: foco.dataset.campo } : null;
  await carregarCoverage();
  if (destino) {
    // Linhas de usuario e a linha TOTAL (sinergia da operacao).
    const alvo = Array.from(document.querySelectorAll('#cv-tabela-wrap input')).find((i) =>
      i.dataset.usuario === destino.usuario && i.dataset.operacao === destino.operacao
      && i.dataset.campo === destino.campo);
    if (alvo) { alvo.focus(); alvo.select(); }
  }
}

function celulaCv(conteudo, classe) {
  const td = document.createElement('td');
  if (classe) td.className = classe;
  if (conteudo instanceof Node) td.appendChild(conteudo); else td.textContent = conteudo;
  return td;
}

// Sinergia da operacao, na linha TOTAL: a visibilidade e da operacao
// (horas cedidas a outra ou recebidas dela), nao de cada pessoa.
function campoSinergiaOperacao(t, campo) {
  const caixa = document.createElement('div');
  caixa.className = 'cv-sinergia-total';
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = '0.25';
  input.value = t[`${campo}_operacao`];
  input.dataset.usuario = '__total__';
  input.dataset.operacao = cvEstado.operacao;
  input.dataset.campo = campo;
  if (!t.sinergia_editavel) {
    input.disabled = true;
    input.value = t[campo];
    input.title = cvTela.gestor
      ? 'A sinergia é da operação inteira: com um gestor no filtro ela não entra no total.'
      : 'A sinergia é de uma operação: escolha uma operação para lançar.';
  } else {
    input.title = `Sinergia ${campo} da operação nesta semana (horas).`;
    input.addEventListener('change', async () => {
      const resposta = await pywebview.api.set_coverage_sinergia(
        cvEstado.operacao, t.chave_periodo, campo, input.value);
      if (!resposta.success) {
        cvStatus.textContent = resposta.message;
        input.value = t[`${campo}_operacao`];
        return;
      }
      await redesenharCoverageMantendoFoco();
      cvStatus.textContent = 'Sinergia da operação salva. O coverage total e a aba Início já refletem.';
    });
  }
  caixa.appendChild(input);
  const porUsuario = t[`${campo}_usuarios`];
  if (porUsuario) {
    const nota = document.createElement('span');
    nota.className = 'cv-sinergia-nota';
    nota.textContent = `+ ${num(porUsuario)} h dos usuários`;
    caixa.appendChild(nota);
  }
  return caixa;
}

function seloCoverage(valor, cor) {
  const selo = document.createElement('span');
  selo.className = `cv-coverage ${cor || 'sem-numero'}`;
  selo.textContent = pct(valor);
  return selo;
}

function desenharTabelaCv(tela) {
  document.getElementById('cv-titulo').textContent = tela.visualizacao === 'mes'
    ? 'Coverage do mês por usuário' : 'Coverage da semana por usuário';
  document.getElementById('cv-contador').textContent = plural(tela.linhas.length, 'usuário', 'usuários');
  const vazio = !tela.linhas.length;
  cvVazio.hidden = !vazio;
  document.getElementById('cv-tabela-wrap').hidden = vazio;
  document.getElementById('cv-todos').hidden = vazio;
  if (vazio) {
    const noMes = tela.visualizacao === 'mes';
    document.getElementById('cv-vazio-titulo').textContent =
      `Nenhuma extração ${noMes ? 'Month' : 'Week'} de ${tela.cards.operacao} em ${cvMes.selectedOptions[0]?.text || 'neste mês'} ainda`;
    document.getElementById('cv-vazio-texto').textContent = noMes
      ? 'Extraia o mês (Month) para ver o coverage de cada usuário.'
      : 'Extraia a semana (Week) para ver o coverage de cada usuário e de cada gestor.';
  }

  cvCorpo.innerHTML = '';
  for (const linha of tela.linhas) {
    const tr = document.createElement('tr');
    if (linha.cor === 'vermelho') tr.classList.add('abaixo');
    const usuario = document.createElement('strong');
    usuario.className = 'cv-usuario';
    usuario.textContent = linha.usuario;
    tr.appendChild(celulaCv(usuario));
    tr.appendChild(celulaCv(linha.operacao));
    tr.appendChild(celulaCv(linha.gestor_rotulo, 'cv-gestor-celula'));
    tr.appendChild(celulaCv(num(linha.lms), 'num'));
    tr.appendChild(celulaCv(num(linha.diretas_sem_meta), 'num'));
    tr.appendChild(celulaCv(campoCoverage(linha, 'dias', '1'), 'num'));
    tr.appendChild(celulaCv(campoCoverage(linha, 'horas', '0.25'), 'num'));
    tr.appendChild(celulaCv(num(linha.metrics), 'num cv-metrics'));
    tr.appendChild(celulaCv(campoCoverage(linha, 'cedida', '0.25'), 'num'));
    tr.appendChild(celulaCv(campoCoverage(linha, 'recebida', '0.25'), 'num'));
    tr.appendChild(celulaCv(seloCoverage(linha.coverage, linha.cor), 'num'));
    cvCorpo.appendChild(tr);
  }

  cvTotal.innerHTML = '';
  if (vazio) return;
  const t = tela.total;
  const tr = document.createElement('tr');
  [
    ['TOTAL', ''], [plural(t.usuarios, 'usuário', 'usuários'), ''], [cvTela.gestor_rotulo || '', 'cv-gestor-celula'],
    [num(t.lms), 'num'], [num(t.diretas_sem_meta), 'num'], ['', 'num'], ['', 'num'],
    [num(t.metrics), 'num'],
  ].forEach(([texto, classe]) => tr.appendChild(celulaCv(texto, classe)));
  for (const campo of ['cedida', 'recebida']) {
    tr.appendChild(celulaCv(campoSinergiaOperacao(t, campo), 'num'));
  }
  const tdTotal = celulaCv(seloCoverage(t.coverage, t.cor), 'num');
  tdTotal.firstChild.classList.add('cv-coverage-total');
  tr.appendChild(tdTotal);
  cvTotal.appendChild(tr);
}

cvOperacao.addEventListener('change', async () => {
  cvEstado.operacao = cvOperacao.value;
  cvEstado.periodo_id = null;
  cvEstado.gestor = '';
  await carregarCoverage();
});
cvGestor.addEventListener('change', async () => {
  cvEstado.gestor = cvGestor.value;
  await carregarCoverage();
});
cvMes.addEventListener('change', async () => {
  cvEstado.mes = cvMes.value;
  cvEstado.periodo_id = null;
  await carregarCoverage();
});
cvPeriodo.addEventListener('change', async () => {
  cvEstado.periodo_id = cvPeriodo.value;
  await carregarCoverage();
});
document.getElementById('cv-extrair').addEventListener('click', () => {
  irParaExtracao(cvEstado.operacao === 'todas' ? null : cvEstado.operacao,
    cvEstado.visualizacao === 'mes' ? 'month' : 'week', 'User ID');
});

cvVisualizacao.addEventListener('click', async (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (!botao) return;
  cvVisualizacao.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b === botao));
  moverDestaque(cvVisualizacao);
  cvEstado.visualizacao = botao.dataset.visualizacao;
  cvEstado.periodo_id = null;
  await carregarCoverage();
});
window.addEventListener('resize', () => moverDestaque(cvVisualizacao));

const cvAplicar = document.getElementById('cv-aplicar-todos');
cvAplicar.addEventListener('click', () => comCarregando(cvAplicar, async () => {
  const pedidos = [['dias', document.getElementById('cv-todos-dias')],
    ['horas', document.getElementById('cv-todos-horas')]].filter(([, campo]) => campo.value !== '');
  if (!pedidos.length) {
    cvStatus.textContent = 'Digite os dias ou as horas que valem para todos os usuários desta tela.';
    return;
  }
  for (const [campo, entrada] of pedidos) {
    const resposta = await pywebview.api.set_coverage_todos(
      cvEstado.operacao, cvEstado.visualizacao, cvEstado.mes, cvEstado.periodo_id, campo, entrada.value,
      cvEstado.gestor || null);
    if (!resposta.success) {
      cvStatus.textContent = resposta.message;
      return;
    }
    entrada.value = '';
  }
  await carregarCoverage();
  cvStatus.textContent = `Aplicado a ${plural(cvTela.linhas.length, 'usuário', 'usuários')} desta tela.`;
}));

// ---------------------------------------------------------------
// Aba Horas Indiretas
// ---------------------------------------------------------------
// Uma extracao propria (Week + Job Code, fixos) e so a visao por
// semana: o mes escolhe quais semanas aparecem. Os numeros e as cores
// vem prontos do Python (indiretas_tela.py); aqui so se desenha.

const indEstado = { operacao: null, mes: null, semana_id: null, vis: 'semanas' };
let indTela = null;
let indExtraindo = false;
const indOperacao = document.getElementById('ind-operacao');
const indMes = document.getElementById('ind-mes');
const indSemana = document.getElementById('ind-semana');
const indVisualizacao = document.getElementById('ind-visualizacao');
const indExtOperacao = document.getElementById('ind-ext-operacao');
const indExtDe = document.getElementById('ind-ext-de');
const indExtAte = document.getElementById('ind-ext-ate');
const indExtrairBtn = document.getElementById('ind-extrair');
const indStatus = document.getElementById('ind-status');

function horas(valor) {
  return valor === null || valor === undefined ? '—' : `${num(valor)} h`;
}

function selo(percentual, cor) {
  const el = document.createElement('span');
  el.className = `ind-pct ${cor || ''}`;
  el.textContent = pct(percentual);
  return el;
}

async function carregarIndiretas() {
  const conteudo = document.getElementById('ind-vis-semanas');
  if (!indTela) conteudo.innerHTML = '<div class="ind-semanas"><div class="ind-esqueleto"></div><div class="ind-esqueleto"></div><div class="ind-esqueleto"></div><div class="ind-esqueleto"></div></div>';
  indTela = await pywebview.api.get_indiretas(indEstado.operacao, indEstado.mes, indEstado.semana_id);
  indEstado.operacao = indTela.operacao;
  indEstado.mes = indTela.mes;
  indEstado.semana_id = indTela.semana_id;
  desenharIndiretas();
}

// Datas sugeridas para extrair o mes escolhido: do domingo da semana do
// dia 1 (cobre as operacoes que fecham a semana no domingo e as que
// fecham na segunda) ate ontem, ou ate o fim do mes se ele ja passou.
function sugerirDatasIndiretas(mes) {
  const [ano, numeroDoMes] = mes.split('-').map(Number);
  const primeiro = new Date(ano, numeroDoMes - 1, 1);
  const de = new Date(primeiro);
  de.setDate(primeiro.getDate() - primeiro.getDay());
  const ultimo = new Date(ano, numeroDoMes, 0);
  const ontem = new Date();
  ontem.setDate(ontem.getDate() - 1);
  indExtDe.value = toInputDate(de);
  indExtAte.value = toInputDate(ontem < ultimo ? ontem : ultimo);
}

function desenharIndiretas() {
  const t = indTela;
  preencherSelect(indOperacao, t.operacoes, t.operacao, 'key', 'label');
  preencherSelect(indMes, t.meses, t.mes);
  if (t.periodos.length) {
    preencherSelect(indSemana, t.periodos, t.semana_id);
  } else {
    preencherSelect(indSemana, [{ id: '', rotulo: 'Nenhuma semana extraída neste mês' }], '');
  }
  indSemana.disabled = !t.periodos.length;

  // A faixa de extracao segue a operacao do filtro (em "Todas", a primeira).
  preencherSelect(indExtOperacao, t.operacoes.filter((o) => o.key !== 'todas'),
    t.operacao !== 'todas' ? t.operacao : (indExtOperacao.value || t.operacoes[1]?.key), 'key', 'label');
  if (!indExtraindo) sugerirDatasIndiretas(t.mes);
  const ultima = document.getElementById('ind-ultima');
  ultima.hidden = !t.ultima_extracao;
  ultima.textContent = t.ultima_extracao || '';

  desenharCardsIndiretas(t);

  const vazio = !t.semanas.length;
  const vazioEl = document.getElementById('ind-vazio');
  vazioEl.hidden = !vazio;
  document.getElementById('ind-rodape').hidden = vazio;
  for (const vis of ['semanas', 'barras', 'pareto']) {
    document.getElementById(`ind-vis-${vis}`).hidden = vazio || indEstado.vis !== vis;
  }
  if (vazio) {
    document.getElementById('ind-vazio-titulo').textContent =
      `Nenhuma extração de Horas Indiretas de ${t.operacao_rotulo} em ${t.mes_rotulo} ainda`;
    const anterior = document.getElementById('ind-vazio-anterior');
    anterior.hidden = !t.mes_anterior;
    if (t.mes_anterior) {
      anterior.textContent = `Ver ${t.mes_anterior.rotulo}`;
      anterior.dataset.mes = t.mes_anterior.id;
    }
    return;
  }

  const rodape = document.getElementById('ind-rodape');
  rodape.innerHTML = '';
  rodape.append(`Limite de atenção: ${pct(t.limite)} — acima disso a semana fica em vermelho. `
    + 'Horas totais = Total + refeição (UnPd Brk); indiretas = Unmeasured Signon Indirect + PD Brk + UnPd Brk.');

  desenharSemanasIndiretas(t);
  desenharBarrasIndiretas(t);
  desenharParetoIndiretas(t);
  for (const wrap of document.querySelectorAll('#page-indiretas .ind-tabela-wrap')) {
    wrap.replaceChildren(tabelaIndiretasComCopia(t));
  }
}

function desenharCardsIndiretas(t) {
  const c = t.cards;
  document.getElementById('ind-card-operacao').textContent = c.operacao;
  document.getElementById('ind-card-periodo').textContent = c.periodo || '—';
  document.getElementById('ind-card-periodo-nota').textContent = c.periodo_nota || '';
  document.getElementById('ind-card-totais').textContent = horas(c.horas_totais);
  document.getElementById('ind-card-indiretas').textContent = horas(c.horas_indiretas);
  document.getElementById('ind-card-atividades').textContent =
    c.horas_indiretas === null ? '' : plural(c.atividades, 'atividade', 'atividades');
  const valor = document.getElementById('ind-card-percentual');
  valor.textContent = c.percentual === null ? '—' : pct(c.percentual);
  valor.closest('.hc-card').classList.toggle('alerta', c.cor === 'vermelho');
  document.getElementById('ind-card-percentual-nota').textContent = c.horas_totais === null
    ? `limite ${pct(t.limite)}`
    : `de ${horas(c.horas_totais)} totais · limite ${pct(t.limite)}`;
}

function linhaIndireta(colunas) {
  const linha = document.createElement('div');
  linha.className = 'ind-linha';
  for (const coluna of colunas) {
    const celula = typeof coluna === 'string' ? document.createElement('span') : coluna;
    if (typeof coluna === 'string') celula.textContent = coluna;
    linha.appendChild(celula);
  }
  return linha;
}

function trilho(proporcao) {
  const el = document.createElement('div');
  el.className = 'ind-trilho';
  const barra = document.createElement('span');
  barra.style.width = `${Math.max(0, Math.min(100, proporcao * 100))}%`;
  el.appendChild(barra);
  return el;
}

function desenharSemanasIndiretas(t) {
  const grade = document.createElement('div');
  grade.className = 'ind-semanas';
  for (const semana of t.semanas) {
    const quadro = document.createElement('div');
    quadro.className = 'ind-quadro' + (semana.id === t.semana_id ? ' selecionado' : '');

    const topo = document.createElement('div');
    topo.className = 'ind-quadro-topo';
    topo.title = 'Ver esta semana nos cards e nos gráficos';
    const titulo = document.createElement('strong');
    titulo.textContent = semana.rotulo;
    const datas = document.createElement('span');
    datas.textContent = semana.datas;
    if (semana.parcial) {
      datas.textContent += ' · ';
      const aviso = document.createElement('span');
      aviso.className = 'ind-incompleta';
      aviso.textContent = 'incompleta';
      datas.appendChild(aviso);
    }
    const copiar = document.createElement('button');
    copiar.type = 'button';
    copiar.className = 'copy-btn ind-copiar';
    copiar.textContent = 'Copiar';
    copiar.setAttribute('aria-label', `Copiar o quadro de ${semana.rotulo} para o PowerPoint`);
    copiar.title = 'Copia o quadro da semana (totais e atividades) para colar no PowerPoint ou no Excel.';
    copiar.addEventListener('click', (evento) => {
      evento.stopPropagation(); // o topo do quadro escolhe a semana
      const linhas = linhasDoQuadroIndiretas(semana);
      copiarComAviso(copiar, textoParaColar(linhas), tabelaParaColar(linhas),
        `quadro da ${semana.rotulo} (${plural(semana.atividades.length, 'atividade', 'atividades')})`);
    });
    const cabecaTopo = document.createElement('div');
    cabecaTopo.className = 'ind-quadro-titulo';
    cabecaTopo.append(titulo, copiar);
    topo.append(cabecaTopo, datas);
    topo.addEventListener('click', () => escolherSemanaIndiretas(semana.id));

    const totais = document.createElement('div');
    totais.className = 'ind-totais';
    const pctTotal = document.createElement('span');
    pctTotal.textContent = '100,00%';
    totais.append(
      linhaIndireta(['Horas totais', num(semana.horas_totais), pctTotal]),
      linhaIndireta(['Totais indiretas', num(semana.horas_indiretas), selo(semana.percentual, semana.cor)]),
    );

    const cabecalho = linhaIndireta(['Indiretas', 'Horas', '%']);
    cabecalho.classList.add('ind-cabecalho');

    const lista = document.createElement('div');
    lista.className = 'ind-lista';
    const maior = semana.atividades[0]?.horas || 0;
    for (const atividade of semana.atividades) {
      const item = document.createElement('div');
      item.className = 'ind-atividade' + (atividade.maior ? ' maior' : '');
      item.title = `${atividade.atividade}: ${horas(atividade.horas)} · ${pct(atividade.percentual)} do total · `
        + `${pct(atividade.percentual_indiretas)} das indiretas`;
      item.append(linhaIndireta([atividade.atividade, num(atividade.horas), pct(atividade.percentual)]),
        trilho(maior ? atividade.horas / maior : 0));
      lista.appendChild(item);
    }
    quadro.append(topo, totais, cabecalho, lista);
    grade.appendChild(quadro);
  }
  document.getElementById('ind-vis-semanas').replaceChildren(grade);
}

// O quadro da semana como a planilha de referencia: totais em cima, o
// cabecalho das indiretas e as atividades da maior para a menor.
function linhasDoQuadroIndiretas(semana) {
  const esquerda = (texto, negrito = false) => ({ texto, alinhamento: 'left', negrito });
  return [
    [esquerda('Horas totais', true), num(semana.horas_totais), '100,00%'],
    [esquerda('Totais indiretas', true), num(semana.horas_indiretas), pct(semana.percentual)],
    [esquerda('Indiretas', true), { texto: 'Horas', negrito: true }, { texto: '%', negrito: true }],
    ...semana.atividades.map((a) => [esquerda(a.atividade), num(a.horas), pct(a.percentual)]),
  ];
}

// A tabela atividade x semana, com o cabecalho das semanas.
function linhasDaTabelaIndiretas(t) {
  const esquerda = (texto, negrito = false) => ({ texto, alinhamento: 'left', negrito });
  const cabecalho = [esquerda('Atividade', true),
    ...t.semanas.map((s) => ({ texto: `${s.rotulo} (${s.datas})`, negrito: true }))];
  const linhas = t.tabela.linhas.map((linha) => [esquerda(linha.atividade), ...t.semanas.map((s) => {
    const celula = linha.celulas[s.id];
    return celula ? `${num(celula.horas)} h · ${pct(celula.percentual)}` : '—';
  })]);
  const total = [esquerda('TOTAL INDIRETAS', true), ...t.semanas.map((s) => `${num(t.tabela.totais[s.id].horas)} h`)];
  const percentual = [esquerda('% INDIRETA', true), ...t.semanas.map((s) => pct(t.tabela.totais[s.id].percentual))];
  return [cabecalho, ...linhas, total, percentual];
}

function tabelaIndiretasComCopia(t) {
  const caixa = document.createElement('div');
  const barra = document.createElement('div');
  barra.className = 'ind-tabela-topo';
  const titulo = document.createElement('span');
  titulo.textContent = `Atividades × semanas · ${t.mes_rotulo}`;
  const copiar = document.createElement('button');
  copiar.type = 'button';
  copiar.className = 'copy-btn';
  copiar.textContent = 'Copiar tabela';
  copiar.title = 'Copia a tabela inteira para colar no PowerPoint ou no Excel.';
  copiar.addEventListener('click', () => {
    const linhas = linhasDaTabelaIndiretas(t);
    copiarComAviso(copiar, textoParaColar(linhas), tabelaParaColar(linhas),
      `tabela de ${plural(t.semanas.length, 'semana', 'semanas')} de ${t.mes_rotulo}`);
  });
  barra.append(titulo, copiar);
  // So a tabela rola; a barra com o Copiar fica parada em cima.
  const rolagem = document.createElement('div');
  rolagem.className = 'ind-tabela-rolagem';
  rolagem.appendChild(tabelaIndiretas(t));
  caixa.append(barra, rolagem);
  return caixa;
}

function semanaEscolhida(t) {
  return t.semanas.find((s) => s.id === t.semana_id) || t.semanas[t.semanas.length - 1];
}

function desenharBarrasIndiretas(t) {
  const semana = semanaEscolhida(t);
  const area = document.getElementById('ind-barras');
  area.innerHTML = '';
  const titulo = document.createElement('p');
  titulo.className = 'ind-barras-titulo';
  titulo.textContent = `${semana.rotulo} · ${semana.datas} — da maior para a menor`;
  const cabecalho = document.createElement('div');
  cabecalho.className = 'ind-barras-linha cabecalho';
  cabecalho.innerHTML = '<span>Atividade</span><span>Horas</span><span>% total</span><span>% indireta</span>';
  area.append(titulo, cabecalho);
  const maior = semana.atividades[0]?.horas || 0;
  for (const atividade of semana.atividades) {
    const item = document.createElement('div');
    item.className = 'ind-barras-item' + (atividade.maior ? ' maior' : '');
    const linha = document.createElement('div');
    linha.className = 'ind-barras-linha';
    for (const texto of [atividade.atividade, num(atividade.horas), pct(atividade.percentual),
      pct(atividade.percentual_indiretas)]) {
      const celula = document.createElement('span');
      celula.textContent = texto;
      linha.appendChild(celula);
    }
    item.append(linha, trilho(maior ? atividade.horas / maior : 0));
    area.appendChild(item);
  }
  const total = document.createElement('div');
  total.className = 'ind-barras-linha total';
  const nome = document.createElement('span');
  nome.textContent = 'TOTAL INDIRETAS';
  const h = document.createElement('span');
  h.textContent = num(semana.horas_indiretas);
  const cem = document.createElement('span');
  cem.textContent = '100,00%';
  total.append(nome, h, selo(semana.percentual, semana.cor), cem);
  area.appendChild(total);
}

// Pareto da semana escolhida: barras da maior para a menor e a linha do
// acumulado (% das indiretas). Um eixo so (horas); o acumulado tem
// rotulo so no primeiro ponto, no que cruza 80% e no ultimo.
function desenharParetoIndiretas(t) {
  const semana = semanaEscolhida(t);
  document.getElementById('ind-pareto-titulo').textContent =
    `Pareto · ${semana.rotulo} · ${semana.datas}`;
  const svg = document.getElementById('ind-pareto');
  svg.innerHTML = '';
  const atividades = semana.atividades;
  if (!atividades.length) return;
  const L = 900; const topo = 24; const base = 236; const esquerda = 48; const direita = 16;
  const maximo = Math.max(...atividades.map((a) => a.horas)) * 1.1 || 1;
  const y = (v) => base - (v / maximo) * (base - topo);
  const yPct = (p) => base - p * (base - topo);
  const passo = (L - esquerda - direita) / atividades.length;
  const largura = Math.min(56, passo * 0.6);
  const centro = (i) => esquerda + passo * i + passo / 2;

  for (const fracao of [0.25, 0.5, 0.75, 1]) {
    const valor = (maximo / 1.1) * fracao;
    svg.appendChild(elementoSvg('line', { x1: esquerda, x2: L - direita, y1: y(valor), y2: y(valor), class: 'ind-pareto-grade' }));
    svg.appendChild(elementoSvg('text', { x: esquerda - 8, y: y(valor) + 4, 'text-anchor': 'end', class: 'ind-pareto-eixo-texto' }, `${num(Math.round(valor))} h`));
  }
  svg.appendChild(elementoSvg('line', { x1: esquerda, x2: L - direita, y1: base, y2: base, class: 'ind-pareto-eixo' }));

  let acumulado = 0;
  const pontos = [];
  atividades.forEach((atividade, i) => {
    acumulado += atividade.percentual_indiretas || 0;
    pontos.push({ x: centro(i), y: yPct(Math.min(1, acumulado)), valor: acumulado });
    const grupo = elementoSvg('g', { class: 'ind-pareto-faixa' });
    grupo.appendChild(elementoSvg('title', {}, `${atividade.atividade}: ${horas(atividade.horas)} · `
      + `${pct(atividade.percentual)} do total · acumulado ${pct(Math.min(1, acumulado))} das indiretas`));
    grupo.appendChild(elementoSvg('rect', { x: centro(i) - passo / 2, y: topo, width: passo, height: base - topo + 40, fill: 'transparent' }));
    const altura = Math.max(1, base - y(atividade.horas));
    const x = centro(i) - largura / 2;
    const raio = Math.min(4, altura);
    grupo.appendChild(elementoSvg('path', {
      class: 'ind-pareto-barra' + (atividade.maior ? ' maior' : ''),
      d: `M${x},${base} V${base - altura + raio} Q${x},${base - altura} ${x + raio},${base - altura} `
        + `H${x + largura - raio} Q${x + largura},${base - altura} ${x + largura},${base - altura + raio} V${base} Z`,
    }));
    grupo.appendChild(elementoSvg('text', { x: centro(i), y: base + 18, class: 'ind-pareto-nome' }, atividade.atividade));
    grupo.appendChild(elementoSvg('text', { x: centro(i), y: base + 32, class: 'ind-pareto-pct' }, pct(atividade.percentual)));
    svg.appendChild(grupo);
  });

  svg.appendChild(elementoSvg('polyline', {
    class: 'ind-pareto-acumulado', points: pontos.map((p) => `${p.x},${p.y}`).join(' '),
  }));
  pontos.forEach((p) => svg.appendChild(elementoSvg('circle', { cx: p.x, cy: p.y, r: 4, class: 'ind-pareto-ponto' })));

  const cruza80 = pontos.findIndex((p) => p.valor >= 0.8);
  const rotulados = new Set([0, cruza80, pontos.length - 1].filter((i) => i >= 0));
  for (const i of rotulados) {
    const p = pontos[i];
    const texto = pct(Math.min(1, p.valor));
    const larguraRotulo = texto.length * 6.6 + 10;
    const ry = Math.max(4, p.y - 26);
    svg.appendChild(elementoSvg('rect', { x: p.x - larguraRotulo / 2, y: ry, width: larguraRotulo, height: 18, rx: 4, class: 'ind-pareto-rotulo-fundo' }));
    svg.appendChild(elementoSvg('text', { x: p.x, y: ry + 13, class: 'ind-pareto-rotulo' }, texto));
  }
}

function tabelaIndiretas(t) {
  const tabela = document.createElement('table');
  tabela.className = 'ind-tabela';
  const cabecalho = t.semanas.map((s) =>
    `<th class="${s.id === t.semana_id ? 'selecionada' : ''}">${s.rotulo}<br><span>${s.datas}</span></th>`).join('');
  tabela.innerHTML = `<thead><tr><th>Atividade</th>${cabecalho}</tr></thead><tbody></tbody><tfoot></tfoot>`;
  const corpo = tabela.querySelector('tbody');
  for (const linha of t.tabela.linhas) {
    const tr = document.createElement('tr');
    const nome = document.createElement('td');
    nome.textContent = linha.atividade;
    tr.appendChild(nome);
    for (const semana of t.semanas) {
      const celula = linha.celulas[semana.id];
      const td = document.createElement('td');
      if (celula) {
        td.textContent = `${num(celula.horas)} h`;
        const p = document.createElement('span');
        p.className = 'ind-pct-celula';
        p.textContent = `· ${pct(celula.percentual)}`;
        td.appendChild(p);
      } else {
        td.className = 'vazia';
        td.textContent = '—';
      }
      tr.appendChild(td);
    }
    corpo.appendChild(tr);
  }
  const rodape = tabela.querySelector('tfoot');
  const total = document.createElement('tr');
  total.className = 'total';
  const percentual = document.createElement('tr');
  percentual.className = 'percentual';
  const rotuloTotal = document.createElement('td');
  rotuloTotal.textContent = 'TOTAL INDIRETAS';
  const rotuloPct = document.createElement('td');
  rotuloPct.textContent = '% INDIRETA';
  total.appendChild(rotuloTotal);
  percentual.appendChild(rotuloPct);
  for (const semana of t.semanas) {
    const soma = t.tabela.totais[semana.id];
    const td = document.createElement('td');
    td.textContent = `${num(soma.horas)} h`;
    total.appendChild(td);
    const tdPct = document.createElement('td');
    tdPct.appendChild(selo(soma.percentual, soma.cor));
    percentual.appendChild(tdPct);
  }
  rodape.append(total, percentual);
  return tabela;
}

async function escolherSemanaIndiretas(id) {
  indEstado.semana_id = id;
  await carregarIndiretas();
}

indOperacao.addEventListener('change', async () => {
  indEstado.operacao = indOperacao.value;
  indEstado.semana_id = null;
  await carregarIndiretas();
});
indMes.addEventListener('change', async () => {
  indEstado.mes = indMes.value;
  indEstado.semana_id = null;
  await carregarIndiretas();
});
indSemana.addEventListener('change', () => escolherSemanaIndiretas(indSemana.value));
indVisualizacao.addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (!botao) return;
  indVisualizacao.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b === botao));
  moverDestaque(indVisualizacao);
  indEstado.vis = botao.dataset.vis;
  if (indTela) desenharIndiretas();
});
window.addEventListener('resize', () => moverDestaque(indVisualizacao));

document.getElementById('ind-vazio-extrair').addEventListener('click', () => {
  document.getElementById('ind-extracao').scrollIntoView({ block: 'nearest', behavior: SEM_ANIMACAO ? 'auto' : 'smooth' });
  indExtrairBtn.focus();
});
document.getElementById('ind-vazio-anterior').addEventListener('click', async (evento) => {
  indEstado.mes = evento.currentTarget.dataset.mes;
  indEstado.semana_id = null;
  await carregarIndiretas();
});

// Etapas da automacao na faixa de extracao (as mesmas do Extrair Dados).
function progressoIndiretas(texto) {
  const lower = texto.toLowerCase();
  const indice = PROGRESS_STEPS.findIndex((def) => def.match(lower));
  document.getElementById('ind-progresso-texto').textContent = texto;
  if (indice >= 0) {
    document.getElementById('ind-progresso-preenchido').style.width =
      `${Math.round(((indice + 1) / PROGRESS_STEPS.length) * 100)}%`;
  }
}

indExtrairBtn.addEventListener('click', async () => {
  indStatus.hidden = true;
  if (!indExtDe.value || !indExtAte.value) {
    showStatus(indStatus, 'Preencha as datas De e Até.', 'error');
    return;
  }
  if (indExtDe.value > indExtAte.value) {
    showStatus(indStatus, 'A data "De" não pode ser depois da data "Até".', 'error');
    return;
  }
  if (!(await ensureFolderConfigured())) {
    showStatus(indStatus, 'É necessário selecionar a pasta do SharePoint antes de extrair.', 'error');
    return;
  }
  const progresso = document.getElementById('ind-progresso');
  progresso.hidden = false;
  document.getElementById('ind-progresso-preenchido').style.width = '0%';
  progressoIndiretas('Iniciando a extração...');
  indExtraindo = true;
  await comCarregando(indExtrairBtn, async () => {
    try {
      const resultado = await pywebview.api.run_extraction(
        indExtOperacao.value, { from_date: indExtDe.value, to_date: indExtAte.value }, 'Job Code', 'indiretas');
      const desfecho = desfechoDe(resultado);
      showStatus(indStatus, resultado.indicators_message || resultado.message, desfecho.classe);
      if (resultado.success) {
        document.getElementById('ind-progresso-preenchido').style.width = '100%';
        indEstado.operacao = indExtOperacao.value;
        indEstado.semana_id = null;
      }
    } catch (erro) {
      registrarErro('extração de horas indiretas', erro);
      showStatus(indStatus, 'Não deu para extrair. Veja o log em Configurações > Gerar diagnóstico.', 'error');
    } finally {
      indExtraindo = false;
      progresso.hidden = true;
    }
  });
  await carregarIndiretas();
});

// ---------------------------------------------------------------
// Abas Resultado Gestor e Resultado Turno
// ---------------------------------------------------------------
// A mesma tabela da aba Inicio, uma por gestor (ou turno). No topo, a
// lista para marcar quais aparecem, como a lista de operacoes do Extrair
// Multiplos. Os numeros e as cores vem prontos do Python (grupos_tela.py).

function criarAbaDeGrupo(dimensao, pre) {
  const el = (id) => document.getElementById(`${pre}-${id}`);
  const estado = { operacao: null, mes: null, vis: 'tabelas', periodoResumo: null };
  // Tabelas recolhidas nesta sessao (por nome do grupo).
  const recolhidos = new Set();
  const nomes = dimensao === 'gestor'
    ? { singular: 'Gestor', plural: 'gestores', tipo: 'Gestor · Week', mes: 'Gestor · Month', nivel: 'Supervisor' }
    : { singular: 'Turno', plural: 'turnos', tipo: 'Turno · Week', mes: 'Turno · Month', nivel: 'Shift' };
  const tipoWeek = `${dimensao}_week`;
  let tela = null;

  async function carregar() {
    const tabelas = el('tabelas');
    if (!tela) tabelas.innerHTML = '<div class="card indicators-card"><div class="ind-esqueleto grupos-esqueleto"></div></div>';
    tela = await pywebview.api.get_resultado_grupo(dimensao, estado.operacao, estado.mes);
    estado.operacao = tela.operacao;
    estado.mes = tela.mes;
    desenhar();
  }

  function desenhar() {
    preencherSelect(el('operacao'), tela.operacoes, tela.operacao, 'key', 'label');
    preencherSelect(el('mes'), tela.meses, tela.mes);
    el('ultima').textContent = tela.ultima_extracao || `Nenhuma extração de ${tela.operacao_rotulo} neste mês ainda`;

    const temDados = tela.colunas.length > 0;
    el('grupos-card').hidden = !temDados;
    el('vazio').hidden = temDados;
    el('legenda').hidden = !temDados || !tela.tabelas.length;
    const porGrupo = estado.vis === 'tabelas';
    el('navegacao').hidden = !temDados || !porGrupo || tela.tabelas.length < 2;
    el('resumo').hidden = !temDados || porGrupo || !tela.tabelas.length;
    el('tabelas').hidden = !porGrupo;
    el('visualizacao').querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b.dataset.vis === estado.vis));
    moverDestaque(el('visualizacao'));
    if (!temDados) {
      el('tabelas').innerHTML = '';
      el('vazio-titulo').textContent =
        `Nenhuma extração ${nomes.tipo} de ${tela.operacao_rotulo} em ${tela.mes_rotulo} ainda`;
      el('vazio-texto').textContent = `Extraia ${nomes.tipo} (Week › ${nomes.nivel} › User ID) e ${nomes.mes} `
        + `(${nomes.nivel} › User ID): cada semana vira uma coluna, o mês entra no final e cada ${nomes.singular.toLowerCase()} ganha a sua tabela.`;
      return;
    }
    desenharLista();
    if (porGrupo) {
      desenharNavegacao();
      desenharTabelas();
    } else {
      desenharResumo();
      if (!tela.tabelas.length) {
        el('tabelas').hidden = false;
        desenharTabelas(); // mostra o "nenhum marcado"
      }
    }
    el('legenda-nota').textContent = dimensao === 'gestor'
      ? 'Presenteísmo e cubo só para gestor com o mesmo nome no Headcount.'
      : 'Turno não tem presenteísmo: presenteísmo e cubo não se aplicam.';
  }

  function desenharLista() {
    const lista = el('lista');
    lista.innerHTML = '';
    for (const grupo of tela.grupos) {
      const item = document.createElement('label');
      item.className = 'ops-item grupo-item' + (grupo.visivel ? ' selected' : '');
      const caixa = document.createElement('input');
      caixa.type = 'checkbox';
      caixa.checked = grupo.visivel;
      caixa.value = grupo.id;
      caixa.addEventListener('change', () => {
        item.classList.toggle('selected', caixa.checked);
        salvarVisiveis();
      });
      const nome = document.createElement('span');
      nome.className = 'grupo-nome';
      nome.textContent = grupo.rotulo;
      nome.title = grupo.rotulo;
      item.append(caixa, nome);
      if (grupo.vinculado) {
        const selo = document.createElement('span');
        selo.className = 'grupo-selo';
        selo.textContent = 'HC';
        selo.title = 'Presenteísmo do Headcount: há um gestor com este mesmo nome lá.';
        item.appendChild(selo);
      }
      lista.appendChild(item);
    }
    const visiveis = tela.grupos.filter((g) => g.visivel).length;
    el('contador').textContent = `· ${visiveis} de ${tela.grupos.length}`;
    el('nota').textContent = dimensao === 'gestor'
      ? 'O nome é o da planilha. O presenteísmo e o cubo aparecem para quem está no Headcount com o mesmo nome (marcado com HC); nome diferente não puxa nada.'
      : 'Os turnos são os que vieram no arquivo extraído (coluna Shift).';
  }

  async function salvarVisiveis(todos) {
    const caixas = Array.from(el('lista').querySelectorAll('input[type="checkbox"]'));
    if (todos !== undefined) {
      caixas.forEach((c) => { c.checked = todos; c.parentElement.classList.toggle('selected', todos); });
    }
    const resposta = await pywebview.api.set_grupos_visiveis(
      dimensao, estado.operacao, tela.grupos.map((g) => g.id), caixas.filter((c) => c.checked).map((c) => c.value));
    if (resposta && resposta.success === false) {
      avisarErro(resposta.message);
      return;
    }
    await carregar();
  }

  function desenharTabelas() {
    const area = el('tabelas');
    const antes = new Set(Array.from(area.querySelectorAll('[data-grupo]')).map((c) => c.dataset.grupo));
    area.innerHTML = '';
    if (!tela.tabelas.length) {
      const vazio = document.createElement('div');
      vazio.className = 'card indicators-card grupos-nenhum';
      vazio.textContent = `Nenhum ${nomes.singular.toLowerCase()} marcado. Marque acima quais ${nomes.plural} aparecem.`;
      area.appendChild(vazio);
      return;
    }
    tela.tabelas.forEach((tabela, indice) => {
      const card = document.createElement('div');
      card.className = 'card indicators-card grupo-tabela';
      card.dataset.grupo = tabela.id;
      // So o que acabou de entrar na tela anima; o resto so troca o valor.
      if (!antes.has(tabela.id) && !SEM_ANIMACAO) {
        card.classList.add('grupo-entrando');
        card.style.animationDelay = `${Math.min(indice, 6) * 50}ms`;
      }
      card.id = `${pre}-grupo-${indice}`;
      if (recolhidos.has(tabela.id)) card.classList.add('recolhido');
      const alternar = document.createElement('button');
      alternar.type = 'button';
      alternar.className = 'grupo-alternar';
      alternar.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>';
      const atualizarRotulo = () => {
        const fechado = card.classList.contains('recolhido');
        alternar.title = fechado ? 'Abrir a tabela' : 'Recolher a tabela';
        alternar.setAttribute('aria-expanded', String(!fechado));
      };
      atualizarRotulo();
      alternar.addEventListener('click', () => {
        card.classList.toggle('recolhido');
        if (card.classList.contains('recolhido')) recolhidos.add(tabela.id); else recolhidos.delete(tabela.id);
        atualizarRotulo();
      });
      card.appendChild(alternar);
      card.appendChild(linhaCompacta(tabela, () => alternar.click()));
      const wrap = document.createElement('div');
      wrap.className = 'table-wrap';
      const t = document.createElement('table');
      t.className = 'indicators-table';
      const thead = document.createElement('thead');
      const linhaCabecalho = document.createElement('tr');
      thead.appendChild(linhaCabecalho);
      const corpo = document.createElement('tbody');
      t.append(thead, corpo);
      wrap.appendChild(t);
      card.appendChild(wrap);
      area.appendChild(card);

      let nota = null;
      if (dimensao === 'gestor') {
        nota = tabela.vinculado
          ? { texto: 'presenteísmo do Headcount', classe: 'ok' }
          : { texto: 'sem o mesmo nome no Headcount', classe: 'alerta',
            dica: 'Cadastre no Headcount um gestor com exatamente este nome para o presenteísmo e o cubo aparecerem.' };
      }
      desenharCabecalhoEm(linhaCabecalho, corpo, tela.colunas, nomes.singular, tabela.rotulo, nota);
      desenharLinhasEm(corpo, tabela.linhas, tela.colunas);
      wrap.scrollLeft = wrap.scrollWidth;
    });
  }

  // Recolhida, a tabela vira uma linha: o nome e os seis indicadores da
  // ultima coluna (o mes, se ja foi extraido).
  function linhaCompacta(tabela, abrir) {
    const linha = document.createElement('div');
    linha.className = 'grupo-compacto';
    const ultima = tela.colunas.length - 1;
    const nome = document.createElement('div');
    nome.className = 'grupo-compacto-nome';
    nome.title = 'Abrir a tabela';
    const rotuloDaColuna = tela.colunas[ultima] ? tela.colunas[ultima].titulo : '';
    nome.innerHTML = `<small>${nomes.singular} · ${escaparHtml(rotuloDaColuna)}</small>`;
    nome.appendChild(document.createTextNode(tabela.rotulo));
    nome.addEventListener('click', abrir);
    const valores = document.createElement('div');
    valores.className = 'grupo-compacto-valores';
    for (const indicador of tabela.linhas) {
      const celula = indicador.celulas[ultima] || {};
      const item = document.createElement('div');
      item.className = 'grupo-compacto-valor';
      const rotulo = document.createElement('span');
      rotulo.textContent = indicador.rotulo;
      item.appendChild(rotulo);
      const valor = document.createElement('span');
      if (celula.texto) {
        valor.className = `indicator-value ${celula.cor || ''}`;
        valor.textContent = celula.texto;
      } else {
        valor.className = 'vazio';
        valor.textContent = celula.nao_se_aplica ? '' : '\u2014';
      }
      item.appendChild(valor);
      valores.appendChild(item);
    }
    linha.append(nome, valores);
    return linha;
  }

  // Barra com o nome de cada um: pula ate a tabela dele.
  function desenharNavegacao() {
    const atalhos = el('atalhos');
    atalhos.innerHTML = '';
    tela.tabelas.forEach((tabela, indice) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'grupo-chip';
      chip.textContent = tabela.rotulo;
      chip.title = `Ir para ${tabela.rotulo}`;
      chip.addEventListener('click', () => irParaGrupo(indice));
      atalhos.appendChild(chip);
    });
  }

  function irParaGrupo(indice) {
    const card = document.getElementById(`${pre}-grupo-${indice}`);
    if (!card) return;
    if (card.classList.contains('recolhido')) card.querySelector('.grupo-alternar').click();
    card.scrollIntoView({ block: 'start', behavior: SEM_ANIMACAO ? 'auto' : 'smooth' });
    reiniciarAnimacao(card, 'grupo-destacado');
  }

  function recolherTodas(recolher) {
    for (const tabela of tela.tabelas) {
      if (recolher) recolhidos.add(tabela.id); else recolhidos.delete(tabela.id);
    }
    el('tabelas').querySelectorAll('.grupo-tabela').forEach((card) => {
      card.classList.toggle('recolhido', recolher);
      const botao = card.querySelector('.grupo-alternar');
      botao.title = recolher ? 'Abrir a tabela' : 'Recolher a tabela';
      botao.setAttribute('aria-expanded', String(!recolher));
    });
  }

  // Resumo: uma tabela so, com os grupos nas linhas e os seis indicadores
  // de um periodo nas colunas. Mesmos textos e cores das tabelas.
  function desenharResumo() {
    const periodos = tela.colunas.map((c, i) => ({ id: String(i), rotulo: `${c.titulo} · ${c.subtitulo}` }));
    const ultima = String(tela.colunas.length - 1);
    if (!periodos.some((p) => p.id === estado.periodoResumo)) estado.periodoResumo = ultima;
    preencherSelect(el('resumo-periodo'), periodos, estado.periodoResumo);
    const indice = Number(estado.periodoResumo);
    const coluna = tela.colunas[indice];
    el('resumo-sub').textContent = `${coluna.titulo} (${coluna.subtitulo}) · ${plural(tela.tabelas.length, nomes.singular.toLowerCase(), nomes.plural)} marcados. Clique no nome para abrir a tabela.`;

    const indicadores = tela.tabelas[0].linhas;
    const cabecalho = el('resumo-cabecalho');
    const corpo = el('resumo-corpo');
    cabecalho.innerHTML = '';
    const canto = document.createElement('th');
    canto.className = 'resumo-canto';
    canto.innerHTML = `<div class="corner-label">${nomes.singular}</div>`;
    const copiarTudo = document.createElement('button');
    copiarTudo.type = 'button';
    copiarTudo.className = 'copy-btn resumo-copiar-tudo';
    copiarTudo.textContent = 'Copiar tabela';
    copiarTudo.title = 'Copia nomes e valores para colar no PowerPoint ou no Excel.';
    copiarTudo.addEventListener('click', () => {
      const linhas = [[{ texto: nomes.singular, alinhamento: 'left', negrito: true },
        ...indicadores.map((i) => ({ texto: i.rotulo, negrito: true }))]];
      corpo.querySelectorAll('tr').forEach((tr, r) => {
        linhas.push([{ texto: tela.tabelas[r].rotulo, alinhamento: 'left' },
          ...indicadores.map((_, c) => valoresDaColuna(c, corpo)[r])]);
      });
      copiarComAviso(copiarTudo, textoParaColar(linhas), tabelaParaColar(linhas),
        `resumo de ${plural(tela.tabelas.length, nomes.singular.toLowerCase(), nomes.plural)} · ${coluna.titulo}`);
    });
    canto.appendChild(copiarTudo);
    cabecalho.appendChild(canto);
    indicadores.forEach((indicador, c) => {
      const th = document.createElement('th');
      th.className = 'resumo-col';
      th.innerHTML = `<div class="col-title">${escaparHtml(indicador.rotulo)}</div><div class="col-subtitle">${escaparHtml(indicador.meta)}</div>`;
      th.appendChild(botaoCopiar(c, `${indicador.rotulo} (${coluna.titulo})`, corpo));
      cabecalho.appendChild(th);
    });

    corpo.innerHTML = '';
    tela.tabelas.forEach((tabela, r) => {
      const tr = document.createElement('tr');
      const nome = document.createElement('th');
      nome.scope = 'row';
      nome.className = 'resumo-nome';
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.textContent = tabela.rotulo;
      botao.title = 'Abrir a tabela deste ' + nomes.singular.toLowerCase();
      botao.addEventListener('click', async () => {
        estado.vis = 'tabelas';
        desenhar();
        requestAnimationFrame(() => irParaGrupo(r));
      });
      nome.appendChild(botao);
      if (dimensao === 'gestor' && !tabela.vinculado) {
        const nota = document.createElement('small');
        nota.textContent = 'sem o mesmo nome no Headcount';
        nome.appendChild(nota);
      }
      tr.appendChild(nome);
      for (const indicador of tabela.linhas) {
        const celula = indicador.celulas[indice] || {};
        const td = document.createElement('td');
        td.className = 'indicator-cell';
        if (celula.nao_se_aplica) {
          td.classList.add('nao-se-aplica');
          if (celula.copia_vazia) td.dataset.copiaVazia = '1';
        } else if (celula.texto) {
          const valor = document.createElement('span');
          valor.className = `indicator-value ${celula.cor || ''}`;
          valor.textContent = celula.texto;
          td.appendChild(valor);
        } else {
          td.classList.add('sem-numero');
          td.textContent = '\u2014';
        }
        tr.appendChild(td);
      }
      corpo.appendChild(tr);
    });
    entrarEmSequencia(corpo);
  }

  el('visualizacao').addEventListener('click', (evento) => {
    const botao = evento.target.closest('.seg-opcao');
    if (!botao || botao.dataset.vis === estado.vis) return;
    estado.vis = botao.dataset.vis;
    if (tela) desenhar();
  });
  window.addEventListener('resize', () => moverDestaque(el('visualizacao')));
  el('resumo-periodo').addEventListener('change', () => {
    estado.periodoResumo = el('resumo-periodo').value;
    desenharResumo();
  });
  el('abrir-todas').addEventListener('click', () => recolherTodas(false));
  el('fechar-todas').addEventListener('click', () => recolherTodas(true));

  el('operacao').addEventListener('change', async () => {
    estado.operacao = el('operacao').value;
    await carregar();
  });
  el('mes').addEventListener('change', async () => {
    estado.mes = el('mes').value;
    await carregar();
  });
  el('todos').addEventListener('click', () => salvarVisiveis(true));
  el('nenhum').addEventListener('click', () => salvarVisiveis(false));
  const extrair = () => irParaExtracao(estado.operacao, tipoWeek);
  el('ir-extrair').addEventListener('click', extrair);
  el('vazio-extrair').addEventListener('click', extrair);

  return { carregar };
}

const abaGestor = criarAbaDeGrupo('gestor', 'rg');
const abaTurno = criarAbaDeGrupo('turno', 'rt');

// ---------------------------------------------------------------
// Preferencias de tela: tema, densidade e menu recolhido
// ---------------------------------------------------------------
// Guardadas pelo Python (settings.json): a janela do app nao guarda o
// localStorage de uma abertura para a outra. So aparencia.

let preferencias = { tema: 'escuro', densidade: 'confortavel', menu_recolhido: false };
const navRecolher = document.getElementById('nav-recolher');

async function carregarPreferencias() {
  try {
    preferencias = { ...preferencias, ...(await pywebview.api.get_preferencias()) };
  } catch (erro) {
    // sem a ponte, fica o padrao
  }
  aplicarPreferencias(false);
}

function aplicarPreferencias(comTransicao = true) {
  const raiz = document.documentElement;
  const trocouTema = raiz.dataset.tema !== preferencias.tema;
  if (comTransicao && trocouTema && !SEM_ANIMACAO) {
    // As cores trocam suavemente em vez de piscar.
    raiz.classList.add('trocando-tema');
    clearTimeout(aplicarPreferencias.timer);
    aplicarPreferencias.timer = setTimeout(() => raiz.classList.remove('trocando-tema'), 400);
  }
  raiz.dataset.tema = preferencias.tema;
  raiz.dataset.densidade = preferencias.densidade;
  document.body.classList.toggle('menu-recolhido', Boolean(preferencias.menu_recolhido));
  navRecolher.setAttribute('aria-expanded', String(!preferencias.menu_recolhido));
  navRecolher.title = preferencias.menu_recolhido ? 'Abrir o menu (Ctrl+B)' : 'Recolher o menu (Ctrl+B)';
  document.getElementById('apresentacao-tema').textContent =
    preferencias.tema === 'claro' ? 'Tema escuro' : 'Tema claro';
  const marcar = (id, valor) => {
    const grupo = document.getElementById(id);
    grupo.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b.dataset.valor === valor));
    moverDestaque(grupo);
  };
  marcar('pref-tema', preferencias.tema);
  marcar('pref-densidade', preferencias.densidade);
  marcar('pref-menu', preferencias.menu_recolhido ? 'recolhido' : 'aberto');
  // Larguras e alturas mudaram: o destaque do menu e dos seletores
  // acompanha, e a lista do Coverage recalcula a altura.
  moverIndicadorDoMenu();
  setTimeout(() => window.dispatchEvent(new Event('resize')), 240);
}

async function mudarPreferencia(chave, valor) {
  if (preferencias[chave] === valor) return;
  preferencias = { ...preferencias, [chave]: valor };
  aplicarPreferencias();
  try {
    const resposta = await pywebview.api.set_preferencia(chave, valor);
    if (resposta && resposta.success === false) avisar(resposta.message, 'erro');
  } catch (erro) {
    registrarErro('preferência', erro);
  }
}

const alternarTema = () => mudarPreferencia('tema', preferencias.tema === 'claro' ? 'escuro' : 'claro');
const alternarMenu = () => mudarPreferencia('menu_recolhido', !preferencias.menu_recolhido);

document.getElementById('tema-alternar').addEventListener('click', alternarTema);
document.getElementById('apresentacao-tema').addEventListener('click', alternarTema);
navRecolher.addEventListener('click', alternarMenu);
document.getElementById('pref-tema').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (botao) mudarPreferencia('tema', botao.dataset.valor);
});
document.getElementById('pref-densidade').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (botao) mudarPreferencia('densidade', botao.dataset.valor);
});
document.getElementById('pref-menu').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (botao) mudarPreferencia('menu_recolhido', botao.dataset.valor === 'recolhido');
});
window.addEventListener('resize', () => document.querySelectorAll('.aparencia-opcoes').forEach(moverDestaque));

// ---------------------------------------------------------------
// Atalhos de teclado
// ---------------------------------------------------------------

const ATALHOS = [
  { teclas: ['Ctrl', '1 … 9'], texto: 'Abre as abas do menu, na ordem (1 = Início, 2 = Resultado Gestor…)' },
  { teclas: ['Ctrl', 'E'], texto: 'Extrair Dados, já com a operação da tela' },
  { teclas: ['Ctrl', 'B'], texto: 'Recolhe ou abre o menu' },
  { teclas: ['Ctrl', 'Shift', 'L'], texto: 'Tema claro ou escuro' },
  { teclas: ['?'], texto: 'Mostra esta lista' },
  { teclas: ['Esc'], texto: 'Fecha esta lista ou sai do modo apresentação' },
  { teclas: ['←', '→'], texto: 'Trocam a operação no modo apresentação' },
];

document.querySelectorAll('[data-atalhos-lista]').forEach((lista) => {
  for (const atalho of ATALHOS) {
    const teclas = document.createElement('span');
    teclas.className = 'teclas';
    atalho.teclas.forEach((tecla) => {
      const kbd = document.createElement('kbd');
      kbd.textContent = tecla;
      teclas.appendChild(kbd);
    });
    const texto = document.createElement('span');
    texto.textContent = atalho.texto;
    lista.append(teclas, texto);
  }
});

const janelaAtalhos = document.getElementById('atalhos');
let focoAntesDosAtalhos = null;

function abrirAtalhos() {
  focoAntesDosAtalhos = document.activeElement;
  janelaAtalhos.hidden = false;
  document.getElementById('atalhos-fechar').focus();
}

function fecharAtalhos() {
  janelaAtalhos.hidden = true;
  if (focoAntesDosAtalhos && focoAntesDosAtalhos.focus) focoAntesDosAtalhos.focus();
}

document.getElementById('atalhos-abrir').addEventListener('click', abrirAtalhos);
document.getElementById('atalhos-fechar').addEventListener('click', fecharAtalhos);
janelaAtalhos.addEventListener('click', (evento) => { if (evento.target === janelaAtalhos) fecharAtalhos(); });

// A operacao da tela aberta, para o Ctrl+E ja levar ela para a extracao.
function operacaoDaTela() {
  const pagina = document.querySelector('.page:not([hidden])')?.id;
  const valor = {
    'page-home': homeOperationSelect.value,
    'page-gestor': document.getElementById('rg-operacao').value,
    'page-turno': document.getElementById('rt-operacao').value,
    'page-coverage': cvEstado.operacao,
    'page-indiretas': indOperacao.value,
    'page-headcount': hcEstado.operacao,
  }[pagina];
  const tipo = { 'page-gestor': 'gestor_week', 'page-turno': 'turno_week', 'page-indiretas': 'indiretas' }[pagina];
  return { operacao: valor && valor !== 'todas' ? valor : null, tipo: tipo || null };
}

// Em captura, para fechar a lista de atalhos antes do Esc do modo
// apresentacao.
document.addEventListener('keydown', (evento) => {
  if (appView.hidden) return; // na tela de login nao ha atalho
  if (!janelaAtalhos.hidden) {
    if (evento.key === 'Escape') {
      evento.preventDefault();
      evento.stopImmediatePropagation();
      fecharAtalhos();
    }
    return;
  }
  const digitando = evento.target.closest && evento.target.closest('input, textarea, select, [contenteditable="true"]');
  if (evento.key === '?' && !digitando && !evento.ctrlKey && !evento.altKey) {
    evento.preventDefault();
    abrirAtalhos();
    return;
  }
  if (!evento.ctrlKey || evento.altKey || evento.metaKey) return;
  const tecla = evento.key.toLowerCase();
  if (evento.shiftKey && tecla === 'l') {
    evento.preventDefault();
    alternarTema();
    return;
  }
  if (evento.shiftKey) return;
  // Trocar de aba no meio da apresentacao bagunçaria a tela cheia.
  if (emApresentacao) return;
  const numero = /^Digit([1-9])$/.exec(evento.code) || /^Numpad([1-9])$/.exec(evento.code);
  if (numero) {
    const botao = document.querySelector(`.nav-item[data-atalho="${numero[1]}"]`);
    if (botao) {
      evento.preventDefault();
      showPage(botao.dataset.page);
    }
    return;
  }
  if (tecla === 'b') {
    evento.preventDefault();
    alternarMenu();
  } else if (tecla === 'e') {
    evento.preventDefault();
    const { operacao, tipo } = operacaoDaTela();
    irParaExtracao(operacao, tipo);
  }
}, true);
