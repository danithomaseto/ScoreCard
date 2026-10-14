async function showPage(pageName) {
  trocarComTransicao(pageName);
  // O que outras pessoas extrairam chega pela pasta do SharePoint; se
  // vier algo novo para esta aba, ela e redesenhada (sem esperar aqui).
  if (ABAS_COM_DADOS.has(pageName)) sincronizarSharePoint();
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
    carregarSaude();
    carregarBackups();
  }
}

async function loadHome() {
  const tabela = await loadIndicators();
  if (!tabela) return null; // sem operacao, ou ja chegou um pedido mais novo
  await loadLastRun(tabela.ultima_extracao);
  mostrarSharePoint('home-sp', homeOperationSelect.value, ['week', 'month', 'peak']);
  return tabela;
}

async function loadLastRun(ultimaDosDados) {
  const history = await pywebview.api.get_report_history();
  // A ultima extracao da operacao escolhida no filtro (a de outra
  // operacao nao diz nada sobre estes numeros).
  const operacao = homeOperationSelect.selectedOptions[0]?.text;
  const last = history.find((h) => h.operation === operacao);
  // Os dados podem ter vindo da pasta do SharePoint, extraidos por outra
  // pessoa: vale a mais nova entre o historico desta maquina e os dados.
  const dosDados = ultimaDosDados ? new Date(ultimaDosDados) : null;
  if (dosDados && (!last || dosDados > new Date(last.timestamp))) {
    homeLastRunEl.textContent = `${operacao} · ${dosDados.toLocaleString('pt-BR')}`;
    return;
  }
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
  if (!operacao) return null;

  const pedido = novoPedido('inicio');
  const antes = valoresNaTela();
  const tabela = await comEsqueleto(
    indicatorsBody, 6,
    () => pywebview.api.get_indicator_table(operacao, homeMes.value || null),
    () => { indicatorsEmpty.hidden = true; indicatorsWrap.hidden = false; },
  );
  if (!pedidoVale('inicio', pedido)) return null;
  preencherSelect(homeMes, tabela.meses || [], tabela.mes);
  marcarOperacoesComDados(tabela.mes);
  const temDados = tabela.colunas.length > 0;

  indicatorsEmpty.hidden = temDados;
  indicatorsWrap.hidden = !temDados;
  indicatorsLegend.hidden = !temDados;
  if (!temDados) {
    document.getElementById('distribuicao-card').hidden = true;
    const nomeDoMes = homeMes.selectedOptions[0]?.text || 'neste mês';
    document.getElementById('indicators-empty-titulo').textContent =
      `Nenhuma extração de ${homeOperationSelect.selectedOptions[0]?.text || 'esta operação'} em ${nomeDoMes} ainda`;
    botaoMesAnterior(document.getElementById('indicators-anterior'), tabela.meses, tabela.mes);
    return tabela;
  }

  desenharDistribuicao(tabela.distribuicao);
  const primeiraVez = !indicatorsBody.querySelector('tr:not(.linha-esqueleto)');
  desenharCabecalho(tabela);
  desenharLinhas(tabela);
  if (primeiraVez) entrarEmSequencia(indicatorsBody);
  else contarValoresQueMudaram(antes);
  // Abre mostrando o fim da tabela: o mes e o pico sao o que se olha
  // primeiro, e numa janela estreita eles ficariam escondidos a direita.
  indicatorsWrap.scrollLeft = indicatorsWrap.scrollWidth;
  return tabela;
}

// Na lista de operacoes, um ponto verde nas que tem dados no mes da tela
// (o desenho fica no CSS; num WebView2 sem o seletor novo, nao aparece).
async function marcarOperacoesComDados(mes) {
  let lista;
  try {
    lista = await pywebview.api.operacoes_com_dados(mes);
  } catch (erro) {
    return;
  }
  if (!Array.isArray(lista) || homeMes.value !== mes) return;
  const rotulo = homeMes.selectedOptions[0]?.text || mes;
  for (const opcao of homeOperationSelect.options) {
    const tem = lista.includes(opcao.value);
    opcao.dataset.dados = tem ? 'sim' : 'nao';
    opcao.title = tem ? `Tem dados em ${rotulo}` : `Sem extração em ${rotulo}`;
  }
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
    const grupo = elementoSvg('g', { class: 'distribuicao-faixa', tabindex: '0' });
    marcarDica(grupo, `Var ${faixa.rotulo}`,
      `${plural(faixa.pessoas, 'pessoa', 'pessoas')} · ${percentualDe(faixa.pessoas, dist.total)} das ${num(dist.total)}`,
      `meta ${num(faixa.meta)}`);
    // Area de toque maior que a barra, para a dica aparecer facil.
    grupo.appendChild(elementoSvg('rect', { x: centro(i) - passo / 2, y: topo - 20, width: passo, height: base - topo + 20, fill: 'transparent' }));
    if (altura > 0) {
      grupo.appendChild(elementoSvg('path', {
        style: `--i: ${i}`,
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
  // Com o simbolo da faixa (dentro, abaixo ou acima da tolerancia), como
  // nos indicadores: a cor nunca e a unica pista.
  dist.faixas.forEach((faixa, i) => {
    const simbolo = faixa.chave === 'dentro' ? '\u2713' : (faixa.chave.startsWith('abaixo') ? '\u25BC' : '\u25B2');
    svg.appendChild(elementoSvg('text', { x: centro(i), y: y(faixa.pessoas) - 8, class: 'distribuicao-valor' },
      `${simbolo} ${num(faixa.pessoas)}`));
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
    const formula = linha.celulas.find((c) => c.dica)?.dica.formula;
    if (formula) marcarDica(th, linha.rotulo, formula, '');
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
        if (celula.dica) {
          marcarDica(td, `${linha.rotulo} · ${coluna.titulo}`, celula.dica.formula, celula.dica.conta);
        }
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

homeOperationSelect.addEventListener('change', loadHome);
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
document.getElementById('indicators-anterior').addEventListener('click', (evento) => {
  homeMes.value = evento.currentTarget.dataset.mes;
  loadIndicators();
});

// Tela vazia: o botao "Ver <mes>" leva ao mes anterior mais recente que
// tem dados (a lista de meses so tem meses com extracao, mais o atual).
function botaoMesAnterior(botao, meses, mesAtual) {
  const anterior = (meses || []).find((m) => m.id < mesAtual);
  botao.hidden = !anterior;
  if (anterior) {
    botao.textContent = `Ver ${anterior.rotulo}`;
    botao.dataset.mes = anterior.id;
  }
}

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
  if (!ligar) {
    ligarAutomatico(false);
    esconderCapa(true);
  }
  try {
    await pywebview.api.tela_cheia(ligar);
  } catch (erro) {
    registrarErro('tela cheia', erro);
  }
  indicatorsWrap.scrollLeft = indicatorsWrap.scrollWidth;
  if (!ligar) document.getElementById('home-apresentar').focus();
}

// Troca a operacao com a capa na frente. Com as setas passa por todas;
// no automatico, so pelas que tem dados no mes (a lista vem pronta do
// Python). Antes o automatico carregava a tabela de cada operacao ate
// achar uma com dados: com uma so operacao no mes ele dava a volta e
// voltava nela, e uma leitura do SharePoint no meio fazia pular a
// seguinte. Uma chamada que nao volta tambem nao trava mais: depois de
// LIMITE_DA_TROCA a troca segue e o relogio volta a correr.
let trocandoNaApresentacao = false;
const LIMITE_DA_TROCA = 20000;

function comLimite(promessa, ms) {
  let relogio;
  const limite = new Promise((resolver) => { relogio = setTimeout(() => resolver(null), ms); });
  return Promise.race([promessa, limite]).finally(() => clearTimeout(relogio));
}

// A proxima operacao no sentido do passo (dando a volta). No automatico,
// so entre as que tem dados no mes; null se nenhuma tem.
async function proximaOperacaoDaApresentacao(passo, mes) {
  const opcoes = [...homeOperationSelect.options].map((o) => o.value);
  const total = opcoes.length;
  const atual = Math.max(0, homeOperationSelect.selectedIndex);
  const seguinte = (i) => opcoes[(((atual + passo * i) % total) + total) % total];
  if (!apresentacaoAuto.ligado) return seguinte(1);
  let comDados = null;
  try {
    comDados = await comLimite(pywebview.api.operacoes_com_dados(mes), LIMITE_DA_TROCA);
  } catch (erro) {
    registrarErro('apresentação automática', erro);
  }
  if (!Array.isArray(comDados)) return seguinte(1); // sem a lista, segue a ordem
  apresentacaoAuto.comDados = comDados;
  for (let i = 1; i <= total; i += 1) {
    if (comDados.includes(seguinte(i))) return seguinte(i);
  }
  return null;
}

// Aviso de "so uma operacao" ou "nenhuma", uma vez por mes da apresentacao.
function avisarRodizio(mes, mesRotulo) {
  const lista = apresentacaoAuto.comDados || [];
  if (lista.length > 1 || apresentacaoAuto.avisado === mes) return;
  apresentacaoAuto.avisado = mes;
  if (!lista.length) {
    avisar(`Nenhuma operação tem dados em ${mesRotulo}`, 'info',
      'O automático fica parado aqui e confere de novo a cada intervalo. Troque o mês no filtro, se quiser.');
  } else {
    const nome = [...homeOperationSelect.options].find((o) => o.value === lista[0])?.text || lista[0];
    avisar(`Só ${nome} tem dados em ${mesRotulo}`, 'info',
      'O automático fica nela e confere de novo a cada intervalo: quando outra operação tiver extração, ela entra no rodízio.');
  }
}

async function trocarOperacaoNaApresentacao(passo) {
  if (!homeOperationSelect.options.length) return;
  if (trocandoNaApresentacao) {
    agendarProximaOperacao();
    return;
  }
  trocandoNaApresentacao = true;
  clearTimeout(apresentacaoAuto.timer);
  const inicio = performance.now();
  // O mes da apresentacao fica o mesmo para todas as operacoes (sem isto,
  // uma operacao sem dados nele voltaria o seletor para o mes atual).
  const mes = homeMes.value;
  const mesRotulo = homeMes.selectedOptions[0]?.text || '';
  const manterMes = () => {
    if (mes && ![...homeMes.options].some((o) => o.value === mes)) homeMes.add(new Option(mesRotulo, mes));
    homeMes.value = mes;
  };
  try {
    const destino = await proximaOperacaoDaApresentacao(passo, mes);
    if (apresentacaoAuto.ligado) avisarRodizio(mes, mesRotulo);
    if (!destino || destino === homeOperationSelect.value) {
      // Ninguem mais no rodizio: so atualiza os numeros da que esta na tela.
      manterMes();
      await comLimite(loadHome(), LIMITE_DA_TROCA);
      return;
    }
    homeOperationSelect.value = destino;
    mostrarCapa(homeOperationSelect.selectedOptions[0]?.text || '', mesRotulo);
    manterMes();
    await comLimite(loadHome(), LIMITE_DA_TROCA);
    preencherResumoDaCapa();
    // A capa fica pelo menos um instante, mesmo com a resposta rapida.
    const falta = Math.max(0, (SEM_ANIMACAO ? 400 : 1500) - (performance.now() - inicio));
    setTimeout(() => esconderCapa(), falta);
  } catch (erro) {
    registrarErro('apresentação', erro);
    esconderCapa(true);
  } finally {
    trocandoNaApresentacao = false;
    agendarProximaOperacao();
  }
}

// ---- Automatico: troca sozinho a cada intervalo ----
const apresentacaoAuto = { ligado: false, intervalo: 30000, timer: null, comDados: null, avisado: null };
const capa = document.getElementById('apresentacao-capa');

function ligarAutomatico(ligar) {
  apresentacaoAuto.ligado = ligar;
  const botao = document.getElementById('apresentacao-auto');
  botao.setAttribute('aria-pressed', String(ligar));
  document.getElementById('apresentacao-auto-texto').textContent = ligar ? 'Pausar' : 'Automático';
  agendarProximaOperacao();
  if (ligar) conferirRodizio();
}

// Ao ligar, ja diz se o rodizio vai ficar numa operacao so (sem esperar
// o primeiro intervalo passar).
async function conferirRodizio() {
  const mes = homeMes.value;
  try {
    const lista = await comLimite(pywebview.api.operacoes_com_dados(mes), LIMITE_DA_TROCA);
    if (Array.isArray(lista) && apresentacaoAuto.ligado && homeMes.value === mes) {
      apresentacaoAuto.comDados = lista;
      avisarRodizio(mes, homeMes.selectedOptions[0]?.text || '');
    }
  } catch (erro) {
    registrarErro('apresentação automática', erro);
  }
}

function agendarProximaOperacao() {
  clearTimeout(apresentacaoAuto.timer);
  const tempo = document.getElementById('apresentacao-tempo');
  if (!apresentacaoAuto.ligado || !emApresentacao) {
    tempo.classList.remove('correndo');
    return;
  }
  tempo.style.animationDuration = `${apresentacaoAuto.intervalo}ms`;
  reiniciarAnimacao(tempo, 'correndo');
  apresentacaoAuto.timer = setTimeout(() => trocarOperacaoNaApresentacao(1), apresentacaoAuto.intervalo);
}

function mostrarCapa(operacao, mesRotulo) {
  document.getElementById('capa-operacao').textContent = operacao;
  document.getElementById('capa-mes').textContent = mesRotulo || homeMes.selectedOptions[0]?.text || '';
  document.getElementById('capa-resumo').textContent = '';
  if (capa.hidden || capa.classList.contains('saindo')) {
    capa.hidden = false;
    capa.classList.remove('saindo');
    reiniciarAnimacao(capa, 'entrando');
  }
}

// "4 de 6 indicadores na meta no mes": a coluna do mes, como esta na tela.
function preencherResumoDaCapa() {
  const resumo = document.getElementById('capa-resumo');
  if (indicatorsWrap.hidden) {
    resumo.textContent = 'Sem extração neste mês';
    return;
  }
  const celulas = [...indicatorsBody.querySelectorAll('td.month-col .indicator-value')];
  const comNumero = celulas.filter((c) => c.textContent.trim());
  if (!comNumero.length) {
    resumo.textContent = '';
    return;
  }
  const naMeta = comNumero.filter((c) => c.classList.contains('verde')).length;
  resumo.textContent = `${naMeta} de ${comNumero.length} indicadores na meta no mês`;
}

function esconderCapa(agora = false) {
  if (capa.hidden) return;
  if (agora || SEM_ANIMACAO) {
    capa.hidden = true;
    return;
  }
  capa.classList.add('saindo');
  setTimeout(() => {
    if (capa.classList.contains('saindo')) {
      capa.hidden = true;
      capa.classList.remove('saindo');
    }
  }, 420);
}

document.getElementById('apresentacao-auto').addEventListener('click', () => ligarAutomatico(!apresentacaoAuto.ligado));
document.getElementById('apresentacao-intervalo').addEventListener('change', (evento) => {
  apresentacaoAuto.intervalo = Number(evento.target.value) || 30000;
  agendarProximaOperacao();
});

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
  } else if (evento.key === ' ' && !evento.target.closest('button')) {
    evento.preventDefault();
    ligarAutomatico(!apresentacaoAuto.ligado);
  }
});

navItems.forEach((btn) => {
  btn.addEventListener('click', () => showPage(btn.dataset.page));
});
