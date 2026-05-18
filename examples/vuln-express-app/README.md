# vuln-express-app

**This is a target repo for demoing the GemmaForge → pwnkit pipeline. DO NOT use in production.** It is deliberately full of textbook web bugs so that the GemmaForge probe has something obvious to flag.

## What's in here

Five route files, each with one or two deliberate vulnerabilities and some safe boilerplate around them so the file doesn't look like a one-liner CTF challenge:

| file | CWE | bug |
|---|---|---|
| `src/users.js` | CWE-89 (SQL injection) | `req.params.id` and `req.query.role` interpolated into SQL strings. |
| `src/files.js` | CWE-22 (path traversal) | `req.query.name` / `req.params.name` joined to `/var/data` with no traversal check. |
| `src/ping.js` | CWE-78 (OS command injection) | `req.query.host` passed to `child_process.exec` via a template string. |
| `src/token.js` | CWE-330 (weak randomness) | Session + password-reset tokens built from `Math.random()` / `Date.now()`. |
| `src/index.js` | — | Mounts the routers, no bugs. |

Each vulnerable route has a `*/safe` counterpart in the same file showing roughly what the fixed version looks like (parameterized SQL, `path.resolve` containment check, `execFile`, `crypto.randomBytes`).

## How it fits into the pipeline

```
gemmaforge scan examples/vuln-express-app
        |
        v
   leads.jsonl  (gemmaforge.leads/v1, one record per ranked region)
        |
        v
pwnkit triage --seed-findings leads.jsonl ...
```

See `scripts/demo_pipeline.sh` at the repo root for the runnable walkthrough.

## Running the server (optional)

The pipeline demo never actually launches the server — it only reads the source. If you want to poke at it locally:

```bash
cd examples/vuln-express-app
npm install
npm start    # binds to 127.0.0.1:3000 only
```

Again: bind address is intentionally `127.0.0.1`. Do not change that.
