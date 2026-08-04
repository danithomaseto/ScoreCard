const { requireAuth } = require('../../_lib/auth');
const { getJob, saveJob } = require('../../_lib/jobStore');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (!requireAuth(req, res)) return;

  const { id } = req.query;
  const job = await getJob(id);
  if (!job) return res.status(404).json({ error: 'Job nao encontrado.' });

  if (job.status !== 'pending') {
    return res.status(409).json({ error: `Job ja esta com status '${job.status}'.` });
  }

  job.status = 'running';
  job.message = 'Agente local esta executando a automacao...';
  await saveJob(job);

  res.status(200).json(job);
};
