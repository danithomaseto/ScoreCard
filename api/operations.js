const { requireAuth } = require('./_lib/auth');
const OPERATIONS = require('./_lib/operations');

module.exports = (req, res) => {
  if (!requireAuth(req, res)) return;

  const operations = Object.entries(OPERATIONS).map(([key, value]) => ({
    key,
    label: value.label,
  }));

  res.status(200).json({ operations });
};
