// ---------------------------------------------------------------
// Configuracoes: saude do sistema, backup e aviso de versao nova
// ---------------------------------------------------------------

function itemDeSaude(nivel, titulo, texto, detalhe) {
  const item = document.createElement('div');
  item.className = `saude-item ${nivel}`;
  const ponto = document.createElement('span');
  ponto.className = 'saude-ponto';
  ponto.setAttribute('aria-hidden', 'true');
  const corpo = document.createElement('div');
  const t = document.createElement('div');
  t.className = 'saude-titulo';
  t.textContent = titulo;
  const v = document.createElement('div');
  v.className = 'saude-texto';
  v.textContent = texto;
  corpo.append(t, v);
  if (detalhe) {
    const d = document.createElement('div');
    d.className = 'saude-detalhe';
    d.textContent = detalhe;
    corpo.appendChild(d);
  }
  item.append(ponto, corpo);
  return item;
}

async function carregarSaude() {
  const lista = document.getElementById('saude-lista');
  const botao = document.getElementById('saude-conferir');
  botao.disabled = true;
  if (!lista.children.length) lista.innerHTML = '<div class="ind-esqueleto saude-esqueleto"></div>';
  let saude;
  try {
    saude = await pywebview.api.get_saude();
  } catch (erro) {
    registrarErro('saúde do sistema', erro);
    botao.disabled = false;
    return;
  }
  botao.disabled = false;
  lista.innerHTML = '';

  const servidores = saude.servidores || [];
  const ok = servidores.filter((x) => x.ok).length;
  const foraDoAr = servidores.filter((x) => !x.ok).map((x) => x.operacoes.join(', '));
  lista.appendChild(itemDeSaude(
    !servidores.length || ok === servidores.length ? 'ok' : (ok ? 'alerta' : 'erro'),
    'VPN e servidores',
    servidores.length ? `${ok} de ${servidores.length} servidores respondem` : 'Nenhum servidor para conferir',
    foraDoAr.length ? `Sem resposta: ${foraDoAr.join(' · ')}` : ''));

  const p = saude.pasta;
  let nivelPasta = 'ok';
  let textoPasta = 'Existe e dá para gravar';
  if (!p.configurada) { nivelPasta = 'erro'; textoPasta = 'Não configurada'; }
  else if (!p.existe) { nivelPasta = 'erro'; textoPasta = 'A pasta não existe mais'; }
  else if (!p.gravavel) { nivelPasta = 'erro'; textoPasta = 'Sem permissão para gravar'; }
  lista.appendChild(itemDeSaude(nivelPasta, 'Pasta do SharePoint',
    `${textoPasta}${p.existe ? (p.onedrive ? ' · no OneDrive' : ' · fora do OneDrive') : ''}`, p.caminho || ''));

  lista.appendChild(itemDeSaude(p.relatorios ? 'ok' : 'alerta', 'Relatórios na pasta',
    p.relatorios ? `${p.relatorios} relatório(s) · mais novo ${p.mais_novo.texto} (${p.mais_novo.operacao} · ${p.mais_novo.tipo})`
      : 'Nenhum relatório ainda',
    p.so_na_nuvem ? `${p.so_na_nuvem} só na nuvem: o OneDrive baixa quando o app lê` : ''));

  const naoLidos = saude.leitura.nao_lidos || [];
  lista.appendChild(itemDeSaude(naoLidos.length ? 'alerta' : 'ok', 'Leitura da pasta',
    `${saude.leitura.lidos} lido(s)${naoLidos.length ? ` · ${naoLidos.length} não lido(s), veja abaixo` : ''}`,
    sp.hora ? `Última leitura às ${sp.hora}` : ''));

  const nav = saude.navegador;
  lista.appendChild(itemDeSaude(nav ? 'ok' : 'erro', 'Navegador da automação',
    nav ? nav.nome : 'Nenhum encontrado: instale ou repare o Microsoft Edge',
    nav ? (nav.reserva.length ? `Reserva: ${nav.reserva.join(', ')}` : 'Sem reserva') : ''));

  const v = saude.versao;
  lista.appendChild(itemDeSaude(v.nova ? 'alerta' : 'ok', 'Versão do app',
    v.nova ? `${v.versao} · a ${v.nova} está na pasta do SharePoint` : `${v.versao}${v.publicada ? ' · a mais nova publicada' : ''}`,
    v.build ? `Build ${v.build}` : ''));

  const d = saude.dados;
  lista.appendChild(itemDeSaude(d.versao >= d.atual ? 'ok' : 'alerta', 'Versão dos dados',
    d.versao >= d.atual ? `Em dia (versão ${d.versao})` : `Versão ${d.versao}, falta chegar na ${d.atual}`, ''));

  const l = saude.lancamentos;
  lista.appendChild(itemDeSaude(l.erros.length ? 'alerta' : 'ok', 'Headcount e Coverage compartilhados',
    l.operacoes ? `${l.operacoes} operação(ões) na pasta · último lançamento gravado ${l.gravado}` : 'Nenhum lançamento na pasta ainda',
    l.erros.length ? `Não deu para juntar: ${l.erros.join(', ')} (tenta de novo na próxima leitura)`
      : (l.juntado ? `Juntado com a pasta às ${l.juntado}` : '')));

  lista.appendChild(itemDeSaude(saude.backup ? 'ok' : 'alerta', 'Backup dos dados',
    saude.backup ? `Último em ${saude.backup.texto} · ${saude.backup.arquivos} arquivo(s)` : 'Nenhum backup ainda', ''));

  const area = document.getElementById('saude-nao-lidos');
  const corpo = document.getElementById('saude-nao-lidos-corpo');
  corpo.innerHTML = '';
  for (const item of naoLidos) {
    const tr = document.createElement('tr');
    for (const texto of [item.operacao_rotulo, item.tipo_rotulo, item.nome, item.motivo]) {
      const td = document.createElement('td');
      td.textContent = texto;
      tr.appendChild(td);
    }
    corpo.appendChild(tr);
  }
  area.hidden = !naoLidos.length;
}

document.getElementById('saude-conferir').addEventListener('click', carregarSaude);
document.getElementById('saude-reler').addEventListener('click', async (evento) => {
  const sim = await perguntar({
    titulo: 'Ler a pasta do zero?',
    texto: 'O app esquece o que já leu e calcula todos os relatórios da pasta do SharePoint de novo.\n'
      + 'Pode levar alguns segundos. Os lançamentos digitados não mudam.',
    botoes: [{ rotulo: 'Cancelar', valor: false }, { rotulo: 'Ler do zero', valor: true, principal: true }],
  });
  if (!sim) return;
  await comCarregando(evento.currentTarget, async () => {
    const r = await pywebview.api.reler_sharepoint();
    if (r.ocupado) {
      avisar('Espere a extração terminar', 'erro', 'A leitura do zero fica para depois dela.');
      return;
    }
    const lidos = (r.atualizados || []).reduce((total, a) => total + a.arquivos, 0);
    avisar('Pasta lida do zero', 'ok', `${lidos} relatório(s) calculado(s)`);
    await carregarSaude();
  });
});

async function carregarBackups(lista) {
  const ul = document.getElementById('backup-lista');
  const backups = lista || (await pywebview.api.get_backups()).backups || [];
  ul.innerHTML = '';
  if (!backups.length) {
    const li = document.createElement('li');
    li.className = 'backup-vazio';
    li.textContent = 'Nenhum backup ainda: o primeiro é feito na próxima abertura do app (ou agora, no botão acima).';
    ul.appendChild(li);
    return;
  }
  for (const item of backups) {
    const li = document.createElement('li');
    li.className = 'backup-item';
    const texto = document.createElement('span');
    texto.innerHTML = `<strong></strong> <span class="backup-hora"></span>`;
    texto.querySelector('strong').textContent = item.dia;
    texto.querySelector('.backup-hora').textContent = item.antes_de_restaurar
      ? `${item.hora} · antes de uma restauração` : `${item.hora} · ${item.arquivos} arquivo(s)`;
    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'secondary acao';
    botao.textContent = 'Restaurar';
    botao.addEventListener('click', () => restaurarBackup(item));
    li.append(texto, botao);
    ul.appendChild(li);
  }
}

async function restaurarBackup(item) {
  const sim = await perguntar({
    titulo: `Restaurar o backup de ${item.dia}?`,
    texto: 'Os dados deste computador voltam a ser os desse dia (Headcount, Coverage, indicadores, histórico e configurações).\n'
      + 'Antes, o estado de agora é guardado como um backup, para dar para voltar.',
    botoes: [{ rotulo: 'Cancelar', valor: false }, { rotulo: 'Restaurar', valor: true, principal: true }],
  });
  if (!sim) return;
  const r = await pywebview.api.restaurar_backup(item.id);
  if (!r.success) {
    avisar('Não deu para restaurar', 'erro', r.message);
    return;
  }
  avisar(`Backup de ${item.dia} restaurado`, 'ok', `${r.restaurados} arquivo(s). O estado anterior ficou guardado.`);
  await carregarBackups(r.backups);
  await carregarPreferencias();
  carregarSaude();
}

document.getElementById('backup-agora').addEventListener('click', async (evento) => {
  await comCarregando(evento.currentTarget, async () => {
    const r = await pywebview.api.fazer_backup();
    if (!r.success) {
      avisar('Backup não feito', 'erro', r.message);
      return;
    }
    avisar('Backup feito', 'ok', 'Guardado na pasta de dados do app.');
    await carregarBackups(r.backups);
  });
});

// Versao nova publicada na pasta do SharePoint: aviso no topo, ate fechar.
async function conferirVersaoNova() {
  let r;
  try {
    r = await pywebview.api.verificar_versao();
  } catch (erro) {
    return;
  }
  const aviso = document.getElementById('aviso-versao');
  if (!r || !r.nova || aviso.dataset.fechado === r.nova) return;
  document.getElementById('aviso-versao-texto').textContent =
    `Há uma versão nova do Score Card (${r.nova}) na pasta do SharePoint. Você está na ${r.atual}: `
    + 'use a nova, as antigas apagam o histórico da pasta.';
  aviso.dataset.versao = r.nova;
  aviso.hidden = false;
}
document.getElementById('aviso-versao-abrir').addEventListener('click', async () => {
  const r = await pywebview.api.abrir_pasta_da_versao();
  if (r && !r.success) avisar('Não deu para abrir a pasta', 'erro', r.message);
});
document.getElementById('aviso-versao-fechar').addEventListener('click', () => {
  const aviso = document.getElementById('aviso-versao');
  aviso.dataset.fechado = aviso.dataset.versao || '';
  aviso.hidden = true;
});
