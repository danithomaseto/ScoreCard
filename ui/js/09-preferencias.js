// ---------------------------------------------------------------
// Preferencias de tela: tema, densidade e menu recolhido
// ---------------------------------------------------------------
// Guardadas pelo Python (settings.json): a janela do app nao guarda o
// localStorage de uma abertura para a outra. So aparencia.

let preferencias = { tema: 'escuro', densidade: 'confortavel', menu_recolhido: false, animacoes: 'completas' };
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
  definirModoLeve(preferencias.animacoes === 'leves');
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
  marcar('pref-animacoes', preferencias.animacoes);
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
document.getElementById('pref-animacoes').addEventListener('click', (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (botao) mudarPreferencia('animacoes', botao.dataset.valor);
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
