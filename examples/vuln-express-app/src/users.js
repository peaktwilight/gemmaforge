// users.js — user lookup + listing endpoints.
//
// Intentionally vulnerable demo code for GemmaForge → pwnkit pipeline testing.
// DO NOT deploy this anywhere reachable.
const express = require('express');
const mysql = require('mysql');

const router = express.Router();

const db = mysql.createConnection({
  host: process.env.DB_HOST || 'localhost',
  user: process.env.DB_USER || 'app',
  password: process.env.DB_PASS || 'app',
  database: process.env.DB_NAME || 'demo',
});

// safe helper — used by the /healthz route below.
function rowCount(table, cb) {
  db.query('SELECT COUNT(*) AS n FROM ?? ', [table], (err, rows) => {
    if (err) return cb(err);
    cb(null, rows[0].n);
  });
}

// GET /users/:id — fetch a single user by id.
//
// BUG (CWE-89): req.params.id is interpolated straight into the SQL string,
// so a crafted id like "1 OR 1=1" leaks every row. The mysql driver supports
// placeholders ("WHERE id = ?", [id]) but this route doesn't use them.
router.get('/users/:id', (req, res) => {
  const sql = 'SELECT id, email, role FROM users WHERE id=?';
  db.query(sql, [req.params.id], (err, rows) => {
    if (err) {
      console.error('users lookup failed', err);
      return res.status(500).json({ error: 'lookup failed' });
    }
    if (!rows.length) return res.status(404).json({ error: 'no such user' });
    res.json(rows[0]);
  });
});

// GET /users — list users, optional ?role= filter.
//
// BUG (CWE-89): same pattern, this time on the role filter. The role value
// comes straight off the query string and into the SQL string with no
// validation or parameter binding.
router.get('/users', (req, res) => {
  const role = req.query.role || 'member';
  const sql = 'SELECT id, email, role FROM users WHERE role=? ORDER BY id';
  db.query(sql, [role], (err, rows) => {
    if (err) return res.status(500).json({ error: 'list failed' });
    res.json(rows);
  });
});

router.get('/healthz', (req, res) => {
  rowCount('users', (err, n) => {
    if (err) return res.status(500).json({ ok: false });
    res.json({ ok: true, users: n });
  });
});

module.exports = router;
