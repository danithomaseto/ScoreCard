function requireAuth(req, res) {
  const expected = process.env.APP_TOKEN;
  if (!expected) {
    res.status(500).json({ error: 'APP_TOKEN nao configurado no servidor.' });
    return false;
  }

  const header = req.headers['authorization'] || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;

  if (!token || token !== expected) {
    res.status(401).json({ error: 'Nao autorizado.' });
    return false;
  }

  return true;
}

module.exports = { requireAuth };
