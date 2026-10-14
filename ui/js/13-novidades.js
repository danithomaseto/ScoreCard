// ---------------------------------------------------------------
// O que ha de novo e tour do primeiro uso
// ---------------------------------------------------------------
// Ao abrir o app o Python diz o que mostrar (novidades.py): o tour para
// quem nunca usou, a janela de novidades para quem ja usava e abriu uma
// versao nova. Os dois reabrem em Configuracoes > Ajuda.

const janelaNovidades = document.getElementById('novidades');
let focoAntesDasNovidades = null;
let estadoDasNovidades = null;

async function conferirNovidades() {
  try {
    estadoDasNovidades = await pywebview.api.get_novidades();
  } catch (erro) {
    return;
  }
  // Espera a abertura e a Inicio assentarem: o tour recorta pedacos dela.
  await esperar(SEM_ANIMACAO ? 200 : 900);
  if (appView.hidden || emApresentacao) return;
  if (estadoDasNovidades.mostrar === 'tour') iniciarTour();
  else if (estadoDasNovidades.mostrar === 'novidades') abrirNovidades();
}

async function abrirNovidades() {
  if (!estadoDasNovidades) {
    try {
      estadoDasNovidades = await pywebview.api.get_novidades();
    } catch (erro) {
      return;
    }
  }
  const { versao, itens } = estadoDasNovidades;
  document.getElementById('novidades-versao').textContent = versao;
  const lista = document.getElementById('novidades-lista');
  lista.innerHTML = '';
  for (const item of itens) {
    const li = document.createElement('li');
    const titulo = document.createElement('strong');
    titulo.textContent = item.titulo;
    const texto = document.createElement('span');
    texto.textContent = item.texto;
    li.append(titulo, texto);
    lista.appendChild(li);
  }
  if (!itens.length) {
    const li = document.createElement('li');
    li.textContent = 'Nada novo nesta versão.';
    lista.appendChild(li);
  }
  focoAntesDasNovidades = document.activeElement;
  janelaNovidades.hidden = false;
  document.getElementById('novidades-ok').focus();
}

async function fecharNovidades({ comTour = false } = {}) {
  if (janelaNovidades.hidden) return;
  janelaNovidades.hidden = true;
  try {
    estadoDasNovidades = { ...estadoDasNovidades, ...(await pywebview.api.marcar_visto('novidades')) };
  } catch (erro) {
    // so deixa de marcar: a janela volta na proxima abertura
  }
  if (comTour) iniciarTour();
  else if (focoAntesDasNovidades && focoAntesDasNovidades.focus) focoAntesDasNovidades.focus();
}

document.getElementById('novidades-ok').addEventListener('click', () => fecharNovidades());
document.getElementById('novidades-tour').addEventListener('click', () => fecharNovidades({ comTour: true }));
janelaNovidades.addEventListener('click', (evento) => { if (evento.target === janelaNovidades) fecharNovidades(); });

// ---------------------------------------------------------------
// Tour: cinco passos na aba Inicio
// ---------------------------------------------------------------

const PASSOS_DO_TOUR = [
  {
    alvo: '#page-home .filtros-card',
    titulo: 'Operação e mês',
    texto: 'Escolha aqui o que ver. "No SharePoint" mostra a data do relatório mais novo da pasta, que vale para todo mundo, mesmo sem você ter extraído.',
  },
  {
    alvo: '#page-home .indicators-card',
    titulo: 'Os indicadores',
    texto: 'Uma coluna por semana, o mês e o pico. ✓ verde está na meta, ▼ vermelho abaixo e ▲ azul acima do teto. Pare o mouse num número para ver a conta.',
  },
  {
    alvo: '#home-acoes',
    titulo: 'Para a reunião',
    texto: 'Imagem copia a tabela como figura, pronta para colar no PowerPoint. Modo apresentação deixa só a tabela, em tela cheia, e troca de operação sozinho.',
  },
  {
    alvo: '.nav-item[data-page="extract"]',
    titulo: 'Sem número ainda?',
    texto: 'Extraia em Extrair Dados (Ctrl+E). O relatório vai para a pasta do SharePoint e aparece para todos que usam a mesma pasta.',
  },
  {
    alvo: '#paleta-abrir',
    titulo: 'Ache qualquer coisa',
    texto: 'Ctrl+K procura telas, operações e ações: experimente "hughes setembro". A tecla ? mostra todos os atalhos.',
  },
];

const tour = {
  el: document.getElementById('tour'),
  recorte: document.getElementById('tour-recorte'),
  caixa: document.getElementById('tour-caixa'),
  passo: 0,
  focoAntes: null,
};

async function iniciarTour() {
  if (!tour.el.hidden || appView.hidden) return;
  if (emApresentacao) await modoApresentacao(false);
  if (paginaAberta() !== 'home') await showPage('home');
  tour.focoAntes = document.activeElement;
  tour.passo = 0;
  const pontos = document.getElementById('tour-pontos');
  pontos.innerHTML = PASSOS_DO_TOUR.map(() => '<i></i>').join('');
  tour.el.hidden = false;
  mostrarPassoDoTour(true);
}

function alvoDoPasso(indice) {
  const alvo = document.querySelector(PASSOS_DO_TOUR[indice].alvo);
  if (!alvo) return null;
  const caixa = alvo.getBoundingClientRect();
  return caixa.width && caixa.height ? alvo : null;
}

function mostrarPassoDoTour(primeiro = false, direcao = 1) {
  // Passo sem alvo na tela (ex.: menu escondido) e pulado.
  while (tour.passo >= 0 && tour.passo < PASSOS_DO_TOUR.length && !alvoDoPasso(tour.passo)) tour.passo += direcao;
  if (tour.passo < 0) tour.passo = 0;
  if (tour.passo >= PASSOS_DO_TOUR.length) {
    fecharTour();
    return;
  }
  const passo = PASSOS_DO_TOUR[tour.passo];
  const alvo = alvoDoPasso(tour.passo);
  alvo.scrollIntoView({ block: 'nearest', inline: 'nearest' });

  document.getElementById('tour-passo').textContent = `Passo ${tour.passo + 1} de ${PASSOS_DO_TOUR.length}`;
  document.getElementById('tour-titulo').textContent = passo.titulo;
  document.getElementById('tour-texto').textContent = passo.texto;
  document.querySelectorAll('#tour-pontos i').forEach((ponto, i) => ponto.classList.toggle('atual', i === tour.passo));
  document.getElementById('tour-voltar').hidden = tour.passo === 0;
  const ultimo = tour.passo === PASSOS_DO_TOUR.length - 1;
  const proximo = document.getElementById('tour-proximo');
  proximo.textContent = ultimo ? 'Concluir' : 'Próximo';

  posicionarTour();
  if (primeiro) reiniciarAnimacao(tour.caixa, 'entrando');
  proximo.focus();
}

// O recorte abraca o alvo; a caixa vai embaixo, a direita, em cima ou a
// esquerda dele, onde couber primeiro.
function posicionarTour() {
  if (tour.el.hidden) return;
  const alvo = alvoDoPasso(tour.passo);
  if (!alvo) return;
  const r = alvo.getBoundingClientRect();
  const folga = 6;
  const recorte = {
    left: Math.max(4, r.left - folga),
    top: Math.max(4, r.top - folga),
    right: Math.min(innerWidth - 4, r.right + folga),
    bottom: Math.min(innerHeight - 4, r.bottom + folga),
  };
  Object.assign(tour.recorte.style, {
    left: `${recorte.left}px`,
    top: `${recorte.top}px`,
    width: `${recorte.right - recorte.left}px`,
    height: `${recorte.bottom - recorte.top}px`,
  });

  const largura = tour.caixa.offsetWidth;
  const altura = tour.caixa.offsetHeight;
  const margem = 16;
  const distancia = 14;
  const cabeX = (x) => Math.min(Math.max(margem, x), innerWidth - largura - margem);
  const cabeY = (y) => Math.min(Math.max(margem, y), innerHeight - altura - margem);
  const opcoes = [
    { ok: recorte.bottom + distancia + altura <= innerHeight - margem, x: cabeX(recorte.left), y: recorte.bottom + distancia },
    { ok: recorte.right + distancia + largura <= innerWidth - margem, x: recorte.right + distancia, y: cabeY(recorte.top) },
    { ok: recorte.top - distancia - altura >= margem, x: cabeX(recorte.left), y: recorte.top - distancia - altura },
    { ok: recorte.left - distancia - largura >= margem, x: recorte.left - distancia - largura, y: cabeY(recorte.top) },
  ];
  const lugar = opcoes.find((o) => o.ok) || { x: cabeX((innerWidth - largura) / 2), y: cabeY(innerHeight - altura - margem) };
  tour.caixa.style.left = `${lugar.x}px`;
  tour.caixa.style.top = `${lugar.y}px`;
}

async function fecharTour() {
  if (tour.el.hidden) return;
  tour.el.hidden = true;
  try {
    estadoDasNovidades = { ...estadoDasNovidades, ...(await pywebview.api.marcar_visto('tour')) };
  } catch (erro) {
    // so deixa de marcar
  }
  if (tour.focoAntes && tour.focoAntes.focus && tour.focoAntes.isConnected) tour.focoAntes.focus();
}

function andarNoTour(passo) {
  if (passo > 0 && tour.passo === PASSOS_DO_TOUR.length - 1) {
    fecharTour();
    return;
  }
  tour.passo = Math.max(0, tour.passo + passo);
  mostrarPassoDoTour(false, passo);
}

document.getElementById('tour-proximo').addEventListener('click', () => andarNoTour(1));
document.getElementById('tour-voltar').addEventListener('click', () => andarNoTour(-1));
document.getElementById('tour-pular').addEventListener('click', () => fecharTour());
window.addEventListener('resize', posicionarTour);
// A rolagem da pagina mexe no alvo: o recorte vai junto.
document.addEventListener('scroll', () => requestAnimationFrame(posicionarTour), true);

document.getElementById('ajuda-novidades').addEventListener('click', () => abrirNovidades());
document.getElementById('ajuda-tour').addEventListener('click', () => iniciarTour());

// Em captura na janela: roda antes dos atalhos do app (no document), que
// nao valem com o tour ou as novidades abertos.
window.addEventListener('keydown', (evento) => {
  if (!tour.el.hidden) {
    evento.stopImmediatePropagation();
    if (evento.key === 'Escape') {
      evento.preventDefault();
      fecharTour();
    } else if (evento.key === 'ArrowRight' || (evento.key === 'Enter' && !evento.target.closest('button'))) {
      evento.preventDefault();
      andarNoTour(1);
    } else if (evento.key === 'ArrowLeft') {
      evento.preventDefault();
      andarNoTour(-1);
    } else if (evento.key === 'Tab') {
      prenderFoco(evento, tour.caixa);
    }
    return;
  }
  if (!janelaNovidades.hidden) {
    evento.stopImmediatePropagation();
    if (evento.key === 'Escape') {
      evento.preventDefault();
      fecharNovidades();
    } else if (evento.key === 'Tab') {
      prenderFoco(evento, janelaNovidades);
    }
  }
}, true);

// O Tab da volta dentro da janela aberta.
function prenderFoco(evento, caixa) {
  const focaveis = [...caixa.querySelectorAll('button, input, select, [tabindex="0"]')]
    .filter((el) => !el.hidden && !el.disabled && el.getClientRects().length);
  if (!focaveis.length) return;
  const i = focaveis.indexOf(document.activeElement);
  evento.preventDefault();
  const proximo = evento.shiftKey ? (i <= 0 ? focaveis.length - 1 : i - 1) : (i + 1) % focaveis.length;
  focaveis[proximo].focus();
}
