// ---------------------------------------------------------------
// Aba Coverage
// ---------------------------------------------------------------
// Uma linha por usuario, com as horas que vieram do Summary (Horas LMS
// e diretas sem meta) e o que se digita aqui: dias, horas, sinergia
// cedida e recebida. O Python calcula; aqui so se desenha.

const cvOperacao = document.getElementById('cv-operacao');
const cvMes = document.getElementById('cv-mes');
const cvPeriodo = document.getElementById('cv-periodo');
const cvVisualizacao = document.getElementById('cv-visualizacao');
const cvCorpo = document.getElementById('cv-corpo');
const cvTotal = document.getElementById('cv-total');
const cvStatus = document.getElementById('cv-status');
const cvVazio = document.getElementById('cv-vazio');
const cvGestor = document.getElementById('cv-gestor');
const cvAgrupar = document.getElementById('cv-agrupar');

let cvEstado = { operacao: 'todas', visualizacao: 'semanal', mes: null, periodo_id: null, gestor: '' };
let cvTela = null;

function pct(valor) {
  if (valor === null || valor === undefined) return '—';
  return `${(valor * 100).toFixed(2).replace('.', ',')}%`;
}

async function carregarCoverage() {
  const pedido = novoPedido('coverage');
  const tela = await comEsqueleto(cvCorpo, 11, () => pywebview.api.get_coverage(
    cvEstado.operacao, cvEstado.visualizacao, cvEstado.mes, cvEstado.periodo_id, cvEstado.gestor || null));
  if (!pedidoVale('coverage', pedido)) return;
  cvTela = tela;
  cvEstado.mes = cvTela.mes;
  cvEstado.periodo_id = cvTela.periodo_id;
  cvEstado.gestor = cvTela.gestor || '';
  desenharFiltrosCv(cvTela);
  desenharCardsCv(cvTela);
  desenharTabelaCv(cvTela);
  ajustarAlturaCv();
  mostrarSharePoint('cv-sp', cvEstado.operacao, ['week', 'month']);
}

// A lista de usuarios ganha a altura que sobra na janela, e rola sozinha
// quando nao cabe: o resto da tela fica parado. Com poucos usuarios a
// tabela fica do tamanho dela, sem barra.
const cvWrap = document.getElementById('cv-tabela-wrap');
const ESPACO_ABAIXO_DA_LISTA = 104; // formula, linha de status e fim do cartao
// Cabecalho, TOTAL e umas quatro linhas de usuario. Numa tela baixa
// (notebook com zoom de 150%) a lista ficava com linha e meia: abaixo
// disso, quem rola e a pagina.
const ALTURA_MINIMA_DA_LISTA = 320;

function ajustarAlturaCv() {
  if (!cvWrap || cvWrap.hidden || !cvWrap.offsetParent) return;
  const topoNaArea = cvWrap.getBoundingClientRect().top
    - contentArea.getBoundingClientRect().top + contentArea.scrollTop;
  const disponivel = contentArea.clientHeight - topoNaArea - ESPACO_ABAIXO_DA_LISTA;
  cvWrap.style.maxHeight = `${Math.max(ALTURA_MINIMA_DA_LISTA, disponivel)}px`;
  // Se ainda sobrou rolagem na pagina (margens, linha de status que
  // quebrou), a lista encolhe esse tanto: quem rola e so ela.
  const sobra = contentArea.scrollHeight - contentArea.clientHeight;
  if (sobra > 0 && cvWrap.scrollHeight > cvWrap.clientHeight) {
    cvWrap.style.maxHeight = `${Math.max(ALTURA_MINIMA_DA_LISTA, cvWrap.clientHeight - sobra)}px`;
  }
  cvWrap.classList.toggle('com-rolagem', cvWrap.scrollHeight > cvWrap.clientHeight);
  pedirJanelaCv();
}
window.addEventListener('resize', ajustarAlturaCv);

function desenharFiltrosCv(tela) {
  preencherSelect(cvOperacao, tela.operacoes, tela.operacao, 'key', 'label');
  preencherSelect(cvMes, tela.meses, tela.mes);
  const noMes = tela.visualizacao === 'mes';
  if (noMes) {
    preencherSelect(cvPeriodo, [{ id: '', rotulo: 'Não se aplica ao resultado do mês' }], '');
  } else if (!tela.periodos.length) {
    preencherSelect(cvPeriodo, [{ id: '', rotulo: 'Nenhuma semana extraída neste mês' }], '');
  } else {
    preencherSelect(cvPeriodo, tela.periodos, tela.periodo_id);
  }
  cvPeriodo.disabled = noMes || !tela.periodos.length;
  // Gestor: o de cada usuario vem do Supervisor da extracao Week.
  preencherSelect(cvGestor, tela.gestores, tela.gestor || '');
  cvGestor.disabled = tela.gestores.length <= 1;
  cvGestor.title = tela.gestores.length <= 1
    ? 'Sem gestor nesta extração: extraia a Week de novo (agora ela vem com o Supervisor).' : '';
  for (const botao of cvVisualizacao.querySelectorAll('.seg-opcao')) {
    botao.classList.toggle('active', botao.dataset.visualizacao === tela.visualizacao);
  }
  moverDestaque(cvVisualizacao);
}

function desenharCardsCv(tela) {
  const c = tela.cards;
  document.getElementById('cv-card-operacao').textContent = c.operacao;
  document.getElementById('cv-card-operacao-nota').textContent = c.operacao_nota || '';
  document.getElementById('cv-card-periodo').textContent = c.periodo;
  document.getElementById('cv-card-periodo-nota').textContent = c.periodo_nota;
  document.getElementById('cv-card-lms').textContent = `${num(c.lms)} h`;
  document.getElementById('cv-card-usuarios').textContent = plural(tela.total.usuarios, 'usuário', 'usuários');
  document.getElementById('cv-card-metrics').textContent = `${num(c.metrics)} h`;
  document.getElementById('cv-card-coverage').textContent = pct(c.coverage);
}

function campoCoverage(linha, campo, passo) {
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = passo;
  input.value = linha[campo];
  input.dataset.usuario = linha.usuario;
  input.dataset.operacao = linha.operacao_key;
  input.dataset.campo = campo;
  const origem = { dias: linha.dias_origem, horas: linha.horas_origem }[campo];
  if (origem && origem !== 'digitado') {
    input.classList.add('valor-herdado');
    input.title = campo === 'dias'
      ? 'Dias úteis do período. Digite para ajustar só este usuário.'
      : `Padrão de ${num(cvTela.horas_padrao)} h por dia. Digite para ajustar só este usuário.`;
  }
  if (campo === 'dias') {
    input.addEventListener('keydown', (evento) => {
      if (['-', '+', 'e', 'E', ',', '.'].includes(evento.key)) evento.preventDefault();
    });
  }
  input.addEventListener('change', async () => {
    const resposta = await pywebview.api.set_coverage(
      linha.operacao_key, linha.chave_periodo, linha.usuario, campo, input.value);
    if (!resposta.success) {
      cvStatus.textContent = resposta.message;
      input.value = linha[campo];
      return;
    }
    await redesenharCoverageMantendoFoco();
    cvStatus.textContent = 'Salvo. A linha COVERAGE da aba Início já reflete a mudança.';
  });
  return input;
}

async function redesenharCoverageMantendoFoco() {
  const foco = document.activeElement;
  const destino = foco && foco.dataset && foco.dataset.usuario
    ? { usuario: foco.dataset.usuario, operacao: foco.dataset.operacao, campo: foco.dataset.campo } : null;
  const rolagem = cvWrap.scrollTop;
  await carregarCoverage();
  // A lista volta para onde estava (e, se for longa, desenha ali na hora).
  cvWrap.scrollTop = rolagem;
  desenharJanelaCv();
  if (destino) {
    // Linhas de usuario e a linha TOTAL (sinergia da operacao).
    const alvo = Array.from(document.querySelectorAll('#cv-tabela-wrap input')).find((i) =>
      i.dataset.usuario === destino.usuario && i.dataset.operacao === destino.operacao
      && i.dataset.campo === destino.campo);
    if (alvo) { alvo.focus(); alvo.select(); }
  }
}

function criarLinhaCv(item) {
  const tr = document.createElement('tr');
  if (item.grupo !== undefined) {
    tr.className = 'cv-grupo';
    const td = document.createElement('td');
    td.colSpan = 11;
    // O nome fica parado a esquerda mesmo com a tabela rolada de lado.
    const rotulo = document.createElement('div');
    rotulo.className = 'cv-grupo-rotulo';
    rotulo.textContent = item.grupo === '—' ? 'Sem gestor na extração' : item.grupo;
    const quantos = document.createElement('span');
    quantos.textContent = plural(item.quantos, 'usuário', 'usuários');
    rotulo.appendChild(quantos);
    td.appendChild(rotulo);
    tr.appendChild(td);
    return tr;
  }
  const linha = item.linha;
  if (linha.cor === 'vermelho') tr.classList.add('abaixo');
  const usuario = document.createElement('strong');
  usuario.className = 'cv-usuario';
  usuario.textContent = linha.usuario;
  tr.appendChild(celulaCv(usuario));
  tr.appendChild(celulaCv(linha.operacao));
  tr.appendChild(celulaCv(linha.gestor_rotulo, 'cv-gestor-celula'));
  tr.appendChild(celulaCv(num(linha.lms), 'num'));
  tr.appendChild(celulaCv(num(linha.diretas_sem_meta), 'num'));
  tr.appendChild(celulaCv(campoCoverage(linha, 'dias', '1'), 'num'));
  tr.appendChild(celulaCv(campoCoverage(linha, 'horas', '0.25'), 'num'));
  tr.appendChild(celulaCv(num(linha.metrics), 'num cv-metrics'));
  tr.appendChild(celulaCv(campoCoverage(linha, 'cedida', '0.25'), 'num'));
  tr.appendChild(celulaCv(campoCoverage(linha, 'recebida', '0.25'), 'num'));
  tr.appendChild(celulaCv(seloCoverage(linha.coverage, linha.cor), 'num'));
  return tr;
}

// Muitos usuarios (todas as operacoes, mes inteiro): so as linhas que
// aparecem na lista, mais uma folga em cima e embaixo, ficam desenhadas;
// dois espacadores fazem a barra de rolagem ter o tamanho de todas. As
// linhas que ja estao na tela nunca sao recriadas nem movidas (o campo
// em que se esta digitando nao perde o foco): so entram e saem nas pontas.
const CV_VIRTUAL_A_PARTIR = 150;
const CV_FOLGA = 20;
const cvVirtual = { ativo: false, itens: [], linhas: new Map(), ini: 0, fim: 0, alturas: null, topo: null, base: null };

function montarListaCv(itens) {
  cvVirtual.itens = itens;
  cvVirtual.linhas = new Map();
  cvVirtual.ativo = itens.length > CV_VIRTUAL_A_PARTIR;
  if (!cvVirtual.ativo) {
    const pedaco = document.createDocumentFragment();
    itens.forEach((item) => pedaco.appendChild(criarLinhaCv(item)));
    cvCorpo.appendChild(pedaco);
    return;
  }
  cvVirtual.topo = espacadorCv();
  cvVirtual.base = espacadorCv();
  cvCorpo.append(cvVirtual.topo, cvVirtual.base);
  cvVirtual.ini = cvVirtual.fim = 0;
  cvVirtual.alturas = null;
  desenharJanelaCv();
}

function espacadorCv() {
  const tr = document.createElement('tr');
  tr.className = 'cv-espaco';
  tr.setAttribute('aria-hidden', 'true');
  const td = document.createElement('td');
  td.colSpan = 11;
  tr.appendChild(td);
  return tr;
}

// Altura de cada item (linha ou titulo de gestor), medida uma vez.
function alturasCv() {
  if (cvVirtual.alturas) return cvVirtual.alturas;
  const medir = (item) => {
    const tr = criarLinhaCv(item);
    cvCorpo.insertBefore(tr, cvVirtual.base);
    const altura = tr.getBoundingClientRect().height || 44;
    tr.remove();
    return altura;
  };
  const primeiraLinha = cvVirtual.itens.find((i) => i.linha);
  const primeiroGrupo = cvVirtual.itens.find((i) => i.grupo !== undefined);
  const linha = primeiraLinha ? medir(primeiraLinha) : 44;
  const grupo = primeiroGrupo ? medir(primeiroGrupo) : linha;
  cvVirtual.alturas = { linha, grupo, calibrada: false, inicio: somarAlturasCv(linha, grupo) };
  return cvVirtual.alturas;
}

function somarAlturasCv(linha, grupo) {
  const inicio = [0];
  cvVirtual.itens.forEach((item, i) => inicio.push(inicio[i] + (item.linha ? linha : grupo)));
  return inicio;
}

// Depois do primeiro desenho, a altura media de verdade das linhas (a
// medida de uma so pode diferir em fracao de pixel, que somada em
// centenas de linhas faz a barra de rolagem pular).
function calibrarAlturasCv() {
  const a = cvVirtual.alturas;
  if (!a || a.calibrada) return;
  const medidas = [...cvVirtual.linhas.entries()]
    .filter(([i]) => cvVirtual.itens[i].linha)
    .map(([, tr]) => tr.getBoundingClientRect().height);
  if (medidas.length < 10) return;
  a.calibrada = true;
  const media = medidas.reduce((x, y) => x + y, 0) / medidas.length;
  if (Math.abs(media - a.linha) < 0.05) return;
  a.linha = media;
  a.inicio = somarAlturasCv(a.linha, a.grupo);
  cvVirtual.topo.firstChild.style.height = `${a.inicio[cvVirtual.ini]}px`;
  cvVirtual.base.firstChild.style.height = `${a.inicio[cvVirtual.itens.length] - a.inicio[cvVirtual.fim]}px`;
}

function indiceNaAltura(inicio, y) {
  let baixo = 0;
  let alto = inicio.length - 1;
  while (baixo < alto) {
    const meio = (baixo + alto + 1) >> 1;
    if (inicio[meio] <= y) baixo = meio; else alto = meio - 1;
  }
  return Math.min(baixo, cvVirtual.itens.length - 1);
}

function desenharJanelaCv() {
  if (!cvVirtual.ativo || !cvVirtual.base.isConnected) return;
  const { inicio } = alturasCv();
  const cabecalho = cvWrap.querySelector('thead')?.getBoundingClientRect().height || 0;
  const topo = Math.max(0, cvWrap.scrollTop - cabecalho);
  // Antes de a lista ganhar a altura dela (ajustarAlturaCv), conta no
  // maximo a janela inteira: senao desenharia todas as linhas.
  const altura = Math.min(cvWrap.clientHeight || window.innerHeight, window.innerHeight);
  const total = cvVirtual.itens.length;
  let ini = Math.max(0, indiceNaAltura(inicio, topo) - CV_FOLGA);
  let fim = Math.min(total, indiceNaAltura(inicio, topo + altura) + 1 + CV_FOLGA);
  // A linha do campo com foco continua desenhada mesmo rolada para longe:
  // quem esta digitando nao perde o que digitou.
  for (const [i, tr] of cvVirtual.linhas) {
    if (tr.contains(document.activeElement)) {
      ini = Math.min(ini, i);
      fim = Math.max(fim, i + 1);
    }
  }
  if (ini === cvVirtual.ini && fim === cvVirtual.fim) return;

  // Sai o que ficou de fora.
  for (const [i, tr] of cvVirtual.linhas) {
    if (i >= ini && i < fim) continue;
    tr.remove();
    cvVirtual.linhas.delete(i);
  }
  // Entra o que faltava, nas pontas (sem nenhuma em comum, tudo depois).
  const desenhadas = [...cvVirtual.linhas.keys()];
  const primeira = desenhadas.length ? Math.min(...desenhadas) : ini;
  const ultima = desenhadas.length ? Math.max(...desenhadas) : ini - 1;
  const antes = document.createDocumentFragment();
  for (let i = ini; i < primeira; i += 1) {
    const tr = criarLinhaCv(cvVirtual.itens[i]);
    cvVirtual.linhas.set(i, tr);
    antes.appendChild(tr);
  }
  cvCorpo.insertBefore(antes, cvVirtual.topo.nextSibling);
  const depois = document.createDocumentFragment();
  for (let i = Math.max(ultima + 1, ini); i < fim; i += 1) {
    const tr = criarLinhaCv(cvVirtual.itens[i]);
    cvVirtual.linhas.set(i, tr);
    depois.appendChild(tr);
  }
  cvCorpo.insertBefore(depois, cvVirtual.base);
  cvVirtual.ini = ini;
  cvVirtual.fim = fim;
  cvVirtual.topo.firstChild.style.height = `${inicio[ini]}px`;
  cvVirtual.base.firstChild.style.height = `${inicio[total] - inicio[fim]}px`;
  calibrarAlturasCv();
}

let cvJanelaPedida = false;
function pedirJanelaCv() {
  if (!cvVirtual.ativo || cvJanelaPedida) return;
  cvJanelaPedida = true;
  requestAnimationFrame(() => { cvJanelaPedida = false; desenharJanelaCv(); });
}

function celulaCv(conteudo, classe) {
  const td = document.createElement('td');
  if (classe) td.className = classe;
  if (conteudo instanceof Node) td.appendChild(conteudo); else td.textContent = conteudo;
  return td;
}

// Sinergia da operacao, na linha TOTAL: a visibilidade e da operacao
// (horas cedidas a outra ou recebidas dela), nao de cada pessoa.
function campoSinergiaOperacao(t, campo) {
  const caixa = document.createElement('div');
  caixa.className = 'cv-sinergia-total';
  const input = document.createElement('input');
  input.type = 'number';
  input.min = '0';
  input.step = '0.25';
  input.value = t[`${campo}_operacao`];
  input.dataset.usuario = '__total__';
  input.dataset.operacao = cvEstado.operacao;
  input.dataset.campo = campo;
  if (!t.sinergia_editavel) {
    input.disabled = true;
    input.value = t[campo];
    input.title = cvTela.gestor
      ? 'A sinergia é da operação inteira: com um gestor no filtro ela não entra no total.'
      : 'A sinergia é de uma operação: escolha uma operação para lançar.';
  } else {
    input.title = `Sinergia ${campo} da operação nesta semana (horas).`;
    input.addEventListener('change', async () => {
      const resposta = await pywebview.api.set_coverage_sinergia(
        cvEstado.operacao, t.chave_periodo, campo, input.value);
      if (!resposta.success) {
        cvStatus.textContent = resposta.message;
        input.value = t[`${campo}_operacao`];
        return;
      }
      await redesenharCoverageMantendoFoco();
      cvStatus.textContent = 'Sinergia da operação salva. O coverage total e a aba Início já refletem.';
    });
  }
  caixa.appendChild(input);
  const porUsuario = t[`${campo}_usuarios`];
  if (porUsuario) {
    const nota = document.createElement('span');
    nota.className = 'cv-sinergia-nota';
    nota.textContent = `+ ${num(porUsuario)} h dos usuários`;
    caixa.appendChild(nota);
  }
  return caixa;
}

function seloCoverage(valor, cor) {
  const selo = document.createElement('span');
  selo.className = `cv-coverage ${cor || 'sem-numero'}`;
  selo.textContent = pct(valor);
  return selo;
}

function desenharTabelaCv(tela) {
  document.getElementById('cv-titulo').textContent = tela.visualizacao === 'mes'
    ? 'Coverage do mês por usuário' : 'Coverage da semana por usuário';
  document.getElementById('cv-contador').textContent = plural(tela.linhas.length, 'usuário', 'usuários');
  const vazio = !tela.linhas.length;
  cvVazio.hidden = !vazio;
  document.getElementById('cv-tabela-wrap').hidden = vazio;
  document.getElementById('cv-todos').hidden = vazio;
  if (vazio) {
    const noMes = tela.visualizacao === 'mes';
    document.getElementById('cv-vazio-titulo').textContent =
      `Nenhuma extração ${noMes ? 'Month' : 'Week'} de ${tela.cards.operacao} em ${cvMes.selectedOptions[0]?.text || 'neste mês'} ainda`;
    document.getElementById('cv-vazio-texto').textContent = noMes
      ? 'Extraia o mês (Month) para ver o coverage de cada usuário.'
      : 'Extraia a semana (Week) para ver o coverage de cada usuário e de cada gestor.';
    botaoMesAnterior(document.getElementById('cv-vazio-anterior'), tela.meses, tela.mes);
  }

  cvCorpo.innerHTML = '';
  // Agrupado: os usuarios de cada gestor juntos, com o nome dele em cima.
  // So muda a ordem e poe os titulos; os numeros sao os mesmos.
  const podeAgrupar = !tela.gestor && tela.gestores.length > 1;
  cvAgrupar.disabled = !podeAgrupar;
  cvAgrupar.closest('.cv-agrupar').classList.toggle('desligado', !podeAgrupar);
  const agrupar = podeAgrupar && cvAgrupar.checked;
  const linhas = agrupar
    ? [...tela.linhas].sort((a, b) => a.gestor_rotulo.localeCompare(b.gestor_rotulo, 'pt-BR')
      || a.operacao.localeCompare(b.operacao, 'pt-BR') || a.usuario.localeCompare(b.usuario, 'pt-BR'))
    : tela.linhas;
  const porGrupo = new Map();
  linhas.forEach((l) => porGrupo.set(l.gestor_rotulo, (porGrupo.get(l.gestor_rotulo) || 0) + 1));
  const itens = [];
  let grupoAtual = null;
  for (const linha of linhas) {
    if (agrupar && linha.gestor_rotulo !== grupoAtual) {
      grupoAtual = linha.gestor_rotulo;
      itens.push({ grupo: grupoAtual, quantos: porGrupo.get(grupoAtual) });
    }
    itens.push({ linha });
  }
  montarListaCv(itens);

  cvTotal.innerHTML = '';
  if (vazio) return;
  const t = tela.total;
  const tr = document.createElement('tr');
  [
    ['TOTAL', ''], [plural(t.usuarios, 'usuário', 'usuários'), ''], [cvTela.gestor_rotulo || '', 'cv-gestor-celula'],
    [num(t.lms), 'num'], [num(t.diretas_sem_meta), 'num'], ['', 'num'], ['', 'num'],
    [num(t.metrics), 'num'],
  ].forEach(([texto, classe]) => tr.appendChild(celulaCv(texto, classe)));
  for (const campo of ['cedida', 'recebida']) {
    tr.appendChild(celulaCv(campoSinergiaOperacao(t, campo), 'num'));
  }
  const tdTotal = celulaCv(seloCoverage(t.coverage, t.cor), 'num');
  tdTotal.firstChild.classList.add('cv-coverage-total');
  tr.appendChild(tdTotal);
  cvTotal.appendChild(tr);
}

cvOperacao.addEventListener('change', async () => {
  cvEstado.operacao = cvOperacao.value;
  cvEstado.periodo_id = null;
  cvEstado.gestor = '';
  await carregarCoverage();
});
document.getElementById('cv-vazio-anterior').addEventListener('click', async (evento) => {
  cvEstado.mes = evento.currentTarget.dataset.mes;
  cvEstado.periodo_id = null;
  await carregarCoverage();
});
cvAgrupar.addEventListener('change', () => { if (cvTela) desenharTabelaCv(cvTela); });
// Rolando a tabela para o lado, a coluna do usuario (parada) ganha sombra.
document.getElementById('cv-tabela-wrap').addEventListener('scroll', (evento) => {
  evento.currentTarget.classList.toggle('rolado-lado', evento.currentTarget.scrollLeft > 0);
  pedirJanelaCv();
}, { passive: true });
window.addEventListener('resize', pedirJanelaCv);
cvGestor.addEventListener('change', async () => {
  cvEstado.gestor = cvGestor.value;
  await carregarCoverage();
});
cvMes.addEventListener('change', async () => {
  cvEstado.mes = cvMes.value;
  cvEstado.periodo_id = null;
  await carregarCoverage();
});
cvPeriodo.addEventListener('change', async () => {
  cvEstado.periodo_id = cvPeriodo.value;
  await carregarCoverage();
});
document.getElementById('cv-extrair').addEventListener('click', () => {
  irParaExtracao(cvEstado.operacao === 'todas' ? null : cvEstado.operacao,
    cvEstado.visualizacao === 'mes' ? 'month' : 'week', 'User ID');
});

cvVisualizacao.addEventListener('click', async (evento) => {
  const botao = evento.target.closest('.seg-opcao');
  if (!botao) return;
  cvVisualizacao.querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b === botao));
  moverDestaque(cvVisualizacao);
  cvEstado.visualizacao = botao.dataset.visualizacao;
  cvEstado.periodo_id = null;
  await carregarCoverage();
});
window.addEventListener('resize', () => moverDestaque(cvVisualizacao));

const cvAplicar = document.getElementById('cv-aplicar-todos');
cvAplicar.addEventListener('click', () => comCarregando(cvAplicar, async () => {
  const pedidos = [['dias', document.getElementById('cv-todos-dias')],
    ['horas', document.getElementById('cv-todos-horas')]].filter(([, campo]) => campo.value !== '');
  if (!pedidos.length) {
    cvStatus.textContent = 'Digite os dias ou as horas que valem para todos os usuários desta tela.';
    return;
  }
  for (const [campo, entrada] of pedidos) {
    const resposta = await pywebview.api.set_coverage_todos(
      cvEstado.operacao, cvEstado.visualizacao, cvEstado.mes, cvEstado.periodo_id, campo, entrada.value,
      cvEstado.gestor || null);
    if (!resposta.success) {
      cvStatus.textContent = resposta.message;
      return;
    }
    entrada.value = '';
  }
  await carregarCoverage();
  cvStatus.textContent = `Aplicado a ${plural(cvTela.linhas.length, 'usuário', 'usuários')} desta tela.`;
}));
