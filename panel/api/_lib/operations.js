// Lista minima das operacoes (so pra popular o dropdown do painel e
// validar o campo "operation" ao criar uma tarefa). As chaves aqui
// precisam bater com as chaves de config/operations.py (raiz do repo),
// que e onde ficam a URL de login, credenciais e parametros do
// relatorio — o agente local e quem le aquele arquivo, nunca o painel.
module.exports = {
  hugo_boss: { label: 'Hugo Boss' },
  hughes: { label: 'Hughes' },
  swa: { label: 'Swa' },
  nike_fisia: { label: 'Nike/Fisia' },
  sumup: { label: 'Sumup' },
  rede: { label: 'Rede' },
  jcb: { label: 'JCB' },
  lego: { label: 'Lego' },
  spacex: { label: 'SpaceX' },
  hpe: { label: 'HPE' },
  armani: { label: 'Armani' },
  abb: { label: 'ABB' },
};
