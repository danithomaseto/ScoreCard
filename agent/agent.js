require('dotenv').config();

const fs = require('fs');
const hugoBoss = require('./automation/hugoBoss');

const RUNNERS = {
  hugo_boss: hugoBoss,
};

const DASHBOARD_URL = (process.env.DASHBOARD_URL || '').replace(/\/+$/, '');
const APP_TOKEN = process.env.APP_TOKEN;
const POLL_INTERVAL_MS = Number(process.env.POLL_INTERVAL_SECONDS || 5) * 1000;

if (!DASHBOARD_URL || !APP_TOKEN) {
  console.error('Configure DASHBOARD_URL e APP_TOKEN no arquivo .env do agente (veja .env.example).');
  process.exit(1);
}

function authHeaders(extra = {}) {
  return Object.assign({ Authorization: `Bearer ${APP_TOKEN}` }, extra);
}

async function fetchPendingJobs() {
  const res = await fetch(`${DASHBOARD_URL}/api/jobs?status=pending`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    throw new Error(`Falha ao consultar tarefas pendentes (HTTP ${res.status}).`);
  }
  const data = await res.json();
  return data.jobs || [];
}

async function claimJob(id) {
  const res = await fetch(`${DASHBOARD_URL}/api/jobs/${id}/claim`, {
    method: 'POST',
    headers: authHeaders(),
  });
  return res.ok;
}

async function reportFailure(id, message) {
  await fetch(`${DASHBOARD_URL}/api/jobs/${id}/complete`, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ status: 'failed', message }),
  });
}

async function uploadResult(id, filePath, fileName) {
  const fileBuffer = fs.readFileSync(filePath);
  const url = `${DASHBOARD_URL}/api/jobs/${id}/complete?filename=${encodeURIComponent(fileName)}`;
  const res = await fetch(url, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/octet-stream' }),
    body: fileBuffer,
  });
  if (!res.ok) {
    throw new Error(`Falha ao enviar o relatorio para o painel (HTTP ${res.status}).`);
  }
}

async function processJob(job) {
  const runner = RUNNERS[job.operation];
  if (!runner) {
    console.log(`[${job.id}] Operacao '${job.operation}' nao implementada neste agente.`);
    await reportFailure(job.id, `Operacao '${job.operation}' nao implementada neste agente.`);
    return;
  }

  console.log(`[${job.id}] Reservando tarefa '${job.operation}'...`);
  const claimed = await claimJob(job.id);
  if (!claimed) {
    console.log(`[${job.id}] Nao foi possivel reservar a tarefa (outro agente pode ja ter pegado).`);
    return;
  }

  console.log(`[${job.id}] Executando automacao...`);
  const result = await runner.run({ headless: true });

  if (!result.success) {
    console.log(`[${job.id}] Falhou: ${result.message}`);
    await reportFailure(job.id, result.message);
    return;
  }

  console.log(`[${job.id}] Automacao concluida, enviando arquivo para o painel...`);
  await uploadResult(job.id, result.filePath, result.fileName);
  console.log(`[${job.id}] Concluido.`);
}

async function pollOnce() {
  const jobs = await fetchPendingJobs();
  for (const job of jobs) {
    try {
      await processJob(job);
    } catch (err) {
      console.error(`[${job.id}] Erro inesperado: ${err.message}`);
      await reportFailure(job.id, err.message).catch(() => {});
    }
  }
}

async function main() {
  console.log(`Agente do Score Card rodando. Painel: ${DASHBOARD_URL}`);
  console.log(`Verificando novas tarefas a cada ${POLL_INTERVAL_MS / 1000}s. Ctrl+C para parar.`);

  for (;;) {
    try {
      await pollOnce();
    } catch (err) {
      console.error('Erro ao consultar o painel:', err.message);
    }
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
  }
}

main();
