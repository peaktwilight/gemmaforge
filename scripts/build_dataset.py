"""Build a vulnerable / safe code-pair dataset for probe training.

Strategy: pull from HuggingFace's `bstee615/bigvul` (or similar) which has
patched/vulnerable C/C++ function pairs labeled with CVE/CWE. Filter to a
balanced ~500 vuln + ~500 safe sample. Write as JSONL with fields:
  { "code": "...", "label": 0|1, "cwe": "...", "cve": "...", "source": "..." }

Falls back to a small built-in seed dataset (built from the author's own
CVEs) if HuggingFace isn't reachable — the demo can still run.
"""
from __future__ import annotations
import json
import os
import random
import sys
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "pairs.jsonl"
OUT.parent.mkdir(parents=True, exist_ok=True)

random.seed(7)


SEED_PAIRS: list[dict] = [
    # CVE-2026-33896 style — certificate verification bug pattern
    {
        "code": "function verifyCert(cert) {\n  if (!cert) return true;\n  return cert.subject === cert.issuer;\n}",
        "label": 1, "cwe": "CWE-295", "cve": "CVE-2026-33896-style",
        "source": "doruk-cve-corpus",
        "note": "Pattern: trivially-accepted certificate verification — every self-signed cert passes.",
    },
    {
        "code": "function verifyCert(cert, trustedCAs) {\n  if (!cert) throw new Error('missing certificate');\n  return trustedCAs.some(ca => pki.verifyCertificateChain(ca, cert));\n}",
        "label": 0, "cwe": None, "cve": None, "source": "doruk-cve-corpus",
    },
    # CWE-22 path traversal
    {
        "code": "function readUserFile(filename) {\n  return fs.readFileSync('/var/data/' + filename, 'utf8');\n}",
        "label": 1, "cwe": "CWE-22", "cve": None, "source": "synthetic-seed",
        "note": "Concatenated user path — '../../etc/passwd' wins.",
    },
    {
        "code": "function readUserFile(filename) {\n  const safe = path.resolve('/var/data', path.basename(filename));\n  if (!safe.startsWith('/var/data/')) throw new Error('bad path');\n  return fs.readFileSync(safe, 'utf8');\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-89 SQL injection
    {
        "code": "function getUserById(id) {\n  return db.query(`SELECT * FROM users WHERE id=${id}`);\n}",
        "label": 1, "cwe": "CWE-89", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function getUserById(id) {\n  return db.query('SELECT * FROM users WHERE id=?', [id]);\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-94 code injection / eval
    {
        "code": "function runRule(expr, data) {\n  return eval(expr);\n}",
        "label": 1, "cwe": "CWE-94", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function runRule(expr, data) {\n  return jsonLogic.apply(expr, data);\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-1333 ReDoS — the picomatch pattern Doruk found
    {
        "code": "const RE = /^(a+)+$/;\nfunction isMatch(input) { return RE.test(input); }",
        "label": 1, "cwe": "CWE-1333", "cve": "picomatch-style",
        "source": "doruk-cve-corpus",
        "note": "Nested-quantifier regex — exponential backtracking.",
    },
    {
        "code": "const RE = /^a+$/;\nfunction isMatch(input) {\n  if (input.length > 1024) return false;\n  return RE.test(input);\n}",
        "label": 0, "cwe": None, "cve": None, "source": "doruk-cve-corpus",
    },
    # CWE-78 OS command injection
    {
        "code": "function runDiag(host) {\n  return execSync(`ping -c 1 ${host}`).toString();\n}",
        "label": 1, "cwe": "CWE-78", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function runDiag(host) {\n  if (!/^[a-z0-9.-]+$/.test(host)) throw new Error('bad host');\n  return execFileSync('ping', ['-c', '1', host]).toString();\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-798 hardcoded credentials
    {
        "code": "const API_KEY = 'sk-prod-9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c';\nfunction client() { return new SDK({ apiKey: API_KEY }); }",
        "label": 1, "cwe": "CWE-798", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function client() {\n  const key = process.env.API_KEY;\n  if (!key) throw new Error('API_KEY not set');\n  return new SDK({ apiKey: key });\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-352 CSRF: token comparison vs no token
    {
        "code": "app.post('/transfer', (req, res) => {\n  bank.transfer(req.user, req.body.to, req.body.amount);\n  res.send('ok');\n});",
        "label": 1, "cwe": "CWE-352", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "app.post('/transfer', csrfCheck, (req, res) => {\n  bank.transfer(req.user, req.body.to, req.body.amount);\n  res.send('ok');\n});",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-918 SSRF
    {
        "code": "app.get('/fetch', async (req, res) => {\n  const r = await fetch(req.query.url);\n  res.send(await r.text());\n});",
        "label": 1, "cwe": "CWE-918", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "const ALLOWED = ['https://api.example.com/'];\napp.get('/fetch', async (req, res) => {\n  if (!ALLOWED.some(p => req.query.url.startsWith(p))) return res.status(400).end();\n  const r = await fetch(req.query.url);\n  res.send(await r.text());\n});",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-330 weak randomness for secrets
    {
        "code": "function newToken() {\n  return Math.random().toString(36).slice(2);\n}",
        "label": 1, "cwe": "CWE-330", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function newToken() {\n  return crypto.randomBytes(32).toString('hex');\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-327 broken crypto
    {
        "code": "function hashPassword(pw) {\n  return crypto.createHash('md5').update(pw).digest('hex');\n}",
        "label": 1, "cwe": "CWE-327", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "async function hashPassword(pw) {\n  return await argon2.hash(pw, { type: argon2.argon2id });\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-79 XSS
    {
        "code": "app.get('/greet', (req, res) => {\n  res.send(`<h1>Hi ${req.query.name}</h1>`);\n});",
        "label": 1, "cwe": "CWE-79", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "app.get('/greet', (req, res) => {\n  res.send(`<h1>Hi ${escapeHtml(req.query.name)}</h1>`);\n});",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
    # CWE-502 unsafe deserialization
    {
        "code": "function load(buf) {\n  return JSON.parse(buf.toString(), reviver);\n}\nfunction reviver(k, v) {\n  if (v && v.__type) return new (global[v.__type])(v.value);\n  return v;\n}",
        "label": 1, "cwe": "CWE-502", "cve": None, "source": "synthetic-seed",
    },
    {
        "code": "function load(buf) {\n  return JSON.parse(buf.toString());\n}",
        "label": 0, "cwe": None, "cve": None, "source": "synthetic-seed",
    },
]


def try_huggingface_dataset(max_pairs: int = 800) -> list[dict]:
    """Pull paired vulnerable/safe examples from HF.

    The DPO datasets are ideal: each row has `chosen` (safe) and `rejected`
    (vulnerable) for the same prompt → perfectly balanced labels for free.
    """
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        print("[dataset] datasets library not installed — using seed only", file=sys.stderr)
        return []

    out: list[dict] = []

    # 1) CyberNative DPO: chosen=safe, rejected=vulnerable, paired by prompt.
    try:
        print("[dataset] CyberNative/Code_Vulnerability_Security_DPO…", file=sys.stderr)
        ds = load_dataset("CyberNative/Code_Vulnerability_Security_DPO", split="train", streaming=True)
        count = 0
        for row in ds:
            chosen = row.get("chosen")
            rejected = row.get("rejected")
            if not chosen or not rejected:
                continue
            lang = row.get("lang") or row.get("language") or "unknown"
            vuln_type = row.get("vulnerability") or row.get("vuln_type")
            out.append({
                "code": str(rejected), "label": 1, "cwe": None, "cve": None,
                "source": "CyberNative-DPO", "lang": lang, "vuln_type": vuln_type,
            })
            out.append({
                "code": str(chosen), "label": 0, "cwe": None, "cve": None,
                "source": "CyberNative-DPO", "lang": lang, "vuln_type": vuln_type,
            })
            count += 1
            if count >= max_pairs:
                break
        print(f"[dataset] CyberNative-DPO: {count} pairs", file=sys.stderr)
    except Exception as e:
        print(f"[dataset] CyberNative-DPO failed: {e}", file=sys.stderr)

    # 2) Fallback: DiverseVul, paired by `func_before` (vuln) vs `func_after` (safe)
    if not out:
        try:
            print("[dataset] DiverseVul fallback…", file=sys.stderr)
            ds = load_dataset("bstee615/diversevul", split="train", streaming=True)
            count = 0
            for row in ds:
                before = row.get("func_before") or row.get("func")
                after = row.get("func_after")
                if not before:
                    continue
                if after and after.strip() and after != before:
                    out.append({"code": str(before), "label": 1, "cwe": row.get("CWE_ID"), "cve": row.get("CVE_ID"), "source": "DiverseVul"})
                    out.append({"code": str(after), "label": 0, "cwe": None, "cve": None, "source": "DiverseVul-patched"})
                    count += 1
                if count >= max_pairs:
                    break
            print(f"[dataset] DiverseVul: {count} pairs", file=sys.stderr)
        except Exception as e:
            print(f"[dataset] DiverseVul failed: {e}", file=sys.stderr)

    return out


def balance(rows: list[dict], n_per_class: int = 500) -> list[dict]:
    pos = [r for r in rows if r["label"] == 1]
    neg = [r for r in rows if r["label"] == 0]
    random.shuffle(pos)
    random.shuffle(neg)
    return pos[:n_per_class] + neg[:n_per_class]


def main() -> None:
    rows: list[dict] = list(SEED_PAIRS)
    enriched = try_huggingface_dataset(max_pairs=int(os.environ.get("GF_MAX", "800")))
    rows.extend(enriched)
    rows = balance(rows, n_per_class=int(os.environ.get("GF_PER_CLASS", "500")))
    random.shuffle(rows)

    with OUT.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    pos = sum(1 for r in rows if r["label"] == 1)
    neg = len(rows) - pos
    print(f"[dataset] wrote {OUT} — {pos} vulnerable / {neg} safe", file=sys.stderr)


if __name__ == "__main__":
    main()
