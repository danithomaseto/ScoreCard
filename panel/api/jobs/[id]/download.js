const { requireAuth } = require('../../_lib/auth');
const { getJob, authHeaders } = require('../../_lib/jobStore');

module.exports = async (req, res) => {
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });
  if (!requireAuth(req, res)) return;

  try {
    const { id } = req.query;
    const job = await getJob(id);
    if (!job || !job.fileUrl) {
      return res.status(404).json({ error: 'Arquivo nao encontrado para esta tarefa.' });
    }

    const blobRes = await fetch(job.fileUrl, { headers: authHeaders() });
    if (!blobRes.ok) {
      return res.status(502).json({ error: 'Falha ao buscar o arquivo no armazenamento (Blob).' });
    }

    const buffer = Buffer.from(await blobRes.arrayBuffer());
    const filename = job.fileName || 'relatorio.xlsx';

    res.setHeader(
      'Content-Type',
      blobRes.headers.get('content-type') || 'application/octet-stream'
    );
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    return res.status(200).send(buffer);
  } catch (err) {
    console.error('Falha em /api/jobs/[id]/download:', err);
    return res.status(500).json({ error: `Falha ao baixar o arquivo. Detalhe: ${err.message}` });
  }
};
