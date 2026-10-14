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
  const pedido = novoPedido('headcount');
  const tela = await comEsqueleto(hcCorpo, 7, () => pywebview.api.get_headcount(
    hcEstado.operacao, hcEstado.visualizacao, hcEstado.mes, hcEstado.periodo_id));
  if (!pedidoVale('headcount', pedido)) return;
  hcTela = tela;

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
      ? `${nome} agora está em ${novaOperacao}. O HC digitado foi junto.`
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
  document.getElementById('hc-vazio-titulo').textContent = tela.operacao === 'todas'
    ? 'Nenhum gestor cadastrado ainda' : `Nenhum gestor cadastrado em ${tela.cards.operacao}`;
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
      : `${plural(linha.usuarios, 'usuário', 'usuários')} na planilha`;
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
document.getElementById('hc-vazio-adicionar').addEventListener('click', () => abrirFaixa('gestor'));
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
