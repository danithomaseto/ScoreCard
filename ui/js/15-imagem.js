// ---------------------------------------------------------------
// Tabela da Inicio como imagem (para o PowerPoint)
// ---------------------------------------------------------------
// Desenhada num canvas a partir da tabela da tela, sempre no visual
// claro (fundo branco combina com o slide e com a impressao), em dobro
// de resolucao para nao borrar no projetor. O botao Imagem copia; com
// Shift, ou se a copia falhar, salva o PNG em Downloads.

const IMAGEM = {
  escala: 2,
  margem: 28,
  fundo: '#ffffff',
  texto: '#1d2433',
  apagado: '#566072',
  fraco: '#6b7280',
  linha: '#eceff4',
  borda: '#d3d9e3',
  coluna: '#f5f7fa',
  destaque: '#8a6100',
  cores: {
    verde: { fundo: '#dcf5e5', texto: '#166534', simbolo: '✓' },
    vermelho: { fundo: '#fde4e8', texto: '#b42318', simbolo: '▼' },
    azul: { fundo: '#dcf1fb', texto: '#026aa2', simbolo: '▲' },
  },
};

// O que esta na tabela da tela, sem estilo: a imagem e redesenhada.
function lerTabelaDaInicio() {
  const cabecalho = document.getElementById('indicators-head');
  const corpo = document.getElementById('indicators-body');
  const colunas = [...cabecalho.querySelectorAll('th.indicator-col')].map((th) => ({
    titulo: th.querySelector('.col-title')?.textContent || '',
    subtitulo: th.querySelector('.col-subtitle')?.textContent || '',
    aviso: th.querySelector('.col-warning')?.textContent || '',
    mes: th.classList.contains('month-col'),
    pico: th.classList.contains('peak-col'),
  }));
  const linhas = [...corpo.querySelectorAll('tr')].filter((tr) => !tr.classList.contains('linha-esqueleto')).map((tr) => ({
    rotulo: tr.querySelector('.indicator-label')?.textContent || '',
    meta: tr.querySelector('.indicator-meta')?.textContent || '',
    celulas: [...tr.querySelectorAll('td')].map((td) => {
      const valor = td.querySelector('.indicator-value');
      if (valor) {
        const cor = ['verde', 'vermelho', 'azul'].find((c) => valor.classList.contains(c)) || '';
        return { texto: valor.textContent, cor };
      }
      return { texto: td.classList.contains('sem-numero') ? '—' : '', vazio: true };
    }),
  }));
  return {
    operacao: homeOperationSelect.selectedOptions[0]?.text || '',
    mes: homeMes.selectedOptions[0]?.text || '',
    colunas,
    linhas,
  };
}

function desenharImagemDaTabela(dados) {
  const fonte = getComputedStyle(document.body).fontFamily || 'Segoe UI, sans-serif';
  const f = (peso, tamanho) => `${peso} ${tamanho}px ${fonte}`;
  const medir = document.createElement('canvas').getContext('2d');
  const largura = (texto, estilo) => { medir.font = estilo; return medir.measureText(texto).width; };

  const { margem } = IMAGEM;
  const estilos = {
    titulo: f(700, 22), sub: f(400, 13), canto: f(700, 11), colTitulo: f(700, 16), colSub: f(400, 12),
    aviso: f(600, 11), rotulo: f(700, 15), meta: f(400, 12), valor: f(700, 16), simbolo: f(700, 11), legenda: f(400, 12),
  };
  const larguraDoValor = (celula) => largura(celula.texto, estilos.valor) + (celula.cor ? 16 : 0) + 24;

  const primeira = Math.max(190, ...dados.linhas.map((l) => Math.max(largura(l.rotulo, estilos.rotulo), largura(l.meta, estilos.meta))),
    largura(dados.operacao, f(700, 20))) + 28;
  const larguras = dados.colunas.map((coluna, i) => Math.max(
    120,
    largura(coluna.titulo, estilos.colTitulo),
    largura(coluna.subtitulo, estilos.colSub),
    largura(coluna.aviso, estilos.aviso),
    ...dados.linhas.map((l) => (l.celulas[i] && !l.celulas[i].vazio ? larguraDoValor(l.celulas[i]) : 0)),
  ) + 28);
  const alturaCabecalho = dados.colunas.some((c) => c.aviso) ? 70 : 56;
  const alturaLinha = 50;
  const topoTabela = margem + 62;
  const larguraTabela = primeira + larguras.reduce((a, b) => a + b, 0);
  const W = Math.ceil(larguraTabela + margem * 2);
  const H = Math.ceil(topoTabela + alturaCabecalho + alturaLinha * dados.linhas.length + 40 + margem);

  const canvas = document.createElement('canvas');
  canvas.width = W * IMAGEM.escala;
  canvas.height = H * IMAGEM.escala;
  const c = canvas.getContext('2d');
  c.scale(IMAGEM.escala, IMAGEM.escala);
  c.fillStyle = IMAGEM.fundo;
  c.fillRect(0, 0, W, H);
  c.textBaseline = 'alphabetic';

  // Titulo: de quem e e de quando, porque o slide sai da tela do app.
  c.fillStyle = IMAGEM.texto;
  c.font = estilos.titulo;
  c.textAlign = 'left';
  c.fillText(`${dados.operacao} · ${dados.mes}`, margem, margem + 22);
  c.fillStyle = IMAGEM.apagado;
  c.font = estilos.sub;
  c.fillText(`Indicadores do Score Card DHL · gerado em ${new Date().toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })}`,
    margem, margem + 44);

  // Fundo das colunas do mes e do pico, e a divisa antes do mes.
  let x = margem + primeira;
  const xs = [];
  dados.colunas.forEach((coluna, i) => {
    xs.push(x);
    if (coluna.mes || coluna.pico) {
      c.fillStyle = IMAGEM.coluna;
      c.fillRect(x, topoTabela, larguras[i], alturaCabecalho + alturaLinha * dados.linhas.length);
    }
    if (coluna.mes && (i === 0 || !dados.colunas[i - 1].mes)) {
      c.fillStyle = IMAGEM.borda;
      c.fillRect(x - 1, topoTabela, 2, alturaCabecalho + alturaLinha * dados.linhas.length);
    }
    x += larguras[i];
  });

  // Cabecalho.
  c.textAlign = 'left';
  c.fillStyle = IMAGEM.apagado;
  c.font = estilos.canto;
  c.fillText('OPERAÇÃO', margem, topoTabela + alturaCabecalho - 30);
  c.fillStyle = IMAGEM.destaque;
  c.font = f(700, 20);
  c.fillText(dados.operacao, margem, topoTabela + alturaCabecalho - 10);
  dados.colunas.forEach((coluna, i) => {
    const meio = xs[i] + larguras[i] / 2;
    c.textAlign = 'center';
    c.fillStyle = coluna.pico ? IMAGEM.destaque : IMAGEM.texto;
    c.font = estilos.colTitulo;
    c.fillText(coluna.titulo, meio, topoTabela + 24);
    c.fillStyle = IMAGEM.apagado;
    c.font = estilos.colSub;
    c.fillText(coluna.subtitulo, meio, topoTabela + 42);
    if (coluna.aviso) {
      c.fillStyle = '#9a3412';
      c.font = estilos.aviso;
      c.fillText(coluna.aviso, meio, topoTabela + 58);
    }
  });
  c.fillStyle = IMAGEM.borda;
  c.fillRect(margem, topoTabela + alturaCabecalho - 1, larguraTabela, 1);

  // Linhas.
  dados.linhas.forEach((linha, n) => {
    const topo = topoTabela + alturaCabecalho + alturaLinha * n;
    const meioY = topo + alturaLinha / 2;
    if (n > 0) {
      c.fillStyle = IMAGEM.linha;
      c.fillRect(margem, topo, larguraTabela, 1);
    }
    c.textAlign = 'left';
    c.fillStyle = IMAGEM.texto;
    c.font = estilos.rotulo;
    c.fillText(linha.rotulo, margem, meioY - 2);
    c.fillStyle = IMAGEM.apagado;
    c.font = estilos.meta;
    c.fillText(linha.meta, margem, meioY + 15);
    linha.celulas.forEach((celula, i) => {
      if (i >= xs.length) return;
      const meio = xs[i] + larguras[i] / 2;
      if (celula.vazio) {
        if (!celula.texto) return;
        c.textAlign = 'center';
        c.fillStyle = IMAGEM.fraco;
        c.font = estilos.valor;
        c.fillText(celula.texto, meio, meioY + 6);
        return;
      }
      const cor = IMAGEM.cores[celula.cor];
      const w = larguraDoValor(celula);
      const h = 32;
      if (cor) {
        c.fillStyle = cor.fundo;
        c.beginPath();
        c.roundRect(meio - w / 2, meioY - h / 2, w, h, 6);
        c.fill();
      }
      c.fillStyle = cor ? cor.texto : IMAGEM.texto;
      c.textAlign = 'left';
      let xTexto = meio - w / 2 + 12;
      if (cor) {
        c.font = estilos.simbolo;
        c.fillText(cor.simbolo, xTexto, meioY + 4);
        xTexto += 16;
      }
      c.font = estilos.valor;
      c.fillText(celula.texto, xTexto, meioY + 6);
    });
  });

  // Legenda: a cor sempre com o simbolo e o texto.
  let xLegenda = margem;
  const yLegenda = topoTabela + alturaCabecalho + alturaLinha * dados.linhas.length + 30;
  c.fillStyle = IMAGEM.borda;
  c.fillRect(margem, yLegenda - 22, larguraTabela, 1);
  for (const [chave, texto] of [['verde', 'dentro da meta'], ['vermelho', 'abaixo da meta'], ['azul', 'acima do teto'], ['', 'ainda sem número']]) {
    const cor = IMAGEM.cores[chave];
    c.textAlign = 'left';
    if (cor) {
      c.fillStyle = cor.fundo;
      c.beginPath();
      c.roundRect(xLegenda, yLegenda - 11, 16, 16, 4);
      c.fill();
      c.fillStyle = cor.texto;
      c.font = f(700, 9);
      c.textAlign = 'center';
      c.fillText(cor.simbolo, xLegenda + 8, yLegenda + 1);
    } else {
      c.fillStyle = IMAGEM.fraco;
      c.font = f(700, 13);
      c.fillText('—', xLegenda, yLegenda + 2);
    }
    c.textAlign = 'left';
    c.fillStyle = IMAGEM.apagado;
    c.font = estilos.legenda;
    c.fillText(texto, xLegenda + 22, yLegenda + 2);
    xLegenda += 22 + largura(texto, estilos.legenda) + 22;
  }
  return canvas;
}

async function exportarImagemDaTabela(modo = 'copiar', botao = null) {
  const dados = lerTabelaDaInicio();
  if (!dados.colunas.length || !dados.linhas.length) {
    avisar('Sem tabela para exportar', 'erro', 'Escolha uma operação e um mês com dados na Início.');
    return;
  }
  const canvas = desenharImagemDaTabela(dados);
  const descricao = `${dados.operacao} · ${dados.mes}`;
  if (modo === 'copiar') {
    try {
      // A promessa vai direto no ClipboardItem: a copia acontece ainda
      // dentro do clique (o navegador so deixa copiar logo depois dele).
      const png = new Promise((resolver, falhar) => canvas.toBlob((b) => (b ? resolver(b) : falhar(new Error('sem png'))), 'image/png'));
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': png })]);
      avisar(`Imagem copiada: ${descricao}`, 'ok', 'Cole no PowerPoint com Ctrl+V.');
      if (botao) mostrarNoBotao(botao, 'Copiada');
      return;
    } catch (erro) {
      // sem area de transferencia de imagem: vai como arquivo
    }
  }
  try {
    const r = await pywebview.api.salvar_imagem(descricao, canvas.toDataURL('image/png'));
    if (r && r.success) {
      avisar(modo === 'copiar' ? 'Não deu para copiar: a imagem foi salva' : 'Imagem salva', 'ok', r.caminho);
      if (botao) mostrarNoBotao(botao, 'Salva');
    } else {
      avisar('Não deu para salvar a imagem', 'erro', r?.message || '');
    }
  } catch (erro) {
    registrarErro('imagem da tabela', erro);
  }
}

function mostrarNoBotao(botao, texto) {
  const rotulo = botao.lastChild;
  if (!rotulo || rotulo.nodeType !== Node.TEXT_NODE) return;
  const original = botao.dataset.rotulo || rotulo.textContent;
  botao.dataset.rotulo = original;
  rotulo.textContent = ` ${texto}`;
  botao.classList.add('copiado');
  clearTimeout(botao.timerCopia);
  botao.timerCopia = setTimeout(() => {
    rotulo.textContent = original;
    botao.classList.remove('copiado');
  }, 2000);
}

document.getElementById('home-imagem').addEventListener('click', (evento) => {
  exportarImagemDaTabela(evento.shiftKey ? 'salvar' : 'copiar', evento.currentTarget);
});
