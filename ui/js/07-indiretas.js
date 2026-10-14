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
  const pedido = novoPedido('indiretas');
  const tela = await comAtualizando(indTela ? document.getElementById('ind-conteudo') : null,
    () => pywebview.api.get_indiretas(indEstado.operacao, indEstado.mes, indEstado.semana_id));
  if (!pedidoVale('indiretas', pedido)) return;
  indTela = tela;
  indEstado.operacao = indTela.operacao;
  indEstado.mes = indTela.mes;
  indEstado.semana_id = indTela.semana_id;
  desenharIndiretas();
  mostrarSharePoint('ind-sp', indEstado.operacao, ['indiretas']);
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
  const lower = semAcento(texto);
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
  if (outraExtracaoRodando()) return;
  if (!(await ensureFolderConfigured())) {
    showStatus(indStatus, 'É necessário selecionar a pasta do SharePoint antes de extrair.', 'error');
    return;
  }
  extracaoComecou('indiretas', `${indExtOperacao.selectedOptions[0]?.text || ''} · Horas Indiretas`);
  const progresso = document.getElementById('ind-progresso');
  progresso.hidden = false;
  document.getElementById('ind-progresso-preenchido').style.width = '0%';
  progressoIndiretas('Iniciando a extração...');
  indExtraindo = true;
  await comCarregando(indExtrairBtn, async () => {
    try {
      const resultado = await pywebview.api.run_extraction(
        indExtOperacao.value, { from_date: indExtDe.value, to_date: indExtAte.value }, 'Job Code', 'indiretas');
      conferirSenhaRecusada(resultado);
      const desfecho = desfechoDe(resultado);
      showStatus(indStatus, resultado.indicators_message || resultado.message, desfecho.classe);
      extracaoTerminou(desfecho.classe, desfecho.rotulo);
      if (resultado.success) {
        document.getElementById('ind-progresso-preenchido').style.width = '100%';
        indEstado.operacao = indExtOperacao.value;
        indEstado.semana_id = null;
      }
    } catch (erro) {
      registrarErro('extração de horas indiretas', erro);
      showStatus(indStatus, 'Não deu para extrair. Veja o log em Configurações > Gerar diagnóstico.', 'error');
      extracaoTerminou('error', 'Falha');
    } finally {
      indExtraindo = false;
      progresso.hidden = true;
    }
  });
  await carregarIndiretas();
});
