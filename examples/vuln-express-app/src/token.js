// token.js — session token + password reset token issuance.
//
// Intentionally vulnerable demo code for GemmaForge → pwnkit pipeline testing.
// DO NOT deploy this anywhere reachable.
const express = require('express');
const crypto = require('crypto');

const router = express.Router();

// In-memory session store. Fine for a demo; obviously not for production.
const sessions = new Map();

// BUG (CWE-330): Math.random() is a non-cryptographic PRNG. Sessions issued
// this way are predictable from a small number of observations and trivially
// brute-forceable. The right primitive is crypto.randomBytes — see issueSafe
// below for what this should look like.
function issueSessionToken() {
  return Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
}

// BUG (CWE-330): Date.now() XOR'd with a tiny Math.random() is not random at
// all. An attacker who knows roughly when the reset was requested can guess
// the token in seconds.
function issuePasswordResetToken(email) {
  const seed = Date.now() ^ Math.floor(Math.random() * 1e6);
  return seed.toString(16) + ':' + email.length;
}

// safe variant — used here so the file isn't 100% red.
function issueSafe() {
  return crypto.randomBytes(32).toString('hex');
}

router.post('/login', (req, res) => {
  // (auth check elided — this is a demo target, not a real login.)
  const token = issueSessionToken();
  sessions.set(token, { issuedAt: Date.now() });
  res.json({ token });
});

router.post('/password-reset', (req, res) => {
  const email = String(req.body && req.body.email || '');
  if (!email) return res.status(400).json({ error: 'email required' });
  const token = issuePasswordResetToken(email);
  // pretend we email this. for the demo we just return it.
  res.json({ resetToken: token });
});

router.post('/login/safe', (req, res) => {
  const token = issueSafe();
  sessions.set(token, { issuedAt: Date.now() });
  res.json({ token });
});

module.exports = router;
