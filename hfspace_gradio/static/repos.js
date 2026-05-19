// GemmaForge · viewer JS — shared between the static heldout benchmark and
// the live-scan results pages. The host page sets `window.GEMMAFORGE_VIEWER`:
//
//   {
//     basePath: "/api/repos" | "/api/scan",  // route prefix for API calls
//     mode: "static" | "live",                // controls which UI bits show
//   }
//
// In live mode there are no ground-truth traces (the user uploaded an
// arbitrary repo), so trace-overlap badges and CWE-match checks degrade
// gracefully to empty.

const CONFIG = window.GEMMAFORGE_VIEWER || { basePath: "/api/repos", mode: "static" };
const BASE = CONFIG.basePath;
const MODE = CONFIG.mode;

const state = {
  index: null,
  filtered: [],
  selectedRepo: null,
  detail: null,
  selectedFile: null,
  // F1-max threshold on lead confidence. Loaded from `${BASE}/index`.
  // Below this floor a lead is not painted at all.
  confidenceThreshold: 0,
};

const el = (id) => document.getElementById(id);

function rankBadge(rank1) {
  if (rank1 == null) return { cls: "no-leads", txt: "—" };
  if (rank1 <= 1) return { cls: "hit-1", txt: "@1" };
  if (rank1 <= 5) return { cls: "hit-5", txt: `@${rank1}` };
  if (rank1 <= 25) return { cls: "hit-25", txt: `@${rank1}` };
  return { cls: "miss", txt: `@${rank1}` };
}

function setSummary(idx) {
  const root = (idx.benchmark_root || "").split("/").slice(-2).join("/");
  const leads = (idx.leads_dir || "—").split("/").slice(-1)[0];
  let calBit = "";
  if (idx.calibration && idx.calibration.f1_max) {
    const tau = idx.calibration.f1_max.threshold;
    const f1 = idx.calibration.f1_max.f1;
    calBit = ` · F1-max τ=${tau.toFixed(3)} (F1=${f1.toFixed(2)})`;
  }
  const label = MODE === "live"
    ? `${idx.n_repos} scan(s) · leads=${leads}${calBit}`
    : `${idx.n_repos} repos · ${idx.n_with_leads} scanned · leads=${leads} · root=${root}${calBit}`;
  el("summary-tagline").textContent = label;
}

function populateFilters(repos) {
  const cwes = new Set();
  const langs = new Set();
  for (const r of repos) {
    if (r.cwe) cwes.add(r.cwe);
    if (r.language) langs.add(r.language);
  }
  const cwePicker = el("filter-cwe");
  if (cwePicker) {
    for (const c of [...cwes].sort()) {
      const o = document.createElement("option");
      o.value = c;
      o.textContent = c;
      cwePicker.appendChild(o);
    }
  }
  const langPicker = el("filter-lang");
  if (langPicker) {
    for (const l of [...langs].sort()) {
      const o = document.createElement("option");
      o.value = l;
      o.textContent = l;
      langPicker.appendChild(o);
    }
  }
}

function applyFilters() {
  const q = (el("search")?.value || "").trim().toLowerCase();
  const cwe = el("filter-cwe")?.value || "";
  const lang = el("filter-lang")?.value || "";
  const status = el("filter-status")?.value || "";
  state.filtered = state.index.repos.filter((r) => {
    if (q && !r.repo_id.toLowerCase().includes(q)) return false;
    if (cwe && r.cwe !== cwe) return false;
    if (lang && r.language !== lang) return false;
    if (status === "no-leads" && r.has_leads) return false;
    if (status === "hit" && (r.first_hit_rank == null || r.first_hit_rank > 25)) return false;
    if (status === "miss") {
      if (!r.has_leads) return false;
      if (r.first_hit_rank != null && r.first_hit_rank <= 25) return false;
    }
    return true;
  });
  renderRepoList();
}

function renderRepoList() {
  const ul = el("repo-list");
  ul.innerHTML = "";
  const counts = el("counts");
  if (counts) {
    counts.textContent = `${state.filtered.length}/${state.index.repos.length} repos`;
  }

  for (const r of state.filtered) {
    const li = document.createElement("li");
    if (state.selectedRepo === r.repo_id) li.classList.add("active");
    const badge = r.has_leads ? rankBadge(r.first_hit_rank) : { cls: "no-leads", txt: "—" };

    const row1 = document.createElement("div");
    row1.className = "row1";
    const id = document.createElement("span");
    id.className = "repo-id";
    id.textContent = r.repo_id;
    id.title = r.repo_id;
    const b = document.createElement("span");
    b.className = `rank-badge ${badge.cls}`;
    b.textContent = badge.txt;
    row1.appendChild(id);
    row1.appendChild(b);

    const row2 = document.createElement("div");
    row2.className = "row2";
    const cwe = document.createElement("span");
    cwe.className = "tag cwe";
    cwe.textContent = r.cwe || "—";
    const lang = document.createElement("span");
    lang.className = "tag lang";
    lang.textContent = r.language || "—";
    const meta = document.createElement("span");
    meta.style.color = "var(--muted)";
    const tau = state.confidenceThreshold || 0;
    const aboveTau = r.n_leads_above_tau ?? r.n_leads;
    const leadBit = tau > 0
      ? `${aboveTau} lead${aboveTau === 1 ? "" : "s"} ≥τ`
      : `${r.n_leads} lead${r.n_leads === 1 ? "" : "s"}`;
    const traceBit = MODE === "live"
      ? `${r.n_files ?? 0} file${(r.n_files ?? 0) === 1 ? "" : "s"}`
      : `${r.n_traces} trace${r.n_traces === 1 ? "" : "s"}`;
    meta.textContent = `${traceBit} · ${leadBit}`;
    row2.appendChild(cwe);
    row2.appendChild(lang);
    row2.appendChild(meta);

    li.appendChild(row1);
    li.appendChild(row2);
    li.addEventListener("click", () => selectRepo(r.repo_id));
    ul.appendChild(li);
  }
}

async function selectRepo(repoId) {
  state.selectedRepo = repoId;
  state.selectedFile = null;
  renderRepoList();
  el("empty-state").classList.add("hidden");
  el("viewer-content").classList.remove("hidden");
  el("repo-title").textContent = repoId;
  el("repo-sub").textContent = "loading…";
  el("file-tabs").innerHTML = "";
  el("file-meta").textContent = "";
  el("code").innerHTML = "";
  el("leads-summary").innerHTML = "";
  el("repo-metrics").innerHTML = "";

  let detail;
  try {
    const res = await fetch(`${BASE}/${encodeURIComponent(repoId)}`);
    if (!res.ok) throw new Error(`http ${res.status}`);
    detail = await res.json();
  } catch (e) {
    el("repo-sub").textContent = `load failed: ${e.message}`;
    return;
  }
  state.detail = detail;
  renderRepoHeader(detail);
  renderFileTabs(detail);
  renderLeadsSummary(detail);

  const vulnFile = (detail.manifest.files || []).find((f) => f.role === "vulnerable");
  const first = vulnFile || (detail.manifest.files || [])[0];
  if (first) selectFile(first.path);
}

function renderRepoHeader(detail) {
  const m = detail.manifest;
  const entry = detail.report_entry || {};
  const tau = state.confidenceThreshold || 0;
  const totalLeads = (detail.leads || []).length;
  const aboveTau = (detail.leads || []).filter(
    (l) => Number(l.gemmaforge_confidence ?? 0) >= tau,
  ).length;
  const leadsStat = tau > 0 ? `${aboveTau} ≥τ / ${totalLeads}` : String(totalLeads);
  const sub = el("repo-sub");
  sub.innerHTML = "";
  const parts = [
    ["cwe", m.cwe || "—"],
    ["lang", m.language || "—"],
    ["source", m.source_dataset || m.source || "—"],
    ["files", String((m.files || []).length)],
  ];
  if (MODE !== "live") {
    parts.push(["traces", String((m.vulnerability_traces || []).length)]);
  }
  parts.push(["leads", leadsStat]);
  for (const [k, v] of parts) {
    const span = document.createElement("span");
    span.innerHTML = `<span style="color:var(--muted)">${k}</span> ${v}`;
    sub.appendChild(span);
  }

  const metrics = el("repo-metrics");
  metrics.innerHTML = "";
  if (MODE === "live") {
    metrics.appendChild(metricBlock("top conf", detail.leads?.length ? Number(detail.leads[0].gemmaforge_confidence || 0).toFixed(3) : "—", ""));
    metrics.appendChild(metricBlock("leads ≥τ", String(aboveTau), aboveTau > 0 ? "hit" : ""));
  } else {
    const rank = entry.first_hit_rank;
    const rr = entry.reciprocal_rank;
    metrics.appendChild(metricBlock(
      "first hit",
      rank == null ? "—" : `@${rank}`,
      rank != null && rank <= 25 ? "hit" : (rank == null ? "" : "miss"),
    ));
    metrics.appendChild(metricBlock("recip rank", rr == null ? "—" : rr.toFixed(2), ""));
    const r1 = entry.repo_recall_at_k && entry.repo_recall_at_k["@1"];
    const r25 = entry.repo_recall_at_k && entry.repo_recall_at_k["@25"];
    metrics.appendChild(metricBlock("recall @1 / @25", `${fmtPct(r1)} / ${fmtPct(r25)}`, ""));
  }
}

function fmtPct(v) {
  if (v == null) return "—";
  return `${Math.round(v * 100)}%`;
}

function metricBlock(label, val, cls) {
  const wrap = document.createElement("div");
  wrap.className = "m";
  const l = document.createElement("span");
  l.textContent = label;
  const v = document.createElement("span");
  v.className = `val ${cls || ""}`;
  v.textContent = val;
  wrap.appendChild(l);
  wrap.appendChild(v);
  return wrap;
}

function renderFileTabs(detail) {
  const tabs = el("file-tabs");
  tabs.innerHTML = "";
  const tau = state.confidenceThreshold || 0;
  const leadFiles = new Set(
    (detail.leads || [])
      .filter((l) => Number(l.gemmaforge_confidence ?? 0) >= tau)
      .map((l) => l.file),
  );
  for (const f of detail.manifest.files || []) {
    const btn = document.createElement("button");
    btn.dataset.path = f.path;
    btn.addEventListener("click", () => selectFile(f.path));
    const label = document.createElement("span");
    label.textContent = f.path;
    btn.appendChild(label);
    if (f.role) {
      const role = document.createElement("span");
      role.className = `role ${f.role}`;
      role.textContent = String(f.role).replace("_", " ");
      btn.appendChild(role);
    }
    if (leadFiles.has(f.path)) {
      const dot = document.createElement("span");
      dot.className = "has-leads";
      dot.title = tau > 0
        ? `probe fired (≥τ=${tau.toFixed(2)}) in this file`
        : "probe emitted a lead in this file";
      btn.appendChild(dot);
    }
    tabs.appendChild(btn);
  }
}

async function selectFile(relPath) {
  if (!state.detail) return;
  state.selectedFile = relPath;
  for (const btn of el("file-tabs").querySelectorAll("button")) {
    btn.classList.toggle("active", btn.dataset.path === relPath);
  }
  el("code").innerHTML = '<div style="padding:12px 18px;color:var(--muted)">loading…</div>';

  let body;
  try {
    const res = await fetch(
      `${BASE}/file?repo=${encodeURIComponent(state.detail.repo_id)}` +
      `&path=${encodeURIComponent(relPath)}`,
    );
    if (!res.ok) throw new Error(`http ${res.status}`);
    body = await res.json();
  } catch (e) {
    el("code").innerHTML = `<div style="padding:12px 18px;color:var(--danger-solid)">load failed: ${e.message}</div>`;
    return;
  }

  const truthSpans = (state.detail.manifest.vulnerability_traces || [])
    .filter((t) => t.file === relPath);
  const leadSpans = (state.detail.leads || [])
    .filter((l) => l.file === relPath);

  const tau = state.confidenceThreshold || 0;
  const leadsAboveTau = leadSpans.filter(
    (l) => Number(l.gemmaforge_confidence ?? 0) >= tau,
  );
  el("file-meta").innerHTML = "";
  appendMeta("lines", body.lines);
  if (MODE !== "live") {
    appendMeta("truth spans", truthSpans.length);
  }
  appendMeta(
    "probe leads",
    tau > 0 ? `${leadsAboveTau.length} ≥τ / ${leadSpans.length} total` : leadSpans.length,
  );
  if (truthSpans.length) {
    const cwes = [...new Set(truthSpans.map((t) => t.cwe).filter(Boolean))];
    if (cwes.length) appendMeta("truth cwe", cwes.join(", "));
  }
  if (leadsAboveTau.length) {
    const cwes = [...new Set(leadsAboveTau.map((l) => l.gemmaforge_top_cwe).filter(Boolean))];
    if (cwes.length) appendMeta("pred cwe (≥τ)", cwes.join(", "));
  }

  renderCode(body.text, truthSpans, leadSpans);
}

function appendMeta(label, val) {
  const span = document.createElement("span");
  span.innerHTML = `<span style="color:var(--muted)">${label}</span> ${val}`;
  el("file-meta").appendChild(span);
}

function renderCode(text, truthSpans, leadSpans) {
  const code = el("code");
  code.innerHTML = "";
  const lines = text.split("\n");
  const truthByLine = new Map();
  for (const t of truthSpans) {
    for (let n = t.start_line; n <= t.end_line; n++) {
      const cur = truthByLine.get(n) || [];
      cur.push(t);
      truthByLine.set(n, cur);
    }
  }
  const tau = state.confidenceThreshold || 0;
  const aboveTau = leadSpans.filter(
    (l) => Number(l.gemmaforge_confidence ?? 0) >= tau,
  );
  const leadByLine = new Map();
  for (const l of aboveTau) {
    for (let n = l.start_line; n <= l.end_line; n++) {
      const cur = leadByLine.get(n) || [];
      cur.push(l);
      leadByLine.set(n, cur);
    }
  }
  const bestLeadByLine = new Map();
  for (const [n, ls] of leadByLine) {
    let best = ls[0];
    for (const l of ls) {
      if ((l.gemmaforge_confidence ?? 0) > (best.gemmaforge_confidence ?? 0)) best = l;
    }
    bestLeadByLine.set(n, best);
  }

  const frag = document.createDocumentFragment();
  for (let i = 0; i < lines.length; i++) {
    const n = i + 1;
    const row = document.createElement("div");
    row.className = "line";
    const t = truthByLine.get(n);
    const l = leadByLine.get(n);
    const best = bestLeadByLine.get(n);
    if (t) row.classList.add("truth");
    if (l) {
      row.classList.add("lead");
      const rank = best.rank ?? 0;
      const conf = Number(best.gemmaforge_confidence ?? 0);
      const denom = Math.max(1e-3, 1 - tau);
      const confFactor = Math.max(0, Math.min(1, (conf - tau) / denom));
      const alpha = (0.25 + 0.60 * confFactor).toFixed(3);
      row.style.setProperty("--lead-alpha", alpha);
      if (rank === 0) row.classList.add("lead-top1");
      else if (rank <= 4) row.classList.add("lead-top5");
    }
    if (l && l.some((x) => x.start_line === n)) row.classList.add("lead-start");
    if (l && l.some((x) => x.end_line === n)) row.classList.add("lead-end");
    row.id = `L${n}`;

    const ln = document.createElement("span");
    ln.className = "ln";
    ln.textContent = String(n);
    row.appendChild(ln);

    const badges = document.createElement("span");
    badges.className = "badge-col";
    if (l) {
      const starting = l.filter((x) => x.start_line === n);
      for (const lead of starting) {
        const b = document.createElement("span");
        b.className = "b lead";
        const conf = lead.gemmaforge_confidence;
        const cwe = lead.gemmaforge_top_cwe || "?";
        b.textContent = `#${(lead.rank ?? 0) + 1} ${cwe} ${(conf ?? 0).toFixed(2)}`;
        b.title =
          `rank=${(lead.rank ?? 0) + 1} · confidence=${conf} · ` +
          `predicted=${cwe} · score=${lead.gemmaforge_top_cwe_score}`;
        badges.appendChild(b);
      }
    }
    if (t) {
      const starting = t.filter((x) => x.start_line === n);
      for (const tr of starting) {
        const b = document.createElement("span");
        b.className = "b truth";
        b.textContent = `truth ${tr.cwe || ""}`.trim();
        b.title = `ground-truth ${tr.role}: ${tr.cwe} (${tr.label_source})`;
        badges.appendChild(b);
      }
    }
    row.appendChild(badges);

    const src = document.createElement("span");
    src.className = "src";
    src.textContent = lines[i];
    row.appendChild(src);

    frag.appendChild(row);
  }
  code.appendChild(frag);
}

function renderLeadsSummary(detail) {
  const wrap = el("leads-summary");
  wrap.innerHTML = "";
  const leads = (detail.leads || []).slice().sort((a, b) => (a.rank ?? 0) - (b.rank ?? 0));
  if (!leads.length) {
    const msg = MODE === "live"
      ? "no leads from the scan — try a different repo or lower the min-confidence slider"
      : "no leads on disk for this repo";
    wrap.innerHTML = `<div style="color:var(--muted)">${msg}</div>`;
    return;
  }
  const normCwe = (s) => {
    if (!s) return "";
    const m = /^CWE-(\d+)$/.exec(String(s));
    return m ? `CWE-${parseInt(m[1], 10)}` : String(s);
  };
  const truthCwes = new Set(
    (detail.manifest.vulnerability_traces || []).map((t) => normCwe(t.cwe)).filter(Boolean),
  );
  const truthFiles = new Set(
    (detail.manifest.vulnerability_traces || []).map((t) => t.file),
  );
  const table = document.createElement("table");
  const truthCol = MODE === "live" ? "" : "<th>cwe match</th>";
  table.innerHTML = `
    <thead><tr>
      <th>rank</th><th>file</th><th>lines</th>
      <th>confidence</th><th>pred cwe</th>${truthCol}
    </tr></thead>
    <tbody></tbody>
  `;
  const tbody = table.querySelector("tbody");
  for (const lead of leads) {
    const tr = document.createElement("tr");
    tr.className = "lead-row";
    tr.dataset.file = lead.file;
    tr.dataset.line = lead.start_line;
    tr.addEventListener("click", async () => {
      await selectFile(lead.file);
      const target = document.getElementById(`L${lead.start_line}`);
      if (target) target.scrollIntoView({ block: "center", behavior: "smooth" });
    });

    const truthHit =
      truthFiles.has(lead.file) &&
      (detail.manifest.vulnerability_traces || []).some(
        (t) =>
          t.file === lead.file &&
          !(t.end_line < lead.start_line || t.start_line > lead.end_line),
      );
    const cweMatch = lead.gemmaforge_top_cwe && truthCwes.has(normCwe(lead.gemmaforge_top_cwe));
    if (cweMatch) tr.classList.add("cwe-hit");

    const conf = Number(lead.gemmaforge_confidence || 0);
    const tau = state.confidenceThreshold || 0;
    if (conf < tau) tr.classList.add("below-tau");
    const truthCell = MODE === "live" ? "" : `<td>${truthHit ? "✓ span" : ""} ${cweMatch ? "✓ cwe" : ""}</td>`;
    tr.innerHTML = `
      <td>#${(lead.rank ?? 0) + 1}</td>
      <td>${lead.file}</td>
      <td>${lead.start_line}–${lead.end_line}</td>
      <td>${conf.toFixed(3)}<span class="conf-bar" style="width:${Math.round(conf * 60)}px"></span></td>
      <td>${lead.gemmaforge_top_cwe || "—"}</td>
      ${truthCell}
    `;
    tbody.appendChild(tr);
  }
  wrap.appendChild(table);
}

async function init() {
  let idx;
  try {
    const res = await fetch(`${BASE}/index`);
    if (!res.ok) throw new Error(`http ${res.status}`);
    idx = await res.json();
  } catch (e) {
    el("summary-tagline").textContent = `index load failed: ${e.message}`;
    return;
  }
  state.index = idx;
  state.filtered = idx.repos || [];
  state.confidenceThreshold =
    (idx.calibration && idx.calibration.f1_max && idx.calibration.f1_max.threshold) || 0;
  setSummary(idx);
  populateFilters(state.filtered);
  renderRepoList();
  for (const id of ["search", "filter-cwe", "filter-lang", "filter-status"]) {
    el(id)?.addEventListener(id === "search" ? "input" : "change", applyFilters);
  }
  // Live-scan mode usually has exactly one repo — auto-select it.
  if (MODE === "live" && state.filtered.length === 1) {
    selectRepo(state.filtered[0].repo_id);
  }
}

init();
