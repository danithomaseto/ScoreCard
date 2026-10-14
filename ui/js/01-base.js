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

// Respostas fora de ordem: cada chamada ao Python roda numa thread, e a
// resposta de um filtro antigo pode chegar depois da do filtro novo
// (troca rapida de operacao, ou a leitura do SharePoint redesenhando a
// aba). Cada aba numera os pedidos e so a resposta do mais novo desenha.
const pedidosDaTela = {};
function novoPedido(aba) {
  pedidosDaTela[aba] = (pedidosDaTela[aba] || 0) + 1;
  return pedidosDaTela[aba];
}
function pedidoVale(aba, numero) {
  return pedidosDaTela[aba] === numero;
}

// Barra fina no topo enquanto o app consulta o Python (filtros, abas).
// So aparece se a consulta passar de um instante; as longas (extracao,
// leitura do SharePoint, VPN) tem o andamento proprio e ficam de fora.
const CONSULTAS_COM_BARRA = /^(get_|set_|add_|update_|edit_|remove_|validate_)/;
const barraDeCarregamento = { pendentes: 0, timer: null };

function comBarraDeCarregamento(api) {
  return new Proxy(api, {
    get(alvo, nome) {
      const original = alvo[nome];
      if (typeof original !== 'function' || !CONSULTAS_COM_BARRA.test(String(nome))) return original;
      return (...args) => {
        consultaComecou();
        let resposta;
        try {
          resposta = original.apply(alvo, args);
        } catch (erro) {
          consultaTerminou();
          throw erro;
        }
        return Promise.resolve(resposta).finally(consultaTerminou);
      };
    },
  });
}

function consultaComecou() {
  barraDeCarregamento.pendentes += 1;
  if (barraDeCarregamento.pendentes === 1) {
    clearTimeout(barraDeCarregamento.timer);
    barraDeCarregamento.timer = setTimeout(() => {
      const barra = document.getElementById('carregando-barra');
      barra.classList.remove('terminando');
      barra.classList.add('ativa');
    }, 160);
  }
}

function consultaTerminou() {
  barraDeCarregamento.pendentes = Math.max(0, barraDeCarregamento.pendentes - 1);
  if (barraDeCarregamento.pendentes) return;
  clearTimeout(barraDeCarregamento.timer);
  const barra = document.getElementById('carregando-barra');
  if (!barra.classList.contains('ativa')) return;
  barra.classList.add('terminando');
  barraDeCarregamento.timer = setTimeout(() => barra.classList.remove('ativa', 'terminando'), 380);
}

// Os valores que mudaram nas tabelas de indicadores contam do numero
// antigo ate o novo (trocar operacao ou mes, ou dado novo chegando).
function contarValoresQueMudaram(antes) {
  if (SEM_ANIMACAO || !antes || !antes.size) return;
  document.querySelectorAll('.page:not([hidden]) td.indicator-cell').forEach((td) => {
    const chave = chaveDaCelula(td);
    const velhoTexto = chave && antes.get(chave);
    const alvo = td.querySelector('.indicator-value');
    if (!velhoTexto || !alvo) return;
    const novoTexto = alvo.textContent.trim();
    if (velhoTexto === novoTexto) return;
    const velho = lerNumeroBR(velhoTexto);
    const novo = lerNumeroBR(novoTexto);
    if (velho && novo) contarAte(alvo, velho.valor, novo, novoTexto);
  });
}

// Abre ou recolhe um card com a altura animada (a troca de conteudo e
// feita por mudar(); a altura vai da de antes para a de depois).
function animarAltura(elemento, mudar) {
  if (SEM_ANIMACAO) { mudar(); return; }
  const antes = elemento.getBoundingClientRect().height;
  mudar();
  const depois = elemento.getBoundingClientRect().height;
  if (Math.abs(antes - depois) < 2) return;
  elemento.style.height = `${antes}px`;
  elemento.style.overflow = 'hidden';
  elemento.classList.add('mudando-altura');
  void elemento.offsetHeight;
  elemento.style.transition = 'height 300ms cubic-bezier(0.2, 0.8, 0.2, 1)';
  elemento.style.height = `${depois}px`;
  let terminou = false;
  const fim = () => {
    if (terminou) return;
    terminou = true;
    elemento.removeEventListener('transitionend', aoTerminar);
    elemento.style.height = '';
    elemento.style.overflow = '';
    elemento.style.transition = '';
    elemento.classList.remove('mudando-altura');
  };
  // So a transicao da altura do proprio card encerra (as dos filhos,
  // como a seta girando, tambem chegam aqui).
  const aoTerminar = (evento) => {
    if (evento.target === elemento && evento.propertyName === 'height') fim();
  };
  elemento.addEventListener('transitionend', aoTerminar);
  setTimeout(fim, 450);
}

// Enquanto o filtro novo carrega, o que esta na tela esmaece um pouco: da
// para ver que algo esta vindo, sem piscar quando a resposta e rapida.
async function comAtualizando(caixa, carregar) {
  const marca = setTimeout(() => caixa && caixa.classList.add('atualizando'), 140);
  try {
    return await carregar();
  } finally {
    clearTimeout(marca);
    if (caixa) caixa.classList.remove('atualizando');
  }
}

async function comEsqueleto(tbody, colunas, carregar, antesDeMostrar) {
  // Voltando a uma aba que ja tem dados, eles ficam na tela enquanto a
  // atualizacao chega: trocar por barras cinza pareceria mais lento.
  if (tbody.querySelector('tr:not(.linha-esqueleto)')) {
    return comAtualizando(tbody.closest('.card') || tbody, carregar);
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

// O texto do andamento sem acento e em minusculas, para comparar com as
// etapas abaixo ("relatório" e "relatorio" sao a mesma etapa).
function semAcento(texto) {
  return String(texto).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

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
  success: { rotulo: 'Concluída', classe: 'success' },
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
        avisar(result.message || 'Não foi possível abrir.', 'erro');
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
  prepararLogin();
  (loginUsername.value ? loginPassword : loginUsername).focus();
  // Com a abertura na frente, o card entra quando ela sai.
  if (!document.getElementById('abertura')) animarEntradaDoLogin();
}

// Saudacao e fundo conforme a hora, e a VPN conferida na propria tela:
// sem ela o login ate passa (ele e so guardado), mas a extracao nao.
function periodoDoDia(hora = new Date().getHours()) {
  if (hora >= 5 && hora < 12) return { classe: 'periodo-manha', texto: 'Bom dia' };
  if (hora >= 12 && hora < 18) return { classe: 'periodo-tarde', texto: 'Boa tarde' };
  return { classe: 'periodo-noite', texto: 'Boa noite' };
}

function prepararLogin() {
  const periodo = periodoDoDia();
  loginView.classList.remove('periodo-manha', 'periodo-tarde', 'periodo-noite');
  loginView.classList.add(periodo.classe);
  document.getElementById('login-saudacao').textContent = periodo.texto;
  conferirVpnDoLogin();
}

async function conferirVpnDoLogin() {
  const botao = document.getElementById('login-vpn');
  const texto = document.getElementById('login-vpn-texto');
  if (botao.dataset.estado === 'verificando' && botao.dataset.rodando === '1') return;
  botao.dataset.rodando = '1';
  botao.dataset.estado = 'verificando';
  texto.textContent = 'Conferindo a VPN…';
  try {
    const r = await pywebview.api.verificar_vpn();
    botao.dataset.estado = r.estado;
    texto.textContent = { ok: 'VPN conectada', parcial: `VPN: ${r.alcancaveis} de ${r.total}`, fora: 'Sem VPN' }[r.estado]
      || 'VPN conectada';
    botao.title = {
      ok: 'Os servidores das operações respondem. Clique para conferir de novo.',
      parcial: `Só ${r.alcancaveis} de ${r.total} servidores das operações respondem. Clique para conferir de novo.`,
      fora: 'Nenhum servidor das operações responde: conecte a VPN da DHL para extrair. Clique para conferir de novo.',
    }[r.estado] || '';
  } catch (err) {
    botao.dataset.estado = 'fora';
    texto.textContent = 'Não deu para conferir a VPN';
  } finally {
    botao.dataset.rodando = '';
  }
}
document.getElementById('login-vpn').addEventListener('click', conferirVpnDoLogin);

// Mostrar/ocultar a senha (o olho no campo).
document.getElementById('login-olho').addEventListener('click', (evento) => {
  const botao = evento.currentTarget;
  const mostrar = loginPassword.type === 'password';
  loginPassword.type = mostrar ? 'text' : 'password';
  botao.setAttribute('aria-pressed', String(mostrar));
  botao.setAttribute('aria-label', mostrar ? 'Ocultar a senha' : 'Mostrar a senha');
  botao.title = mostrar ? 'Ocultar a senha' : 'Mostrar a senha';
  loginPassword.focus();
});

// Senha recusada pelo Summary: na primeira, um aviso; na segunda seguida,
// o app para de tentar (a fila inteira com a senha errada bloquearia o
// usuario) e oferece sair para entrar de novo.
async function conferirSenhaRecusada(resultado) {
  const vezes = (resultado && resultado.senhas_recusadas) || 0;
  if (vezes === 1) {
    avisar('O Summary recusou a senha', 'erro', 'Confira o usuário e a senha antes de tentar de novo: na segunda recusa o app para.');
  } else if (vezes >= 2) {
    const sair = await perguntar({
      icone: 'erro',
      titulo: 'Senha recusada 2 vezes',
      texto: 'Para não bloquear o seu usuário no Summary, o app parou de tentar.\n'
        + 'Saia, confira a senha entrando no próprio Summary e faça login de novo.',
      botoes: [{ rotulo: 'Agora não', valor: false }, { rotulo: 'Sair e entrar de novo', valor: true, principal: true }],
    });
    if (sair) logoutBtn.click();
  }
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
  atualizarRodape();
  iniciarLeituraDoSharePoint();
  conferirVersaoNova();
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
  aviso.className = `toast ${tipo}`;
  aviso.setAttribute('role', tipo === 'erro' ? 'alert' : 'status');
  aviso.innerHTML = `<svg class="toast-icone" viewBox="0 0 24 24" aria-hidden="true">${ICONES_DO_AVISO[tipo] || ICONES_DO_AVISO.info}</svg>`;
  const corpo = document.createElement('div');
  corpo.textContent = texto;
  if (detalhe) {
    const pequeno = document.createElement('span');
    pequeno.className = 'toast-detalhe';
    pequeno.textContent = detalhe;
    corpo.appendChild(pequeno);
  }
  aviso.appendChild(corpo);
  // Barrinha embaixo mostrando quanto falta para o aviso sumir; com o
  // mouse em cima, o tempo para.
  const duracao = tipo === 'erro' ? 6000 : 3200;
  const tempo = document.createElement('span');
  tempo.className = 'toast-tempo';
  tempo.style.animationDuration = `${duracao}ms`;
  aviso.appendChild(tempo);
  area.appendChild(aviso);
  while (area.children.length > 4) area.firstElementChild.remove();
  const sair = () => {
    if (!aviso.isConnected || aviso.classList.contains('saindo')) return;
    aviso.classList.add('saindo');
    setTimeout(() => aviso.remove(), SEM_ANIMACAO ? 0 : 260);
  };
  aviso.addEventListener('click', sair);
  let restante = duracao;
  let inicio = Date.now();
  let timer = setTimeout(sair, restante);
  aviso.addEventListener('mouseenter', () => {
    clearTimeout(timer);
    restante -= Date.now() - inicio;
  });
  aviso.addEventListener('mouseleave', () => {
    inicio = Date.now();
    timer = setTimeout(sair, Math.max(600, restante));
  });
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
  desenharSelo(); // o selo da extracao some na tela de onde ela saiu
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
