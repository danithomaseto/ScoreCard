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
