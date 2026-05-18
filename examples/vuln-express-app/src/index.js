// index.js — entrypoint for the vuln-express-app demo target.
//
// This server only exists so GemmaForge → pwnkit can be demoed end-to-end
// on a fresh checkout, with no Gemma weights, no DB, no external services.
// DO NOT run this on a host that's reachable from the internet.
const express = require('express');

const users = require('./users');
const files = require('./files');
const ping = require('./ping');
const token = require('./token');

const app = express();
app.use(express.json());

app.get('/', (req, res) => {
  res.json({
    name: 'vuln-express-app',
    purpose: 'demo target for GemmaForge → pwnkit',
    routes: [
      'GET /users/:id',
      'GET /users?role=...',
      'GET /files?name=...',
      'GET /files/raw/:name',
      'GET /ping?host=...',
      'GET /traceroute?host=...',
      'POST /login',
      'POST /password-reset',
    ],
    warning: 'intentionally vulnerable — do not deploy',
  });
});

app.use(users);
app.use(files);
app.use(ping);
app.use(token);

// catch-all 404 so unknown routes don't leak express defaults.
app.use((req, res) => res.status(404).json({ error: 'not found' }));

if (require.main === module) {
  const port = Number(process.env.PORT || 3000);
  app.listen(port, '127.0.0.1', () => {
    console.log(`vuln-express-app listening on http://127.0.0.1:${port}`);
    console.log('this is a vulnerable demo target — do not expose');
  });
}

module.exports = app;
