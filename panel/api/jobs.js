const crypto = require('crypto');
const { requireAuth } = require('./_lib/auth');
const { createJob, listJobs } = require('./_lib/jobStore');
const OPERATIONS = require('./_lib/operations');

module.exports = async (req, res) => {
  if (!requireAuth(req, res)) return;

  if (req.method === 'GET') {
    const status = typeof req.query.status === 'string' ? req.query.status : undefined;
    const jobs = await listJobs({ status });
    return res.status(200).json({ jobs });
  }

  if (req.method === 'POST') {
    const { operation } = req.body || {};
    if (!operation || !OPERATIONS[operation]) {
      return res.status(400).json({ error: 'Operacao invalida.' });
    }

    const id = crypto.randomUUID();
    const job = await createJob(id, operation, OPERATIONS[operation].label);
    return res.status(201).json(job);
  }

  res.status(405).json({ error: 'Method not allowed' });
};
