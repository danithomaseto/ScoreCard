// Cadastro completo das operacoes (URL de login, credenciais e parametros
// do relatorio). Fica só no agente local — nunca é enviado ao painel Vercel.
//
// Para adicionar uma nova operacao:
// 1. Adicione uma entrada aqui com loginUrl e os nomes das variaveis de
//    usuario/senha.
// 2. Adicione essas variaveis no .env do agente (e no .env.example).
// 3. Crie agent/automation/<operacao>.js seguindo o padrao de hugoBoss.js.
// 4. Registre o runner em agent/agent.js (objeto RUNNERS).
// 5. Adicione a operacao tambem em api/_lib/operations.js (so label),
//    para aparecer no dropdown do painel.
module.exports = {
  hugo_boss: {
    label: 'Hugo Boss',
    loginUrl: 'https://czcholspc003138.prg-dc.dhl.com:11217/rp/login',
    usernameEnv: 'HUGO_BOSS_USERNAME',
    passwordEnv: 'HUGO_BOSS_PASSWORD',
    reportName: 'rptLMUserSummaryRaw',
    dateRangeOption: 'Last Week',
    groupByOption: 'User ID',
    exportFormat: 'EXCEL',
  },
};
