// ---------------------------------------------------------------
// Perguntas no visual do app (no lugar das caixas do Windows)
// ---------------------------------------------------------------

const ICONES_DO_DIALOGO = {
  erro: '<svg viewBox="0 0 24 24"><rect x="4" y="11" width="16" height="10" rx="2"></rect><path d="M8 11V7a4 4 0 0 1 8 0v4"></path></svg>',
  pasta: '<svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path></svg>',
  aviso: '<svg viewBox="0 0 24 24"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>',
};

// Resolve com o "valor" do botao escolhido; Esc ou clique fora, com null.
function perguntar({ titulo, texto, icone = 'aviso', botoes }) {
  const fundo = document.getElementById('dialogo');
  const area = document.getElementById('dialogo-botoes');
  const focoAntes = document.activeElement;
  document.getElementById('dialogo-titulo').textContent = titulo;
  document.getElementById('dialogo-texto').textContent = texto;
  const caixaDoIcone = document.getElementById('dialogo-icone');
  caixaDoIcone.innerHTML = ICONES_DO_DIALOGO[icone] || ICONES_DO_DIALOGO.aviso;
  caixaDoIcone.className = `dialogo-icone ${icone === 'erro' ? 'erro' : ''}`;
  area.innerHTML = '';
  return new Promise((resolver) => {
    const fechar = (valor) => {
      fundo.hidden = true;
      document.removeEventListener('keydown', teclas, true);
      if (focoAntes && focoAntes.focus) focoAntes.focus();
      resolver(valor);
    };
    const teclas = (evento) => {
      if (evento.key === 'Escape') {
        evento.preventDefault();
        evento.stopImmediatePropagation();
        fechar(null);
      } else if (evento.key === 'Tab') {
        // O foco fica dentro da janela.
        const focaveis = [...area.querySelectorAll('button')];
        const i = focaveis.indexOf(document.activeElement);
        evento.preventDefault();
        const proximo = evento.shiftKey ? (i <= 0 ? focaveis.length - 1 : i - 1) : (i + 1) % focaveis.length;
        focaveis[proximo].focus();
      }
    };
    let principal = null;
    for (const botao of botoes) {
      const el = document.createElement('button');
      el.type = 'button';
      el.textContent = botao.rotulo;
      if (!botao.principal) el.className = 'secondary';
      el.addEventListener('click', () => fechar(botao.valor));
      area.appendChild(el);
      if (botao.principal) principal = el;
    }
    fundo.onclick = (evento) => { if (evento.target === fundo) fechar(null); };
    document.addEventListener('keydown', teclas, true);
    fundo.hidden = false;
    (principal || area.lastElementChild).focus();
  });
}

// ---------------------------------------------------------------
// Extracao em andamento, vista de qualquer aba
// ---------------------------------------------------------------
// Um selo na barra amarela mostra a extracao que esta rodando (unica,
// fila ou horas indiretas) quando se esta em outra aba; clicar nele volta
// para a tela de onde ela saiu. So uma extracao roda por vez.

const seloExtracao = document.getElementById('topbar-extracao');
const ROTULO_DA_ORIGEM = { extract: 'Extrair Dados', multi: 'Extrair Múltiplos', indiretas: 'Horas Indiretas' };
const extracaoAtual = { ativa: false, origem: null, rotulo: '', texto: '', fracao: 0, desfecho: null, timer: null };

function paginaAberta() {
  return (document.querySelector('.page:not([hidden])')?.id || '').replace('page-', '');
}

function outraExtracaoRodando() {
  if (!extracaoAtual.ativa) return false;
  avisar('Já tem uma extração rodando', 'erro',
    `${extracaoAtual.rotulo} (${ROTULO_DA_ORIGEM[extracaoAtual.origem]}). Espere ela terminar para começar outra.`);
  return true;
}

function desenharSelo() {
  const e = extracaoAtual;
  const visivel = (e.ativa || e.desfecho) && paginaAberta() !== e.origem;
  seloExtracao.hidden = !visivel;
  if (!visivel) return;
  seloExtracao.classList.remove('ok', 'aviso', 'erro');
  if (e.desfecho) seloExtracao.classList.add({ success: 'ok', warning: 'aviso', error: 'erro' }[e.desfecho.classe] || 'ok');
  document.getElementById('topbar-extracao-texto').textContent = e.ativa
    ? `Extraindo · ${e.texto || e.rotulo}`
    : `${e.desfecho.rotulo} · ${e.rotulo}`;
  document.getElementById('topbar-extracao-progresso').style.width = `${Math.round(e.fracao * 100)}%`;
  seloExtracao.title = `${e.ativa ? 'Extração em andamento' : 'Última extração'}: ${e.rotulo}. Clique para abrir ${ROTULO_DA_ORIGEM[e.origem]}.`;
}

function extracaoComecou(origem, rotulo) {
  clearTimeout(extracaoAtual.timer);
  Object.assign(extracaoAtual, { ativa: true, origem, rotulo, texto: '', fracao: 0, desfecho: null });
  desenharSelo();
  desenharRodape();
}

function extracaoAndou(texto, fracao) {
  if (!extracaoAtual.ativa) return;
  extracaoAtual.texto = extracaoAtual.origem === 'multi' ? texto : `${extracaoAtual.rotulo} · ${texto}`;
  extracaoAtual.fracao = Math.max(0, Math.min(1, fracao));
  desenharSelo();
  desenharRodape();
}

function extracaoTerminou(classe, rotulo) {
  const e = extracaoAtual;
  if (!e.ativa) return;
  e.ativa = false;
  e.fracao = 1;
  e.desfecho = { classe, rotulo };
  // Quem esta em outra aba fica sabendo pelo aviso no canto.
  if (paginaAberta() !== e.origem) {
    avisar(`${rotulo}: ${e.rotulo}`, classe === 'error' ? 'erro' : 'ok',
      `Clique no selo da barra amarela para abrir ${ROTULO_DA_ORIGEM[e.origem]}.`);
  }
  desenharSelo();
  e.timer = setTimeout(() => { e.desfecho = null; desenharSelo(); }, 10000);
  atualizarRodape();
}

seloExtracao.addEventListener('click', () => {
  if (extracaoAtual.origem) showPage(extracaoAtual.origem);
});

// ---------------------------------------------------------------
// Rodape do menu: a ultima extracao, ha quanto tempo
// ---------------------------------------------------------------

function haQuanto(iso) {
  const minutos = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (!Number.isFinite(minutos)) return '';
  if (minutos < 1) return 'agora há pouco';
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `há ${horas} h`;
  const dias = Math.floor(horas / 24);
  if (dias === 1) return 'ontem';
  if (dias < 7) return `há ${dias} dias`;
  return `em ${new Date(iso).toLocaleDateString('pt-BR')}`;
}

async function atualizarRodape() {
  try {
    historicoCompleto = await pywebview.api.get_report_history();
  } catch (erro) {
    return;
  }
  desenharRodape();
}

function desenharRodape() {
  const ponto = document.getElementById('status-dot');
  const titulo = document.getElementById('status-titulo');
  const sub = document.getElementById('status-sub');
  ponto.classList.remove('extraindo', 'aviso', 'erro');
  if (extracaoAtual.ativa) {
    ponto.classList.add('extraindo');
    titulo.textContent = 'Extraindo…';
    sub.textContent = extracaoAtual.texto || extracaoAtual.rotulo;
  } else {
    const ultima = historicoCompleto[0];
    titulo.textContent = 'Pronto para extrair';
    if (!ultima) {
      sub.textContent = 'Nenhuma extração ainda';
    } else {
      const desfecho = desfechoDe(ultima);
      if (desfecho.classe === 'warning') ponto.classList.add('aviso');
      if (desfecho.classe === 'error') ponto.classList.add('erro');
      const resultado = desfecho.classe === 'success' ? '' : ` · ${desfecho.rotulo.toLowerCase()}`;
      sub.textContent = `Última extração ${haQuanto(ultima.timestamp)} · ${ultima.operation}${resultado}`;
    }
  }
  // Com o menu recolhido so o ponto aparece: o texto vai no "title".
  document.getElementById('sidebar-status').title = `${titulo.textContent} — ${sub.textContent}`;
}
// O "há 5 min" anda sozinho.
setInterval(() => { if (!appView.hidden && !janelaEscondida()) desenharRodape(); }, 60000);
document.addEventListener('janelavoltou', () => { if (!appView.hidden) desenharRodape(); });
