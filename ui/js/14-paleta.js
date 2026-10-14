// ---------------------------------------------------------------
// Procurar (Ctrl+K)
// ---------------------------------------------------------------
// Uma caixa so para ir a qualquer aba, operacao + mes ou acao, sem passar
// pelo menu: "hughes setembro" abre a Inicio da Hughes em setembro;
// "hughes coverage", o Coverage da Hughes; "tema", a troca de tema.
// Sem acento e sem diferenca de maiuscula; cada palavra digitada tem de
// aparecer no item.

const paleta = {
  el: document.getElementById('paleta'),
  campo: document.getElementById('paleta-campo'),
  lista: document.getElementById('paleta-lista'),
  itens: [],
  escolhido: 0,
  focoAntes: null,
};

const MESES_DA_PALETA = ['janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho', 'julho', 'agosto',
  'setembro', 'outubro', 'novembro', 'dezembro'];
const NOMES_DOS_MESES = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto',
  'Setembro', 'Outubro', 'Novembro', 'Dezembro'];

// Abas com filtro de operacao e mes: os seletores de cada uma.
const FILTROS_DA_ABA = {
  home: { operacao: 'home-operation', mes: 'home-mes' },
  gestor: { operacao: 'rg-operacao', mes: 'rg-mes' },
  turno: { operacao: 'rt-operacao', mes: 'rt-mes' },
  coverage: { operacao: 'cv-operacao', mes: 'cv-mes' },
  headcount: { operacao: 'hc-operacao', mes: 'hc-mes' },
  indiretas: { operacao: 'ind-operacao', mes: 'ind-mes' },
};

const ICONES_DA_PALETA = {
  acao: '<polyline points="9 18 15 12 9 6"></polyline>',
  operacao: '<path d="M3 21h18"></path><path d="M5 21V7l7-4 7 4v14"></path><path d="M9 21v-6h6v6"></path>',
  imagem: '<rect x="3" y="3" width="18" height="18" rx="2"></rect><circle cx="9" cy="9" r="2"></circle><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"></path>',
  tema: '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>',
  tela: '<rect x="2" y="3" width="20" height="14" rx="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line>',
  ajuda: '<circle cx="12" cy="12" r="9"></circle><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line>',
  nuvem: '<path d="M17.5 19a4.5 4.5 0 0 0 .5-8.97A6 6 0 0 0 6.34 8.6 4 4 0 0 0 6.5 19Z"></path>',
};

// "set", "setem", "setembro" -> 9; "09/2026" e "2026-09" tambem.
function mesDaPalavra(palavra) {
  if (palavra.length >= 3) {
    const i = MESES_DA_PALETA.findIndex((nome) => nome.startsWith(palavra));
    if (i >= 0) return { numero: i + 1 };
  }
  const casou = /^(\d{1,2})\/(\d{4})$/.exec(palavra) || /^(\d{4})-(\d{1,2})$/.exec(palavra);
  if (casou) {
    const [a, b] = [Number(casou[1]), Number(casou[2])];
    const [numero, ano] = a > 12 ? [b, a] : [a, b];
    if (numero >= 1 && numero <= 12) return { numero, ano };
  }
  return null;
}

// Sem ano, o mes mais recente que ja passou (ou o atual): em outubro,
// "setembro" e deste ano e "dezembro", do ano passado.
function mesEscolhido(numero, ano) {
  const hoje = new Date();
  const anoFinal = ano || (numero <= hoje.getMonth() + 1 ? hoje.getFullYear() : hoje.getFullYear() - 1);
  return {
    id: `${anoFinal}-${String(numero).padStart(2, '0')}`,
    rotulo: `${NOMES_DOS_MESES[numero - 1]}/${anoFinal}`,
  };
}

function operacoesDoApp() {
  return [...homeOperationSelect.options].map((o) => ({ key: o.value, label: o.textContent }));
}

// Nome inteiro ("jcb", "rede") ou comeco com 3 letras ou mais ("hug"):
// com 2 letras, "re" de "Resultado" viraria a operacao Rede.
function operacaoDaPalavra(palavra) {
  if (palavra.length < 2) return null;
  const ops = operacoesDoApp();
  const exata = ops.find((op) => semAcento(op.key) === palavra || semAcento(op.label) === palavra);
  if (exata || palavra.length < 3) return exata || null;
  return ops.find((op) => semAcento(op.label).split(/[\s/]+/).some((p) => p.startsWith(palavra)) || semAcento(op.key).startsWith(palavra))
    || null;
}

function abasDoMenu() {
  return [...document.querySelectorAll('.nav-item[data-page]')].map((botao) => ({
    pagina: botao.dataset.page,
    titulo: botao.querySelector('span')?.textContent.trim() || botao.dataset.page,
    icone: botao.querySelector('svg')?.innerHTML || ICONES_DA_PALETA.acao,
    atalho: botao.dataset.atalho ? `Ctrl ${botao.dataset.atalho}` : '',
  }));
}

function acoesDaPaleta() {
  const tema = preferencias.tema === 'claro' ? 'escuro' : 'claro';
  return [
    { titulo: 'Modo apresentação', detalhe: 'Só a tabela da Início, em tela cheia', palavras: 'tv reuniao tela cheia projetor', icone: ICONES_DA_PALETA.tela,
      fazer: async () => { if (paginaAberta() !== 'home') await showPage('home'); modoApresentacao(true); } },
    { titulo: 'Copiar a tabela como imagem', detalhe: 'Indicadores da Início, para colar no PowerPoint', palavras: 'png figura print foto exportar powerpoint ppt slide', icone: ICONES_DA_PALETA.imagem,
      fazer: async () => { if (paginaAberta() !== 'home') await showPage('home'); exportarImagemDaTabela('copiar'); } },
    { titulo: 'Salvar a tabela como PNG', detalhe: 'Arquivo de imagem na pasta Downloads', palavras: 'png imagem arquivo exportar downloads figura', icone: ICONES_DA_PALETA.imagem,
      fazer: async () => { if (paginaAberta() !== 'home') await showPage('home'); exportarImagemDaTabela('salvar'); } },
    { titulo: `Tema ${tema}`, detalhe: 'Ctrl+Shift+L', palavras: 'tema claro escuro cor aparencia dark light', icone: ICONES_DA_PALETA.tema, fazer: alternarTema },
    { titulo: preferencias.menu_recolhido ? 'Abrir o menu' : 'Recolher o menu', detalhe: 'Ctrl+B', palavras: 'menu lateral recolher abrir', icone: ICONES_DA_PALETA.acao, fazer: alternarMenu },
    { titulo: preferencias.densidade === 'compacta' ? 'Densidade confortável' : 'Densidade compacta', detalhe: 'Mais ou menos linhas na tela', palavras: 'densidade compacta confortavel espaco', icone: ICONES_DA_PALETA.acao,
      fazer: () => mudarPreferencia('densidade', preferencias.densidade === 'compacta' ? 'confortavel' : 'compacta') },
    { titulo: preferencias.animacoes === 'leves' ? 'Animações completas' : 'Modo leve', detalhe: 'Desliga o que só enfeita: notebook fraco, Citrix e projetor', palavras: 'animacoes leve lento rapido desempenho', icone: ICONES_DA_PALETA.acao,
      fazer: () => mudarPreferencia('animacoes', preferencias.animacoes === 'leves' ? 'completas' : 'leves') },
    { titulo: 'Extrair a operação desta tela', detalhe: 'Ctrl+E', palavras: 'extrair extracao relatorio summary baixar', icone: ICONES_DA_PALETA.acao,
      fazer: () => { const { operacao, tipo } = operacaoDaTela(); irParaExtracao(operacao, tipo); } },
    { titulo: 'Ler a pasta do SharePoint agora', detalhe: 'Traz o que outras pessoas extraíram', palavras: 'sharepoint pasta atualizar sincronizar ler', icone: ICONES_DA_PALETA.nuvem,
      fazer: () => sincronizarSharePoint({ forcar: true }) },
    { titulo: 'Atalhos de teclado', detalhe: 'Tecla ?', palavras: 'atalhos teclado teclas', icone: ICONES_DA_PALETA.ajuda, fazer: abrirAtalhos },
    { titulo: 'O que há de novo', detalhe: 'Novidades desta versão', palavras: 'novidades versao novo mudou', icone: ICONES_DA_PALETA.ajuda, fazer: abrirNovidades },
    { titulo: 'Fazer o tour', detalhe: 'Um minuto pela aba Início', palavras: 'tour ajuda tutorial como usar', icone: ICONES_DA_PALETA.ajuda, fazer: iniciarTour },
    { titulo: 'Gerar diagnóstico', detalhe: 'Para mandar a quem dá suporte', palavras: 'diagnostico suporte erro log', icone: ICONES_DA_PALETA.ajuda,
      fazer: async () => { await showPage('settings'); document.getElementById('diagnostico-btn').click(); } },
    { titulo: 'Fazer backup agora', detalhe: 'Cópia dos dados deste computador', palavras: 'backup copia seguranca restaurar', icone: ICONES_DA_PALETA.ajuda,
      fazer: async () => { await showPage('settings'); document.getElementById('backup-agora').click(); } },
  ];
}

// Abre a aba ja com a operacao e o mes. O mes muda primeiro: cada aba
// guarda o mes no proprio estado ao trocar o seletor, e a troca de
// operacao em seguida ja carrega com ele (o pedido anterior fica velho e
// e descartado).
async function abrirAbaCom(pagina, operacao, mes) {
  if (paginaAberta() !== pagina) await showPage(pagina);
  const ids = FILTROS_DA_ABA[pagina];
  if (!ids) return;
  const seletorMes = document.getElementById(ids.mes);
  const seletorOp = document.getElementById(ids.operacao);
  const mesDoCiclo = pagina === 'headcount' && hcEstado.visualizacao === 'mes';
  if (mes && !mesDoCiclo && seletorMes.value !== mes.id) {
    if (![...seletorMes.options].some((o) => o.value === mes.id)) seletorMes.add(new Option(mes.rotulo, mes.id));
    seletorMes.value = mes.id;
    seletorMes.dispatchEvent(new Event('change'));
  }
  if (operacao && seletorOp.value !== operacao && [...seletorOp.options].some((o) => o.value === operacao)) {
    seletorOp.value = operacao;
    seletorOp.dispatchEvent(new Event('change'));
  }
}

// A lista para o texto digitado: com operacao ou mes na busca, primeiro
// as abas ja filtradas; depois as abas e acoes que tem todas as palavras.
function montarItensDaPaleta(texto) {
  const palavras = semAcento(texto).split(/\s+/).filter(Boolean);
  let operacao = null;
  let mes = null;
  let ano = null;
  const resto = [];
  for (const palavra of palavras) {
    // "hugo boss": o "boss" ja faz parte da operacao escolhida.
    if (operacao && semAcento(`${operacao.label} ${operacao.key}`).split(/[\s/_]+/).some((p) => p.startsWith(palavra))) continue;
    const op = !operacao && operacaoDaPalavra(palavra);
    const m = !mes && mesDaPalavra(palavra);
    if (op) operacao = op;
    else if (m) mes = m;
    else if (/^20\d\d$/.test(palavra)) ano = Number(palavra);
    else resto.push(palavra);
  }
  if (mes && ano && !mes.ano) mes.ano = ano;
  const mesFinal = mes ? mesEscolhido(mes.numero, mes.ano) : null;

  const pontuar = (busca) => {
    let pontos = 0;
    for (const palavra of resto) {
      const i = busca.indexOf(palavra);
      if (i < 0) return -1;
      pontos += i === 0 || busca[i - 1] === ' ' ? 3 : 1;
    }
    return pontos;
  };

  const itens = [];
  const abas = abasDoMenu();
  if (operacao || mesFinal) {
    const comFiltro = [...abas.filter((a) => FILTROS_DA_ABA[a.pagina])];
    if (operacao) comFiltro.push({ pagina: 'extract', titulo: 'Extrair Dados', icone: abas.find((a) => a.pagina === 'extract')?.icone });
    comFiltro.forEach((aba, ordem) => {
      const partes = [aba.titulo];
      if (operacao) partes.push(operacao.label);
      if (mesFinal && aba.pagina !== 'extract') partes.push(mesFinal.rotulo);
      const pontos = pontuar(semAcento(`${aba.titulo} ${aba.pagina}`));
      if (pontos < 0) return;
      itens.push({
        grupo: 'Ir para', titulo: partes.join(' · '), icone: aba.icone || ICONES_DA_PALETA.operacao,
        detalhe: aba.pagina === 'extract' ? 'Extrair Dados já com a operação' : 'Abre a aba já filtrada',
        pontos: pontos * 10 + (comFiltro.length - ordem),
        fazer: () => (aba.pagina === 'extract' ? irParaExtracao(operacao.key, 'week') : abrirAbaCom(aba.pagina, operacao?.key, mesFinal)),
      });
    });
  }

  if (!operacao && !mesFinal) {
    abas.forEach((aba, ordem) => {
      const pontos = pontuar(semAcento(`${aba.titulo} ${aba.pagina} aba tela`));
      if (pontos < 0) return;
      itens.push({ grupo: 'Abas', titulo: aba.titulo, icone: aba.icone, atalho: aba.atalho, pontos: pontos * 10 + (abas.length - ordem) / 100,
        fazer: () => showPage(aba.pagina) });
    });
    acoesDaPaleta().forEach((acao, ordem) => {
      const pontos = pontuar(semAcento(`${acao.titulo} ${acao.detalhe} ${acao.palavras}`));
      if (pontos < 0 || (!resto.length && ordem > 7)) return;
      itens.push({ ...acao, grupo: 'Ações', pontos: pontos * 10 - ordem / 100 - (resto.length ? 0 : 1) });
    });
  }

  // Com palavras digitadas, o melhor primeiro; sem nada, a ordem do menu.
  if (resto.length) itens.sort((a, b) => b.pontos - a.pontos);
  return itens.slice(0, 14);
}

function marcarPalavras(elemento, texto, palavras) {
  // O que bate com a busca fica em destaque (sem innerHTML: o texto e
  // montado no DOM).
  const normal = semAcento(texto);
  const marcas = new Array(texto.length).fill(false);
  for (const palavra of palavras) {
    let i = normal.indexOf(palavra);
    while (palavra && i >= 0) {
      for (let j = i; j < i + palavra.length; j += 1) marcas[j] = true;
      i = normal.indexOf(palavra, i + palavra.length);
    }
  }
  let i = 0;
  while (i < texto.length) {
    let j = i;
    while (j < texto.length && marcas[j] === marcas[i]) j += 1;
    const pedaco = texto.slice(i, j);
    elemento.append(marcas[i] ? Object.assign(document.createElement('mark'), { textContent: pedaco }) : pedaco);
    i = j;
  }
}

function desenharPaleta() {
  const texto = paleta.campo.value;
  paleta.itens = montarItensDaPaleta(texto);
  paleta.escolhido = Math.min(paleta.escolhido, Math.max(0, paleta.itens.length - 1));
  const palavras = semAcento(texto).split(/\s+/).filter((p) => p.length >= 2);
  paleta.lista.innerHTML = '';
  if (!paleta.itens.length) {
    const vazio = document.createElement('li');
    vazio.className = 'paleta-vazio';
    vazio.textContent = `Nada encontrado para "${texto.trim()}". Tente o nome de uma aba, operação ou mês.`;
    paleta.lista.appendChild(vazio);
    paleta.campo.removeAttribute('aria-activedescendant');
    return;
  }
  let grupoAtual = null;
  paleta.itens.forEach((item, i) => {
    if (!palavras.length && item.grupo !== grupoAtual) {
      grupoAtual = item.grupo;
      const titulo = document.createElement('li');
      titulo.className = 'paleta-grupo';
      titulo.setAttribute('role', 'presentation');
      titulo.textContent = item.grupo;
      paleta.lista.appendChild(titulo);
    }
    const li = document.createElement('li');
    li.className = 'paleta-item';
    li.id = `paleta-item-${i}`;
    li.setAttribute('role', 'option');
    li.setAttribute('aria-selected', String(i === paleta.escolhido));
    const icone = document.createElement('span');
    icone.className = 'paleta-icone';
    icone.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true">${item.icone || ICONES_DA_PALETA.acao}</svg>`;
    const corpo = document.createElement('span');
    corpo.className = 'paleta-texto';
    const titulo = document.createElement('strong');
    marcarPalavras(titulo, item.titulo, palavras);
    corpo.appendChild(titulo);
    if (item.detalhe) {
      const detalhe = document.createElement('span');
      detalhe.textContent = item.detalhe;
      corpo.appendChild(detalhe);
    }
    li.append(icone, corpo);
    if (item.atalho) {
      const kbd = document.createElement('kbd');
      kbd.textContent = item.atalho;
      li.appendChild(kbd);
    }
    li.addEventListener('mousemove', () => { if (paleta.escolhido !== i) escolherNaPaleta(i); });
    li.addEventListener('click', () => executarDaPaleta(i));
    paleta.lista.appendChild(li);
  });
  paleta.campo.setAttribute('aria-activedescendant', `paleta-item-${paleta.escolhido}`);
}

function escolherNaPaleta(indice) {
  const total = paleta.itens.length;
  if (!total) return;
  paleta.escolhido = (indice + total) % total;
  paleta.lista.querySelectorAll('.paleta-item').forEach((li, i) => li.setAttribute('aria-selected', String(i === paleta.escolhido)));
  const atual = document.getElementById(`paleta-item-${paleta.escolhido}`);
  paleta.campo.setAttribute('aria-activedescendant', atual.id);
  atual.scrollIntoView({ block: 'nearest' });
}

async function executarDaPaleta(indice) {
  const item = paleta.itens[indice];
  if (!item) return;
  fecharPaleta(false);
  try {
    await item.fazer();
  } catch (erro) {
    registrarErro('procurar', erro);
  }
}

function abrirPaleta() {
  if (!paleta.el.hidden || appView.hidden || emApresentacao) return;
  paleta.focoAntes = document.activeElement;
  paleta.campo.value = '';
  paleta.escolhido = 0;
  desenharPaleta();
  paleta.el.hidden = false;
  paleta.campo.focus();
}

function fecharPaleta(devolverFoco = true) {
  if (paleta.el.hidden) return;
  paleta.el.hidden = true;
  if (devolverFoco && paleta.focoAntes && paleta.focoAntes.focus && paleta.focoAntes.isConnected) paleta.focoAntes.focus();
}

paleta.campo.addEventListener('input', () => {
  paleta.escolhido = 0;
  desenharPaleta();
});
paleta.el.addEventListener('mousedown', (evento) => { if (evento.target === paleta.el) fecharPaleta(); });
document.getElementById('paleta-abrir').addEventListener('click', abrirPaleta);

// Em captura na janela, antes dos atalhos do app: com a caixa aberta, so
// ela responde ao teclado (as letras seguem para o campo).
window.addEventListener('keydown', (evento) => {
  const ctrlK = (evento.ctrlKey || evento.metaKey) && !evento.altKey && !evento.shiftKey && evento.key.toLowerCase() === 'k';
  if (paleta.el.hidden) {
    const outraJanela = !janelaAtalhos.hidden || !document.getElementById('dialogo').hidden;
    if (ctrlK && !appView.hidden && !outraJanela) {
      evento.preventDefault();
      evento.stopImmediatePropagation();
      abrirPaleta();
    }
    return;
  }
  evento.stopImmediatePropagation();
  if (ctrlK || evento.key === 'Escape') {
    evento.preventDefault();
    fecharPaleta();
  } else if (evento.key === 'ArrowDown' || evento.key === 'ArrowUp') {
    evento.preventDefault();
    escolherNaPaleta(paleta.escolhido + (evento.key === 'ArrowDown' ? 1 : -1));
  } else if (evento.key === 'Enter') {
    evento.preventDefault();
    executarDaPaleta(paleta.escolhido);
  } else if (evento.key === 'Tab') {
    evento.preventDefault();
    paleta.campo.focus();
  }
}, true);
