#!/usr/bin/env python3
"""Quick browser-based viewer for data/*.jsonl pair datasets.

Usage:
    uv run scripts/dataset_viewer.py            # serves on http://127.0.0.1:8765
    uv run scripts/dataset_viewer.py --port 9000
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

# Cache: filename -> list[dict]
_cache: dict[str, list[dict]] = {}


def load(name: str) -> list[dict]:
    if name in _cache:
        return _cache[name]
    path = DATA_DIR / name
    rows: list[dict] = []
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    _cache[name] = rows
    return rows


def list_files() -> list[dict]:
    out = []
    seen: set[str] = set()
    for pattern in ("dataset*.jsonl", "pairs*.jsonl"):
        for p in sorted(DATA_DIR.glob(pattern)):
            if p.name in seen:
                continue
            seen.add(p.name)
            size = p.stat().st_size
            # count lines without loading whole file into memory
            with p.open() as fh:
                n = sum(1 for _ in fh)
            out.append({"name": p.name, "rows": n, "bytes": size})
    return out


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>gemmaforge dataset viewer</title>
<style>
  :root { --bg: #0e1116; --fg: #d6dde6; --muted: #7d8a9c; --vuln: #ff5d5d; --safe: #4ade80; --accent: #6aa9ff; --card: #161b22; --border: #232a35; }
  * { box-sizing: border-box; }
  body { margin: 0; font: 14px/1.45 ui-sans-serif, system-ui, sans-serif; background: var(--bg); color: var(--fg); }
  header { padding: 12px 18px; border-bottom: 1px solid var(--border); display: flex; gap: 16px; align-items: center; flex-wrap: wrap; }
  header h1 { font-size: 14px; margin: 0; font-weight: 600; }
  header select, header input, header button { background: var(--card); color: var(--fg); border: 1px solid var(--border); padding: 5px 9px; border-radius: 4px; font: inherit; }
  header button { cursor: pointer; }
  header button:hover { border-color: var(--accent); }
  .stat { color: var(--muted); font-size: 12px; }
  main { display: grid; grid-template-columns: 280px 1fr; height: calc(100vh - 50px); }
  aside { border-right: 1px solid var(--border); overflow-y: auto; }
  .row { padding: 8px 12px; border-bottom: 1px solid var(--border); cursor: pointer; font-size: 12px; }
  .row:hover { background: var(--card); }
  .row.active { background: #1f2937; border-left: 3px solid var(--accent); padding-left: 9px; }
  .row .lbl { display: inline-block; width: 38px; font-weight: 700; }
  .row .lbl.vuln { color: var(--vuln); }
  .row .lbl.safe { color: var(--safe); }
  .row .meta { color: var(--muted); }
  section { overflow-y: auto; padding: 18px 24px; }
  .meta-grid { display: grid; grid-template-columns: 120px 1fr; gap: 4px 14px; margin-bottom: 14px; }
  .meta-grid .k { color: var(--muted); }
  pre { background: var(--card); border: 1px solid var(--border); padding: 14px; border-radius: 6px; overflow-x: auto; font: 13px/1.55 ui-monospace, "SF Mono", Menlo, monospace; white-space: pre; }
  pre.vuln { border-left: 3px solid var(--vuln); }
  pre.safe { border-left: 3px solid var(--safe); }
  .tok-sink { background: rgba(255,93,93,.28); border-radius: 2px; }
  .tok-source { background: rgba(106,169,255,.28); border-radius: 2px; }
  .tok-sanitizer { background: rgba(74,222,128,.28); border-radius: 2px; }
  .tok-evidence { outline: 1px dashed rgba(255,200,80,.6); border-radius: 2px; }
  .tok-vuln_line { background: rgba(255,93,93,.12); }
  .legend { font-size: 12px; color: var(--muted); margin: 6px 0 12px; }
  .legend span { display: inline-block; padding: 1px 6px; margin-right: 8px; border-radius: 3px; }
  .pager { display: flex; gap: 8px; align-items: center; }
</style>
</head>
<body>
<header>
  <h1>gemmaforge / dataset viewer</h1>
  <select id="fileSel"></select>
  <span class="stat" id="fileStat"></span>
  <input id="filter" placeholder="filter (cwe / lang / label / source)" size="34">
  <div class="pager">
    <button id="prev">prev</button>
    <input id="jump" type="number" min="0" style="width:80px" placeholder="idx">
    <button id="next">next</button>
  </div>
</header>
<main>
  <aside id="list"></aside>
  <section id="detail"></section>
</main>
<script>
const fileSel = document.getElementById('fileSel');
const fileStat = document.getElementById('fileStat');
const listEl = document.getElementById('list');
const detailEl = document.getElementById('detail');
const filterEl = document.getElementById('filter');
const jumpEl = document.getElementById('jump');

let state = { file: null, rows: [], filtered: [], idx: 0 };

async function init() {
  const files = await (await fetch('/api/files')).json();
  fileSel.innerHTML = files.map(f => `<option value="${f.name}">${f.name} (${f.rows})</option>`).join('');
  fileSel.onchange = () => loadFile(fileSel.value);
  filterEl.oninput = applyFilter;
  document.getElementById('prev').onclick = () => move(-1);
  document.getElementById('next').onclick = () => move(1);
  jumpEl.onchange = () => { state.idx = Math.max(0, Math.min(state.filtered.length-1, +jumpEl.value)); render(); };
  await loadFile(files[0].name);
}

async function loadFile(name) {
  state.file = name;
  state.rows = await (await fetch('/api/rows?file=' + encodeURIComponent(name))).json();
  fileStat.textContent = `${state.rows.length} rows`;
  state.idx = 0;
  applyFilter();
}

function applyFilter() {
  const q = filterEl.value.trim().toLowerCase();
  state.filtered = !q ? state.rows.slice() : state.rows.filter(r => {
    const hay = [r.label, r.cwe, r.cve, r.lang, r.source, r.vuln_type, r._origin_repo, r._file_name, r._func_name, r.label_confidence, r.is_completion_vulnerable].join(' ').toLowerCase();
    return hay.includes(q);
  });
  state.idx = 0;
  renderList();
  render();
}

function renderList() {
  listEl.innerHTML = state.filtered.slice(0, 500).map((r, i) => {
    const isVuln = r.label === 1 || r.is_completion_vulnerable === true;
    const lbl = isVuln ? 'VULN' : 'SAFE';
    const cls = isVuln ? 'vuln' : 'safe';
    return `<div class="row ${i===state.idx?'active':''}" data-i="${i}">
      <span class="lbl ${cls}">${lbl}</span>
      <span>${r.cwe || '-'}</span>
      <span class="meta"> · ${r.lang || '-'} · ${r.source || '-'}</span>
    </div>`;
  }).join('') + (state.filtered.length > 500 ? `<div class="row meta">… ${state.filtered.length-500} more (filter to narrow)</div>` : '');
  listEl.querySelectorAll('.row[data-i]').forEach(el => {
    el.onclick = () => { state.idx = +el.dataset.i; render(); };
  });
}

function move(d) {
  state.idx = Math.max(0, Math.min(state.filtered.length-1, state.idx + d));
  render();
}

function escapeHtml(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

function renderCodeWithTokenLabels(code, tokenLabels) {
  if (!tokenLabels) return escapeHtml(code);
  // Build a span-tagged version using char offsets.
  const ranges = [];
  for (const [kind, spans] of Object.entries(tokenLabels)) {
    for (const [a, b] of spans) ranges.push({ a, b, kind });
  }
  ranges.sort((x, y) => x.a - y.a || y.b - x.b);
  let out = '', cursor = 0;
  // Render in order; allow overlap by sequential opening (simple but readable).
  // To keep it simple, flatten into a non-overlap layer per priority.
  const priority = { sink: 0, source: 1, sanitizer: 2, evidence: 3, vulnerable_line: 4 };
  ranges.sort((x, y) => x.a - y.a || (priority[x.kind] ?? 99) - (priority[y.kind] ?? 99));
  for (const r of ranges) {
    if (r.a < cursor) continue; // skip nested for simplicity
    out += escapeHtml(code.slice(cursor, r.a));
    const cls = r.kind === 'vulnerable_line' ? 'tok-vuln_line' : 'tok-' + r.kind;
    out += `<span class="${cls}" title="${r.kind} ${r.a}-${r.b}">${escapeHtml(code.slice(r.a, r.b))}</span>`;
    cursor = r.b;
  }
  out += escapeHtml(code.slice(cursor));
  return out;
}

function render() {
  jumpEl.value = state.idx;
  listEl.querySelectorAll('.row').forEach((el, i) => el.classList.toggle('active', i === state.idx));
  const r = state.filtered[state.idx];
  if (!r) { detailEl.innerHTML = '<p class="stat">no rows</p>'; return; }
  const isVuln = r.label === 1 || r.is_completion_vulnerable === true;
  const meta = [
    ['index', `${state.idx} / ${state.filtered.length-1}`],
    ['label', isVuln ? 'VULN (1)' : 'SAFE (0)'],
    ['cwe', r.cwe], ['cve', r.cve], ['lang', r.lang],
    ['source', r.source], ['vuln_type', r.vuln_type],
    ['_origin_repo', r._origin_repo], ['_file_name', r._file_name], ['_func_name', r._func_name],
    ['_line_no', r._line_no],
    ['label_confidence', r.label_confidence],
  ].filter(([_, v]) => v !== undefined && v !== null && v !== '');
  const legend = r.token_labels ? `<div class="legend">
    <span class="tok-sink">sink</span><span class="tok-source">source</span>
    <span class="tok-sanitizer">sanitizer</span><span class="tok-evidence">evidence</span>
    <span class="tok-vuln_line">vulnerable_line</span>
  </div>` : '';
  detailEl.innerHTML = `
    <div class="meta-grid">${meta.map(([k,v]) => `<div class="k">${k}</div><div>${escapeHtml(String(v))}</div>`).join('')}</div>
    ${legend}
    <pre class="${isVuln?'vuln':'safe'}">${renderCodeWithTokenLabels(r.code || '', r.token_labels)}</pre>
  `;
}

init();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, body: bytes, ctype: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            self._send(200, INDEX_HTML.encode(), "text/html; charset=utf-8")
            return
        if url.path == "/api/files":
            self._send(200, json.dumps(list_files()).encode(), "application/json")
            return
        if url.path == "/api/rows":
            qs = parse_qs(url.query)
            name = qs.get("file", [""])[0]
            if not name or not (DATA_DIR / name).exists():
                self._send(404, b'{"error":"file not found"}', "application/json")
                return
            self._send(200, json.dumps(load(name)).encode(), "application/json")
            return
        self._send(404, b"not found", "text/plain")

    def log_message(self, *_args) -> None:  # quiet
        pass


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    args = ap.parse_args()
    if not DATA_DIR.exists():
        raise SystemExit(f"data dir not found: {DATA_DIR}")
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"dataset viewer → http://{args.host}:{args.port}")
    print(f"serving {len(list_files())} files from {DATA_DIR}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
