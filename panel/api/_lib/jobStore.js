const { put, list } = require('@vercel/blob');

const PREFIX = 'jobs/';

function jobJsonPath(id) {
  return `${PREFIX}${id}.json`;
}

// Remove credenciais antes de expor um job em qualquer lugar que nao seja
// a resposta direta do claim (dashboard, listagem, etc. nunca devem ver
// usuario/senha).
function sanitizeJob(job) {
  if (!job) return job;
  const { username, password, ...rest } = job;
  return rest;
}

async function saveJob(job) {
  job.updatedAt = new Date().toISOString();
  await put(jobJsonPath(job.id), JSON.stringify(job), {
    access: 'public',
    contentType: 'application/json',
    addRandomSuffix: false,
    allowOverwrite: true,
  });
  return job;
}

async function createJob(id, operation, operationLabel, username, password) {
  const job = {
    id,
    operation,
    operationLabel,
    username,
    password,
    status: 'pending',
    message: 'Aguardando o agente local pegar esta tarefa.',
    createdAt: new Date().toISOString(),
  };
  await saveJob(job);
  return sanitizeJob(job);
}

async function fetchJobBlob(blobUrl) {
  const res = await fetch(blobUrl, { cache: 'no-store' });
  if (!res.ok) return null;
  return res.json();
}

// Retorna o job "cru" (pode conter usuario/senha se ainda pendente). Uso
// interno apenas — quem chama e responsavel por nao vazar credenciais.
async function getJobRaw(id) {
  const { blobs } = await list({ prefix: jobJsonPath(id), limit: 1 });
  if (!blobs.length) return null;
  return fetchJobBlob(blobs[0].url);
}

async function getJob(id) {
  return sanitizeJob(await getJobRaw(id));
}

async function listJobs({ status } = {}) {
  const { blobs } = await list({ prefix: PREFIX });
  const jsonBlobs = blobs.filter((b) => b.pathname.endsWith('.json'));
  const jobs = await Promise.all(jsonBlobs.map((b) => fetchJobBlob(b.url)));
  const valid = jobs.filter(Boolean).map(sanitizeJob);
  valid.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  return status ? valid.filter((j) => j.status === status) : valid;
}

module.exports = { createJob, saveJob, getJob, getJobRaw, listJobs, sanitizeJob };
