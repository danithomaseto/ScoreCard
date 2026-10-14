// ---------------------------------------------------------------
// Abas Resultado Gestor e Resultado Turno
// ---------------------------------------------------------------
// A mesma tabela da aba Inicio, uma por gestor (ou turno). No topo, a
// lista para marcar quais aparecem, como a lista de operacoes do Extrair
// Multiplos. Os numeros e as cores vem prontos do Python (grupos_tela.py).

function criarAbaDeGrupo(dimensao, pre) {
  const el = (id) => document.getElementById(`${pre}-${id}`);
  const estado = { operacao: null, mes: null, vis: 'tabelas', periodoResumo: null };
  // Tabelas recolhidas nesta sessao (por nome do grupo).
  const recolhidos = new Set();
  const nomes = dimensao === 'gestor'
    ? { singular: 'Gestor', plural: 'gestores', tipo: 'Gestor · Week', mes: 'Gestor · Month', nivel: 'Supervisor' }
    : { singular: 'Turno', plural: 'turnos', tipo: 'Turno · Week', mes: 'Turno · Month', nivel: 'Shift' };
  const tipoWeek = `${dimensao}_week`;
  let tela = null;

  async function carregar() {
    const tabelas = el('tabelas');
    if (!tela) tabelas.innerHTML = '<div class="card indicators-card"><div class="ind-esqueleto grupos-esqueleto"></div></div>';
    const pedido = novoPedido(pre);
    const antes = valoresNaTela();
    const nova = await comAtualizando(tela ? tabelas : null,
      () => pywebview.api.get_resultado_grupo(dimensao, estado.operacao, estado.mes));
    if (!pedidoVale(pre, pedido)) return;
    tela = nova;
    estado.operacao = tela.operacao;
    estado.mes = tela.mes;
    desenhar();
    contarValoresQueMudaram(antes);
  }

  function desenhar() {
    preencherSelect(el('operacao'), tela.operacoes, tela.operacao, 'key', 'label');
    preencherSelect(el('mes'), tela.meses, tela.mes);
    el('ultima').textContent = tela.ultima_extracao || `Nenhuma extração de ${tela.operacao_rotulo} neste mês ainda`;
    mostrarSharePoint(`${pre}-sp`, tela.operacao, [`${dimensao}_week`, `${dimensao}_month`]);

    const temDados = tela.colunas.length > 0;
    el('grupos-card').hidden = !temDados;
    el('vazio').hidden = temDados;
    el('legenda').hidden = !temDados || !tela.tabelas.length;
    const porGrupo = estado.vis === 'tabelas';
    el('navegacao').hidden = !temDados || !porGrupo || tela.tabelas.length < 2;
    el('resumo').hidden = !temDados || porGrupo || !tela.tabelas.length;
    el('tabelas').hidden = !porGrupo;
    el('visualizacao').querySelectorAll('.seg-opcao').forEach((b) => b.classList.toggle('active', b.dataset.vis === estado.vis));
    moverDestaque(el('visualizacao'));
    if (!temDados) {
      el('tabelas').innerHTML = '';
      el('vazio-titulo').textContent =
        `Nenhuma extração ${nomes.tipo} de ${tela.operacao_rotulo} em ${tela.mes_rotulo} ainda`;
      el('vazio-texto').textContent = `Extraia ${nomes.tipo} (Week › ${nomes.nivel} › User ID) e ${nomes.mes} `
        + `(${nomes.nivel} › User ID): cada semana vira uma coluna, o mês entra no final e cada ${nomes.singular.toLowerCase()} ganha a sua tabela.`;
      botaoMesAnterior(el('vazio-anterior'), tela.meses, tela.mes);
      return;
    }
    desenharLista();
    if (porGrupo) {
      desenharNavegacao();
      desenharTabelas();
    } else {
      desenharResumo();
      if (!tela.tabelas.length) {
        el('tabelas').hidden = false;
        desenharTabelas(); // mostra o "nenhum marcado"
      }
    }
    el('legenda-nota').textContent = dimensao === 'gestor'
      ? 'Presenteísmo e cubo só para gestor com o mesmo nome no Headcount.'
      : 'Turno não tem presenteísmo: presenteísmo e cubo não se aplicam.';
  }

  function desenharLista() {
    const lista = el('lista');
    lista.innerHTML = '';
    for (const grupo of tela.grupos) {
      const item = document.createElement('label');
      item.className = 'ops-item grupo-item' + (grupo.visivel ? ' selected' : '');
      const caixa = document.createElement('input');
      caixa.type = 'checkbox';
      caixa.checked = grupo.visivel;
      caixa.value = grupo.id;
      caixa.addEventListener('change', () => {
        item.classList.toggle('selected', caixa.checked);
        salvarVisiveis();
      });
      const nome = document.createElement('span');
      nome.className = 'grupo-nome';
      nome.textContent = grupo.rotulo;
      nome.title = grupo.rotulo;
      item.append(caixa, nome);
      if (grupo.vinculado) {
        const selo = document.createElement('span');
        selo.className = 'grupo-selo';
        selo.textContent = 'HC';
        selo.title = 'Presenteísmo do Headcount: há um gestor com este mesmo nome lá.';
        item.appendChild(selo);
      }
      lista.appendChild(item);
    }
    const visiveis = tela.grupos.filter((g) => g.visivel).length;
    el('contador').textContent = `· ${visiveis} de ${tela.grupos.length}`;
    el('nota').textContent = dimensao === 'gestor'
      ? 'O nome é o da planilha. O presenteísmo e o cubo aparecem para quem está no Headcount com o mesmo nome (marcado com HC); nome diferente não puxa nada.'
      : 'Os turnos são os que vieram no arquivo extraído (coluna Shift).';
  }

  async function salvarVisiveis(todos) {
    const caixas = Array.from(el('lista').querySelectorAll('input[type="checkbox"]'));
    if (todos !== undefined) {
      caixas.forEach((c) => { c.checked = todos; c.parentElement.classList.toggle('selected', todos); });
    }
    const resposta = await pywebview.api.set_grupos_visiveis(
      dimensao, estado.operacao, tela.grupos.map((g) => g.id), caixas.filter((c) => c.checked).map((c) => c.value));
    if (resposta && resposta.success === false) {
      avisarErro(resposta.message);
      return;
    }
    await carregar();
  }

  function desenharTabelas() {
    const area = el('tabelas');
    const antes = new Set(Array.from(area.querySelectorAll('[data-grupo]')).map((c) => c.dataset.grupo));
    area.innerHTML = '';
    if (!tela.tabelas.length) {
      const vazio = document.createElement('div');
      vazio.className = 'card indicators-card';
      vazio.innerHTML = '<div class="estado-vazio"><svg class="estado-vazio-icone" viewBox="0 0 24 24" aria-hidden="true">'
        + '<rect x="3" y="3" width="18" height="18" rx="2"></rect><polyline points="8 12 11 15 16 9"></polyline></svg>'
        + `<strong>Nenhum ${nomes.singular.toLowerCase()} marcado</strong>`
        + `<p>Marque na lista acima quais ${nomes.plural} aparecem. A escolha fica guardada para esta operação.</p>`
        + '<div class="estado-vazio-acoes"><button type="button" class="acao">Selecionar todos</button></div></div>';
      vazio.querySelector('button').addEventListener('click', () => salvarVisiveis(true));
      area.appendChild(vazio);
      return;
    }
    tela.tabelas.forEach((tabela, indice) => {
      const card = document.createElement('div');
      card.className = 'card indicators-card grupo-tabela';
      card.dataset.grupo = tabela.id;
      // So o que acabou de entrar na tela anima; o resto so troca o valor.
      if (!antes.has(tabela.id) && !SEM_ANIMACAO) {
        card.classList.add('grupo-entrando');
        card.style.animationDelay = `${Math.min(indice, 6) * 50}ms`;
      }
      card.id = `${pre}-grupo-${indice}`;
      if (recolhidos.has(tabela.id)) card.classList.add('recolhido');
      const alternar = document.createElement('button');
      alternar.type = 'button';
      alternar.className = 'grupo-alternar';
      alternar.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="6 9 12 15 18 9"></polyline></svg>';
      const atualizarRotulo = () => {
        const fechado = card.classList.contains('recolhido');
        alternar.title = fechado ? 'Abrir a tabela' : 'Recolher a tabela';
        alternar.setAttribute('aria-expanded', String(!fechado));
      };
      atualizarRotulo();
      alternar.addEventListener('click', () => {
        animarAltura(card, () => card.classList.toggle('recolhido'));
        if (card.classList.contains('recolhido')) recolhidos.add(tabela.id); else recolhidos.delete(tabela.id);
        atualizarRotulo();
      });
      card.appendChild(alternar);
      card.appendChild(linhaCompacta(tabela, () => alternar.click()));
      const wrap = document.createElement('div');
      wrap.className = 'table-wrap';
      const t = document.createElement('table');
      t.className = 'indicators-table';
      const thead = document.createElement('thead');
      const linhaCabecalho = document.createElement('tr');
      thead.appendChild(linhaCabecalho);
      const corpo = document.createElement('tbody');
      t.append(thead, corpo);
      wrap.appendChild(t);
      card.appendChild(wrap);
      area.appendChild(card);

      let nota = null;
      if (dimensao === 'gestor') {
        nota = tabela.vinculado
          ? { texto: 'presenteísmo do Headcount', classe: 'ok' }
          : { texto: 'sem o mesmo nome no Headcount', classe: 'alerta',
            dica: 'Cadastre no Headcount um gestor com exatamente este nome para o presenteísmo e o cubo aparecerem.' };
      }
      desenharCabecalhoEm(linhaCabecalho, corpo, tela.colunas, nomes.singular, tabela.rotulo, nota);
      desenharLinhasEm(corpo, tabela.linhas, tela.colunas);
      wrap.scrollLeft = wrap.scrollWidth;
    });
  }

  // Recolhida, a tabela vira uma linha: o nome e os seis indicadores da
  // ultima coluna (o mes, se ja foi extraido).
  function linhaCompacta(tabela, abrir) {
    const linha = document.createElement('div');
    linha.className = 'grupo-compacto';
    const ultima = tela.colunas.length - 1;
    const nome = document.createElement('div');
    nome.className = 'grupo-compacto-nome';
    nome.title = 'Abrir a tabela';
    const rotuloDaColuna = tela.colunas[ultima] ? tela.colunas[ultima].titulo : '';
    nome.innerHTML = `<small>${nomes.singular} · ${escaparHtml(rotuloDaColuna)}</small>`;
    nome.appendChild(document.createTextNode(tabela.rotulo));
    nome.addEventListener('click', abrir);
    const valores = document.createElement('div');
    valores.className = 'grupo-compacto-valores';
    for (const indicador of tabela.linhas) {
      const celula = indicador.celulas[ultima] || {};
      const item = document.createElement('div');
      item.className = 'grupo-compacto-valor';
      const rotulo = document.createElement('span');
      rotulo.textContent = indicador.rotulo;
      item.appendChild(rotulo);
      const valor = document.createElement('span');
      if (celula.texto) {
        valor.className = `indicator-value ${celula.cor || ''}`;
        valor.textContent = celula.texto;
      } else {
        valor.className = 'vazio';
        valor.textContent = celula.nao_se_aplica ? '' : '\u2014';
      }
      item.appendChild(valor);
      valores.appendChild(item);
    }
    linha.append(nome, valores);
    return linha;
  }

  // Barra com o nome de cada um: pula ate a tabela dele.
  function desenharNavegacao() {
    const atalhos = el('atalhos');
    atalhos.innerHTML = '';
    tela.tabelas.forEach((tabela, indice) => {
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'grupo-chip';
      chip.textContent = tabela.rotulo;
      chip.title = `Ir para ${tabela.rotulo}`;
      chip.addEventListener('click', () => irParaGrupo(indice));
      atalhos.appendChild(chip);
    });
  }

  function irParaGrupo(indice) {
    const card = document.getElementById(`${pre}-grupo-${indice}`);
    if (!card) return;
    if (card.classList.contains('recolhido')) card.querySelector('.grupo-alternar').click();
    card.scrollIntoView({ block: 'start', behavior: SEM_ANIMACAO ? 'auto' : 'smooth' });
    reiniciarAnimacao(card, 'grupo-destacado');
  }

  function recolherTodas(recolher) {
    for (const tabela of tela.tabelas) {
      if (recolher) recolhidos.add(tabela.id); else recolhidos.delete(tabela.id);
    }
    el('tabelas').querySelectorAll('.grupo-tabela').forEach((card) => {
      card.classList.toggle('recolhido', recolher);
      const botao = card.querySelector('.grupo-alternar');
      botao.title = recolher ? 'Abrir a tabela' : 'Recolher a tabela';
      botao.setAttribute('aria-expanded', String(!recolher));
    });
  }

  // Resumo: uma tabela so, com os grupos nas linhas e os seis indicadores
  // de um periodo nas colunas. Mesmos textos e cores das tabelas.
  function desenharResumo() {
    const periodos = tela.colunas.map((c, i) => ({ id: String(i), rotulo: `${c.titulo} · ${c.subtitulo}` }));
    const ultima = String(tela.colunas.length - 1);
    if (!periodos.some((p) => p.id === estado.periodoResumo)) estado.periodoResumo = ultima;
    preencherSelect(el('resumo-periodo'), periodos, estado.periodoResumo);
    const indice = Number(estado.periodoResumo);
    const coluna = tela.colunas[indice];
    el('resumo-sub').textContent = `${coluna.titulo} (${coluna.subtitulo}) · ${plural(tela.tabelas.length, nomes.singular.toLowerCase(), nomes.plural)} marcados. Clique no nome para abrir a tabela.`;

    const indicadores = tela.tabelas[0].linhas;
    const cabecalho = el('resumo-cabecalho');
    const corpo = el('resumo-corpo');
    cabecalho.innerHTML = '';
    const canto = document.createElement('th');
    canto.className = 'resumo-canto';
    canto.innerHTML = `<div class="corner-label">${nomes.singular}</div>`;
    const copiarTudo = document.createElement('button');
    copiarTudo.type = 'button';
    copiarTudo.className = 'copy-btn resumo-copiar-tudo';
    copiarTudo.textContent = 'Copiar tabela';
    copiarTudo.title = 'Copia nomes e valores para colar no PowerPoint ou no Excel.';
    copiarTudo.addEventListener('click', () => {
      const linhas = [[{ texto: nomes.singular, alinhamento: 'left', negrito: true },
        ...indicadores.map((i) => ({ texto: i.rotulo, negrito: true }))]];
      corpo.querySelectorAll('tr').forEach((tr, r) => {
        linhas.push([{ texto: tela.tabelas[r].rotulo, alinhamento: 'left' },
          ...indicadores.map((_, c) => valoresDaColuna(c, corpo)[r])]);
      });
      copiarComAviso(copiarTudo, textoParaColar(linhas), tabelaParaColar(linhas),
        `resumo de ${plural(tela.tabelas.length, nomes.singular.toLowerCase(), nomes.plural)} · ${coluna.titulo}`);
    });
    canto.appendChild(copiarTudo);
    cabecalho.appendChild(canto);
    indicadores.forEach((indicador, c) => {
      const th = document.createElement('th');
      th.className = 'resumo-col';
      th.innerHTML = `<div class="col-title">${escaparHtml(indicador.rotulo)}</div><div class="col-subtitle">${escaparHtml(indicador.meta)}</div>`;
      th.appendChild(botaoCopiar(c, `${indicador.rotulo} (${coluna.titulo})`, corpo));
      cabecalho.appendChild(th);
    });

    corpo.innerHTML = '';
    tela.tabelas.forEach((tabela, r) => {
      const tr = document.createElement('tr');
      const nome = document.createElement('th');
      nome.scope = 'row';
      nome.className = 'resumo-nome';
      const botao = document.createElement('button');
      botao.type = 'button';
      botao.textContent = tabela.rotulo;
      botao.title = 'Abrir a tabela deste ' + nomes.singular.toLowerCase();
      botao.addEventListener('click', async () => {
        estado.vis = 'tabelas';
        desenhar();
        requestAnimationFrame(() => irParaGrupo(r));
      });
      nome.appendChild(botao);
      if (dimensao === 'gestor' && !tabela.vinculado) {
        const nota = document.createElement('small');
        nota.textContent = 'sem o mesmo nome no Headcount';
        nome.appendChild(nota);
      }
      tr.appendChild(nome);
      for (const indicador of tabela.linhas) {
        const celula = indicador.celulas[indice] || {};
        const td = document.createElement('td');
        td.className = 'indicator-cell';
        if (celula.nao_se_aplica) {
          td.classList.add('nao-se-aplica');
          if (celula.copia_vazia) td.dataset.copiaVazia = '1';
        } else if (celula.texto) {
          const valor = document.createElement('span');
          valor.className = `indicator-value ${celula.cor || ''}`;
          valor.textContent = celula.texto;
          td.appendChild(valor);
        } else {
          td.classList.add('sem-numero');
          td.textContent = '\u2014';
        }
        tr.appendChild(td);
      }
      corpo.appendChild(tr);
    });
    entrarEmSequencia(corpo);
  }

  el('visualizacao').addEventListener('click', (evento) => {
    const botao = evento.target.closest('.seg-opcao');
    if (!botao || botao.dataset.vis === estado.vis) return;
    estado.vis = botao.dataset.vis;
    if (tela) desenhar();
  });
  window.addEventListener('resize', () => moverDestaque(el('visualizacao')));
  el('resumo-periodo').addEventListener('change', () => {
    estado.periodoResumo = el('resumo-periodo').value;
    desenharResumo();
  });
  el('abrir-todas').addEventListener('click', () => recolherTodas(false));
  el('fechar-todas').addEventListener('click', () => recolherTodas(true));

  el('operacao').addEventListener('change', async () => {
    estado.operacao = el('operacao').value;
    await carregar();
  });
  el('mes').addEventListener('change', async () => {
    estado.mes = el('mes').value;
    await carregar();
  });
  el('todos').addEventListener('click', () => salvarVisiveis(true));
  el('nenhum').addEventListener('click', () => salvarVisiveis(false));
  const extrair = () => irParaExtracao(estado.operacao, tipoWeek);
  el('ir-extrair').addEventListener('click', extrair);
  el('vazio-extrair').addEventListener('click', extrair);
  el('vazio-anterior').addEventListener('click', async (evento) => {
    estado.mes = evento.currentTarget.dataset.mes;
    await carregar();
  });

  return { carregar };
}

const abaGestor = criarAbaDeGrupo('gestor', 'rg');
const abaTurno = criarAbaDeGrupo('turno', 'rt');
