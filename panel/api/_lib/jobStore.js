const { put, list } = require('@vercel/blob');

const PREFIX = 'jobs/';

// Blob Stores criados no modo novo do Vercel (OIDC) nao emitem mais um
// BLOB_READ_WRITE_TOKEN classico — em vez disso, cada chamada precisa
// informar o storeId explicitamente (a autenticacao acontece sozinha,
// via identidade do proprio deployment na Vercel). Configuramos o ID em
// BLOB_STORE_ID (variavel nossa, estavel) em vez de depender do nome
// gerado automaticamente pela Vercel (que muda conforme o nome do
// Store). Projetos que ainda usam o token classico simplesmente ignoram
// isso, sem problema.
function blobOptions(extra = {}) {
  const options = { ...extra };
  if (process.env.BLOB_STORE_ID) {
    options.storeId = process.env.BLOB_STORE_ID;
  }
  return options;
}

// Contas mais novas do Vercel so oferecem Blob Store no modo "Private"
// (nao existe mais opcao publica). Isso significa que mesmo ler o
// conteudo de um blob (nao so escrever) exige autenticacao — por isso
// toda leitura interna passa o token como Bearer.
function authHeaders() {
  return process.env.BLOB_READ_WRITE_TOKEN
    ? { Authorization: `Bearer ${process.env.BLOB_READ_WRITE_TOKEN}` }
    : {};
}

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
  await put(
    jobJsonPath(job.id),
    JSON.stringify(job),
    blobOptions({
      access: 'private',
      contentType: 'application/json',
      addRandomSuffix: false,
      allowOverwrite: true,
    })
  );
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
  const res = await fetch(blobUrl, { cache: 'no-store', headers: authHeaders() });
  if (!res.ok) return null;
  return res.json();
}

// Retorna o job "cru" (pode conter usuario/senha se ainda pendente). Uso
// interno apenas — quem chama e responsavel por nao vazar credenciais.
async function getJobRaw(id) {
  const { blobs } = await list(blobOptions({ prefix: jobJsonPath(id), limit: 1 }));
  if (!blobs.length) return null;
  return fetchJobBlob(blobs[0].url);
}

async function getJob(id) {
  return sanitizeJob(await getJobRaw(id));
}

async function listJobs({ status } = {}) {
  const { blobs } = await list(blobOptions({ prefix: PREFIX }));
  const jsonBlobs = blobs.filter((b) => b.pathname.endsWith('.json'));
  const jobs = await Promise.all(jsonBlobs.map((b) => fetchJobBlob(b.url)));
  const valid = jobs.filter(Boolean).map(sanitizeJob);
  valid.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
  return status ? valid.filter((j) => j.status === status) : valid;
}

module.exports = {
  createJob,
  saveJob,
  getJob,
  getJobRaw,
  listJobs,
  sanitizeJob,
  blobOptions,
  authHeaders,
};
