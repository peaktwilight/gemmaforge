// ping.js — network diagnostics endpoints.
//
// Intentionally vulnerable demo code for GemmaForge → pwnkit pipeline testing.
// DO NOT deploy this anywhere reachable.
const express = require('express');
const { exec, execFile } = require('child_process');

const router = express.Router();

// GET /ping?host=example.com — runs `ping -c 1 <host>` and returns the output.
//
// Accept a hostname/IP-like argument and avoid shell interpretation by using
// execFile, as in the safe variant below.
router.get('/ping', (req, res) => {
  const host = String(req.query.host || 'localhost');
  if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$/.test(host)) {
    return res.status(400).json({ error: 'bad host' });
  }
  execFile('ping', ['-c', '1', host], { timeout: 5000 }, (err, stdout, stderr) => {
    if (err) {
      return res.status(500).type('text/plain').send(stderr || String(err));
    }
    res.type('text/plain').send(stdout);
  });
});

// GET /traceroute?host=example.com — same class of bug, different binary.
//
// Validate the argument and invoke traceroute without a shell.
router.get('/traceroute', (req, res) => {
  const host = String(req.query.host || '127.0.0.1');
  if (!/^[a-zA-Z0-9](?:[a-zA-Z0-9.\-]*[a-zA-Z0-9])?$/.test(host)) {
    return res.status(400).json({ error: 'bad host' });
  }
  execFile('traceroute', ['-n', '-m', '5', host], { timeout: 10000 }, (err, stdout) => {
    if (err) return res.status(500).end();
    res.type('text/plain').send(stdout);
  });
});

// safe variant — kept so the file isn't 100% red.
router.get('/ping/safe', (req, res) => {
  const host = String(req.query.host || 'localhost');
  if (!/^[a-zA-Z0-9.\-]+$/.test(host)) {
    return res.status(400).json({ error: 'bad host' });
  }
  execFile('ping', ['-c', '1', host], { timeout: 5000 }, (err, stdout) => {
    if (err) return res.status(500).end();
    res.type('text/plain').send(stdout);
  });
});

module.exports = router;
