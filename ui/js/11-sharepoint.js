// ---------------------------------------------------------------
// Pasta do SharePoint compartilhada
// ---------------------------------------------------------------
// Toda extracao vai para a pasta do SharePoint, que e a mesma para todo
// mundo. O app le os relatorios que ainda nao tem (arquivos_sharepoint.py)
// ao entrar, ao abrir uma aba de resultado e a cada minuto: quem filtra
// uma operacao ve o que qualquer pessoa extraiu. Ao lado da "Ultima
// extracao" fica a data do relatorio mais novo da pasta (vem do nome do
// arquivo).

const ABAS_COM_DADOS = new Set(['home', 'gestor', 'turno', 'coverage', 'indiretas', 'headcount']);
// Com o observador da pasta ligado (o Python avisa quando algo muda), a
// leitura periodica e so uma rede de seguranca; sem ele, le a cada minuto.
const SP_INTERVALO = 60000;
const SP_INTERVALO_OBSERVANDO = 5 * 60000;
const SP_INTERVALO_MINIMO = 15000;  // trocar de aba nao le de novo antes disto
const sp = { lendo: false, ultima: 0, estado: null, hora: '', relogio: null, pedidos: 0, observando: false, pendente: false };
const seloSp = document.getElementById('topbar-sp');

function desenharSeloSp() {
  const texto = document.getElementById('topbar-sp-texto');
  seloSp.hidden = !sp.estado;
  seloSp.dataset.estado = sp.estado || '';
  seloSp.disabled = sp.estado === 'lendo';
  texto.textContent = {
    lendo: 'Lendo o SharePoint…',
    'sem-pasta': 'SharePoint: escolha a pasta',
    erro: 'SharePoint indisponível',
  }[sp.estado] || `SharePoint · ${sp.hora}`;
}

// porAviso: o observador da pasta avisou que algo mudou (le mesmo dentro
// do intervalo minimo, sem o aviso "Nada novo"). Com a janela minimizada
// ou lendo, fica pendente e le quando der.
async function sincronizarSharePoint({ forcar = false, porAviso = false } = {}) {
  if (appView.hidden) return null;
  if (sp.lendo || (janelaEscondida() && !forcar)) {
    if (porAviso || janelaEscondida()) sp.pendente = true;
    return null;
  }
  if (!forcar && !porAviso && Date.now() - sp.ultima < SP_INTERVALO_MINIMO) return null;
  sp.pendente = false;
  sp.lendo = true;
  // So mostra "lendo" se demorar: o normal e levar milissegundos.
  const mostrarLendo = setTimeout(() => { sp.estado = 'lendo'; desenharSeloSp(); }, forcar ? 0 : 500);
  const antes = sp.estado === 'lendo' ? null : sp.estado;
  let resposta;
  try {
    resposta = await pywebview.api.sincronizar_sharepoint();
  } catch (err) {
    resposta = { erro: String(err), atualizados: [] };
  }
  clearTimeout(mostrarLendo);
  sp.lendo = false;
  sp.ultima = Date.now();
  if (Boolean(resposta.observando) !== sp.observando) {
    sp.observando = Boolean(resposta.observando);
    agendarLeitura();
  }
  if (sp.pendente) setTimeout(() => sincronizarSharePoint({ porAviso: true }), 0);
  if (resposta.sem_pasta) sp.estado = 'sem-pasta';
  else if (resposta.erro) sp.estado = 'erro';
  else if (resposta.ocupado) sp.estado = antes || 'ok'; // extraindo: le na proxima
  else {
    sp.estado = 'ok';
    sp.hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  if (sp.estado === 'ok' && !sp.hora) {
    sp.hora = new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
  desenharSeloSp();

  const novos = resposta.atualizados || [];
  const lancados = resposta.lancamentos || [];
  if (novos.length) {
    const lista = novos.map((n) => `${n.operacao_rotulo} · ${n.tipo_rotulo}`);
    avisar(novos.length === 1 ? 'Dado novo da pasta do SharePoint' : `${novos.length} dados novos da pasta do SharePoint`,
      'ok', lista.slice(0, 4).join(', ') + (lista.length > 4 ? ` e mais ${lista.length - 4}` : ''));
  }
  if (lancados.length) {
    const lista = lancados.map((l) => l.operacao_rotulo);
    avisar('Lançamentos de outra pessoa', 'ok',
      `Headcount e Coverage de ${lista.slice(0, 4).join(', ')}${lista.length > 4 ? ` e mais ${lista.length - 4}` : ''}`);
  }
  if (novos.length || lancados.length) {
    await recarregarAbaAberta();
  } else if (forcar && sp.estado === 'ok' && !resposta.ocupado) {
    avisar('Nada novo no SharePoint', 'info', 'Os dados da pasta já estão na tela.');
  } else if (forcar && sp.estado === 'sem-pasta') {
    avisar('Escolha a pasta do SharePoint', 'erro', 'Configurações › Pasta do SharePoint.');
  }
  return resposta;
}

async function recarregarAbaAberta() {
  // Quem esta digitando num campo nao perde o que digitou: a tela so
  // recarrega quando sai do campo.
  await esperarSairDoCampo();
  const aba = paginaAberta();
  const antes = valoresNaTela();
  if (aba === 'home') await loadHome();
  else if (aba === 'gestor') await abaGestor.carregar();
  else if (aba === 'turno') await abaTurno.carregar();
  else if (aba === 'coverage') await carregarCoverage();
  else if (aba === 'indiretas') await carregarIndiretas();
  else if (aba === 'headcount') await carregarHeadcount();
  destacarNovos(antes);
}

function campoEmEdicao() {
  const ativo = document.activeElement;
  return ativo && ativo.matches('input, select, textarea') && ativo.closest('.page:not([hidden])') ? ativo : null;
}

async function esperarSairDoCampo() {
  while (campoEmEdicao()) {
    // O valor digitado e gravado no "change", que vem junto com a saida
    // do campo: espera um pouco para a gravacao chegar antes.
    await new Promise((resolver) => document.addEventListener('focusout', () => setTimeout(resolver, 400), { once: true }));
  }
}

// Os valores das tabelas de indicadores, por tabela, linha e coluna
// (pelo titulo, nao pela posicao: uma semana nova empurra as outras).
function valoresNaTela() {
  const valores = new Map();
  document.querySelectorAll('.page:not([hidden]) td.indicator-cell').forEach((td) => {
    const chave = chaveDaCelula(td);
    if (chave) valores.set(chave, td.textContent.trim());
  });
  return valores;
}

function chaveDaCelula(td) {
  const tabela = td.closest('table');
  const titulo = tabela?.tHead?.rows[0]?.cells[td.cellIndex]?.querySelector('.col-title')?.textContent;
  const linha = td.closest('tr')?.querySelector('.indicator-label')?.textContent;
  if (!titulo || !linha) return null;
  const dono = td.closest('[data-grupo]')?.dataset.grupo || tabela.id || '';
  return `${dono}|${linha}|${titulo}`;
}

// Depois de chegar dado novo da pasta do SharePoint, o que mudou pisca
// em amarelo por um instante.
function destacarNovos(antes) {
  if (SEM_ANIMACAO || !antes.size) return;
  document.querySelectorAll('.page:not([hidden]) td.indicator-cell').forEach((td) => {
    const chave = chaveDaCelula(td);
    if (!chave || antes.get(chave) === td.textContent.trim()) return;
    const alvo = td.querySelector('.indicator-value') || td;
    alvo.classList.remove('valor-novo');
    void alvo.offsetWidth; // reinicia a animacao
    alvo.classList.add('valor-novo');
    setTimeout(() => alvo.classList.remove('valor-novo'), 1800);
  });
}

function iniciarLeituraDoSharePoint() {
  sincronizarSharePoint();
  if (!sp.relogio) agendarLeitura();
}

// A leitura periodica: a cada minuto, ou a cada 5 com o observador ligado.
function agendarLeitura() {
  clearInterval(sp.relogio);
  sp.relogio = setInterval(() => sincronizarSharePoint(),
    sp.observando ? SP_INTERVALO_OBSERVANDO : SP_INTERVALO);
}

// O Python avisa quando algo muda na pasta (observador_de_pasta.py).
window.pastaMudou = () => sincronizarSharePoint({ porAviso: true });
document.addEventListener('janelavoltou', () => {
  if (sp.pendente || Date.now() - sp.ultima > SP_INTERVALO) sincronizarSharePoint({ porAviso: true });
});

seloSp.addEventListener('click', () => {
  if (sp.estado === 'sem-pasta') { showPage('settings'); return; }
  sincronizarSharePoint({ forcar: true });
});

// "No SharePoint: 13/10/2026 15:22 · Week" ao lado da ultima extracao,
// com o mais novo de cada tipo no title.
async function mostrarSharePoint(id, operacao, tipos) {
  const alvo = document.getElementById(id);
  if (!alvo || !operacao) return;
  const pedido = String(++sp.pedidos);
  alvo.dataset.pedido = pedido;
  let info;
  try {
    info = await pywebview.api.get_sharepoint_info(operacao);
  } catch (err) {
    return;
  }
  if (alvo.dataset.pedido !== pedido) return; // trocou o filtro no meio
  const todas = operacao === 'todas';
  const achados = tipos.map((t) => (info.tipos || {})[t]).filter(Boolean)
    .sort((a, b) => (a.quando < b.quando ? 1 : -1));
  let texto;
  if (!info.pasta) texto = 'Pasta não configurada';
  else if (!achados.length) texto = todas ? 'Nenhum arquivo na pasta' : 'Nenhum arquivo desta operação';
  else {
    const novo = achados[0];
    // "Gestor · Week" vira so "Week": a aba ja diz de quem e.
    const tipo = tipos.length > 1 ? ` · ${novo.rotulo.replace(/^(Gestor|Turno) · /, '')}` : '';
    texto = `${novo.texto}${todas ? ` · ${novo.operacao}` : ''}${tipo}`;
  }
  alvo.dataset.estado = achados.length ? 'ok' : 'vazio';
  alvo.title = achados.length
    ? `Relatório mais novo na pasta do SharePoint, por tipo:\n${achados.map((a) => `${a.rotulo}${todas ? ` (${a.operacao})` : ''}: ${a.texto}${a.periodo ? ` · período ${a.periodo}` : ''}`).join('\n')}`
    : 'Nenhum relatório na pasta do SharePoint ainda.';
  const campoTexto = alvo.querySelector('.sp-texto');
  if (campoTexto) campoTexto.textContent = texto;
  else alvo.textContent = `No SharePoint: ${texto}`;
}
