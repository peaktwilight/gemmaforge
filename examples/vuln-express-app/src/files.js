// files.js — static file download endpoints.
//
// Intentionally vulnerable demo code for GemmaForge → pwnkit pipeline testing.
// DO NOT deploy this anywhere reachable.
const express = require('express');
const fs = require('fs');
const path = require('path');

const router = express.Router();

const DATA_ROOT = process.env.DATA_ROOT || '/var/data';

// safe helper — restricts a name to a single non-traversing segment.
// Not used by the vulnerable routes below, on purpose.
function safeJoin(root, name) {
  const resolved = path.resolve(root, name);
  if (!resolved.startsWith(path.resolve(root) + path.sep)) {
    throw new Error('path escapes root');
  }
  return resolved;
}

// GET /files?name=foo.txt — read a file from the data dir.
//
// BUG (CWE-22): the name query param is path.join'd onto DATA_ROOT with no
// check that the result stays inside DATA_ROOT. A request like
// ?name=../../etc/passwd resolves to /etc/passwd and is happily served.
router.get('/files', (req, res) => {
  const name = req.query.name || 'index.txt';
  const target = path.join(DATA_ROOT, name);
  fs.readFile(target, 'utf8', (err, data) => {
    if (err) {
      console.error('read failed', err);
      return res.status(404).json({ error: 'not found' });
    }
    res.type('text/plain').send(data);
  });
});

// GET /files/raw/:name — alternative download route.
//
// BUG (CWE-22): same class of issue, this time using string concatenation
// instead of path.join. Equally bypassable with "../" segments.
router.get('/files/raw/:name', (req, res) => {
  const filePath = DATA_ROOT + '/' + req.params.name;
  fs.readFile(filePath, (err, buf) => {
    if (err) return res.status(404).end();
    res.send(buf);
  });
});

// safe variant — kept here so the file isn't 100% vulnerable code.
router.get('/files/safe/:name', (req, res) => {
  try {
    const target = safeJoin(DATA_ROOT, req.params.name);
    fs.readFile(target, (err, buf) => {
      if (err) return res.status(404).end();
      res.send(buf);
    });
  } catch (e) {
    res.status(400).json({ error: 'bad path' });
  }
});

module.exports = router;
