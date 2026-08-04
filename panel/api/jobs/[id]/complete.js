const { put } = require('@vercel/blob');
const { requireAuth } = require('../../_lib/auth');
const { getJob, saveJob } = require('../../_lib/jobStore');

module.exports = async (req, res) => {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  if (!requireAuth(req, res)) return;

  try {
    const { id } = req.query;
    const job = await getJob(id);
    if (!job) return res.status(404).json({ error: 'Job nao encontrado.' });

    const contentType = req.headers['content-type'] || '';

    if (contentType.includes('application/json')) {
      const { status, message } = req.body || {};
      job.status = status === 'failed' ? 'failed' : 'done';
      job.message = message || (job.status === 'failed' ? 'Falha na automacao.' : 'Concluido.');
      await saveJob(job);
      return res.status(200).json(job);
    }

    const filename = typeof req.query.filename === 'string' ? req.query.filename : 'relatorio.xlsx';
    const fileBuffer = req.body;

    if (!Buffer.isBuffer(fileBuffer) || fileBuffer.length === 0) {
      return res.status(400).json({ error: 'Arquivo vazio ou invalido.' });
    }

    const blob = await put(`jobs/${id}-${filename}`, fileBuffer, {
      access: 'public',
      addRandomSuffix: true,
    });

    job.status = 'done';
    job.message = 'Relatorio pronto para download.';
    job.fileUrl = blob.url;
    job.fileName = filename;
    await saveJob(job);

    return res.status(200).json(job);
  } catch (err) {
    console.error('Falha em /api/jobs/[id]/complete:', err);
    return res.status(500).json({
      error: `Falha ao acessar o armazenamento (Blob). Verifique se o Blob Store esta conectado ao projeto no Vercel. Detalhe: ${err.message}`,
    });
  }
};
