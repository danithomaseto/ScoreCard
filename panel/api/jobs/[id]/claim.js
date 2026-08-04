const { requireAuth } = require('../../_lib/auth');
const { getJobRaw, saveJob } = require('../../_lib/jobStore');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (!requireAuth(req, res)) return;

  try {
    const { id } = req.query;
    const job = await getJobRaw(id);
    if (!job) return res.status(404).json({ error: 'Job nao encontrado.' });

    if (job.status !== 'pending') {
      return res.status(409).json({ error: `Job ja esta com status '${job.status}'.` });
    }

    const { username, password } = job;

    // Apaga as credenciais do que fica salvo — a partir daqui, nenhuma
    // outra resposta (listagem, historico) volta a expor usuario/senha.
    const scrubbed = { ...job };
    delete scrubbed.username;
    delete scrubbed.password;
    scrubbed.status = 'running';
    scrubbed.message = 'Agente local esta executando a automacao...';
    await saveJob(scrubbed);

    // Unica resposta que carrega as credenciais: vai direto pro agente que
    // reservou a tarefa.
    return res.status(200).json({ ...scrubbed, username, password });
  } catch (err) {
    console.error('Falha em /api/jobs/[id]/claim:', err);
    return res.status(500).json({
      error: `Falha ao acessar o armazenamento (Blob). Verifique se o Blob Store esta conectado ao projeto no Vercel. Detalhe: ${err.message}`,
    });
  }
};
