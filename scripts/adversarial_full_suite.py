"""Full T1-T5 adversarial transformation suite for the shipped probe.

Extends scripts/adversarial_test.py (which covered T1 + T3) to all five
transformations from the research report (Bailey et al. arXiv 2412.09565;
Risse & Bohme SLODA, FSE 2025):

  T1 identifier rename (sink):  db.query -> database.execute, etc.
  T2 source rename:             req.params.* -> destructured local;
                                process.argv / sys.argv -> cfg.input;
                                input(...), os.environ, request.args, etc.
  T3 whitespace + comment:      insert benign comment + re-indent.
  T4 dead code insertion:       prepend an unrelated safe helper + wrap
                                vuln in `if (false) { ... }` block.
                                Language-aware (JS vs Python).
  T5 SQL keyword case + concat: SELECT/WHERE -> lowercase; template-literal
                                <-> string concatenation (lexical-level).

Methodology:
  We deliberately reuse the EXACT same 20 vulnerable examples that
  scripts/adversarial_test.py sampled (seed=7) by reading the
  per_example.row_idx list from data/adversarial_eval.json and pulling
  the original code from data/pairs.jsonl. This gives an apples-to-apples
  comparison against the baseline + T1 + T3 numbers already in
  data/adversarial_eval.json.

Output: data/adversarial_full_suite.json (same schema, plus t2/t4/t5 keys).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import torch


MODEL_ID_DEFAULT = "google/gemma-4-E2B-it"


# ------------------------------------------------------------------
# T1 -- identifier rename (sink). Kept identical to adversarial_test.py
# so we can sanity-check our reproduction against the shipped numbers.
# ------------------------------------------------------------------
T1_RULES: list[tuple[str, str]] = [
    (r"\bdb\.query\b",       "database.execute"),
    (r"\bpool\.query\b",     "client.run"),
    (r"\bcursor\.execute\b", "db.run"),
    (r"\breq\.params\.id\b", "userId"),
    (r"\brequest\.args\b",   "incomingArgs"),
]


def apply_t1(code: str) -> tuple[str, int]:
    new = code
    n = 0
    for pat, repl in T1_RULES:
        new, k = re.subn(pat, repl, new)
        n += k
    return new, n


# ------------------------------------------------------------------
# T2 -- *source* rename. Hits the attacker-controlled input boundary
# instead of the sink. Distinct from T1.
# ------------------------------------------------------------------
T2_RULES: list[tuple[str, str]] = [
    # JS / Express-style sources
    (r"\breq\.params\.id\b",       "userId"),
    (r"\breq\.params\.([A-Za-z_]\w*)\b", r"local_\1"),
    (r"\breq\.body\.([A-Za-z_]\w*)\b",   r"payload_\1"),
    (r"\breq\.query\.([A-Za-z_]\w*)\b",  r"q_\1"),
    (r"\breq\.headers\.([A-Za-z_]\w*)\b", r"hdr_\1"),
    (r"\brequest\.args\b",         "incomingArgs"),
    (r"\brequest\.form\b",         "submittedForm"),
    (r"\bprocess\.argv\b",         "cfg.input"),
    (r"\bprocess\.env\b",          "cfg.env"),
    # Python sources
    (r"\bsys\.argv\b",             "cfg.input"),
    (r"\bos\.environ\b",           "cfg.env"),
    (r"\bos\.getenv\(",            "cfg.lookup("),
    (r"\brequest\.values\b",       "incomingValues"),
    # raw_input/input() readers
    (r"\binput\(",                 "cfg.read("),
    # File-handle / stream reads (taint sources for a number of CWE-78/94 cases)
    (r"\b([A-Za-z_]\w*)\.readline\(\)", r"\1.next_line()"),
    (r"\b([A-Za-z_]\w*)\.read\(\)",     r"\1.load()"),
]


def apply_t2(code: str) -> tuple[str, int]:
    new = code
    n = 0
    for pat, repl in T2_RULES:
        new, k = re.subn(pat, repl, new)
        n += k
    return new, n


# ------------------------------------------------------------------
# T3 -- whitespace + comment (already in adversarial_test.py).
# ------------------------------------------------------------------
def apply_t3(code: str, lang: str | None) -> str:
    comment = "// pre-validated by upstream middleware"
    if lang and lang.lower() in {"python", "py", "ruby", "rb", "yaml", "yml", "shell", "sh", "bash"}:
        comment = "# pre-validated by upstream middleware"

    lines = code.split("\n")
    out_lines: list[str] = []
    inserted = False
    for ln in lines:
        if not inserted and ln.strip():
            out_lines.append(comment)
            out_lines.append("")
            inserted = True
        out_lines.append("  " + ln if ln else ln)
    if not inserted:
        out_lines = [comment, ""] + ["  " + ln if ln else ln for ln in lines]
    return "\n".join(out_lines)


# ------------------------------------------------------------------
# T4 -- dead code insertion. Tests robustness to attention dilution.
# Prepend an unrelated safe helper, then wrap the original code in an
# unreachable `if (false) { ... }` block AND keep the original code
# directly afterwards so semantics are preserved. The probe still has
# to localise the dangerous line amid the noise.
# ------------------------------------------------------------------
def apply_t4(code: str, lang: str | None) -> str:
    is_python = bool(lang and lang.lower() in {"python", "py"})

    if is_python:
        helper = (
            "def _safe_helper():\n"
            "    # benign utility unrelated to the operation below\n"
            "    total = 0\n"
            "    for k in range(3):\n"
            "        total += k\n"
            "    return total\n"
            "\n"
            "if False:\n"
            "    # dead branch -- never executes\n"
            "    placeholder_value = _safe_helper()\n"
            "    placeholder_text = 'unused diagnostic string'\n"
            "    debug_flag = bool(placeholder_value)\n"
            "\n"
        )
    else:
        helper = (
            "function _safeHelper() {\n"
            "  // benign utility unrelated to the operation below\n"
            "  let total = 0;\n"
            "  for (let k = 0; k < 3; k++) { total += k; }\n"
            "  return total;\n"
            "}\n"
            "\n"
            "if (false) {\n"
            "  // dead branch -- never executes\n"
            "  const placeholderValue = _safeHelper();\n"
            "  const placeholderText = 'unused diagnostic string';\n"
            "  const debugFlag = Boolean(placeholderValue);\n"
            "}\n"
            "\n"
        )
    return helper + code


# ------------------------------------------------------------------
# T5 -- SQL keyword case + concat-style swap. Lexical-only.
# Two sub-rewrites:
#   (a) SQL keywords (SELECT, FROM, WHERE, INSERT, UPDATE, DELETE, etc.)
#       lower-cased when they appear inside string literals.
#   (b) Convert single-line JS template literals `... ${x} ...` to
#       string-concatenation form  '...' + x + '...'.
#       And (best-effort) Python f"...{x}..." -> "..." + str(x) + "..."
# Both are semantics-preserving in our snippet population.
# ------------------------------------------------------------------
_SQL_KEYWORDS = [
    "SELECT", "FROM", "WHERE", "INSERT", "INTO", "VALUES", "UPDATE",
    "DELETE", "JOIN", "INNER", "OUTER", "LEFT", "RIGHT", "ORDER",
    "GROUP", "BY", "HAVING", "UNION", "AND", "OR", "LIKE", "IS", "NULL",
]


def _lower_sql_keywords_in_strlit(s: str) -> str:
    # Find string literals (single, double, backtick). For each, rewrite
    # bare-word SQL keywords to lowercase. We use a tight class for the
    # literal body so we don't accidentally span across literals.
    pat = re.compile(r"""(['"`])((?:\\.|(?!\1).)*)\1""", re.DOTALL)
    kw_re = re.compile(r"\b(" + "|".join(_SQL_KEYWORDS) + r")\b")

    def rewrite(m):
        q, body = m.group(1), m.group(2)
        new_body = kw_re.sub(lambda km: km.group(1).lower(), body)
        return q + new_body + q

    return pat.sub(rewrite, s)


def _template_to_concat_js(s: str) -> tuple[str, int]:
    # `aaa ${x} bbb` -> 'aaa ' + x + ' bbb'
    # We only rewrite single-line template literals (no embedded newlines)
    # to avoid corrupting multi-line tagged templates.
    pat = re.compile(r"`([^`\n]*)`")
    n = 0

    def rewrite(m):
        nonlocal n
        body = m.group(1)
        if "${" not in body:
            # Just a non-interpolating backtick string -> plain quoted str.
            n += 1
            return "'" + body.replace("'", "\\'") + "'"
        # Split on ${...}
        parts: list[str] = []
        i = 0
        while i < len(body):
            j = body.find("${", i)
            if j < 0:
                parts.append(("L", body[i:]))
                break
            if j > i:
                parts.append(("L", body[i:j]))
            # find matching }
            depth = 1
            k = j + 2
            while k < len(body) and depth > 0:
                if body[k] == "{":
                    depth += 1
                elif body[k] == "}":
                    depth -= 1
                k += 1
            expr = body[j + 2 : k - 1]
            parts.append(("E", expr))
            i = k
        out_terms: list[str] = []
        for kind, val in parts:
            if kind == "L":
                if val == "":
                    continue
                out_terms.append("'" + val.replace("'", "\\'") + "'")
            else:
                out_terms.append("(" + val.strip() + ")")
        n += 1
        if not out_terms:
            return "''"
        return " + ".join(out_terms)

    new = pat.sub(rewrite, s)
    return new, n


def _fstring_to_concat_py(s: str) -> tuple[str, int]:
    # f"..." / f'...' on single line -> "..." + str(x) + "..."
    pat = re.compile(r"""f(['"])((?:\\.|(?!\1).)*?)\1""")
    n = 0

    def rewrite(m):
        nonlocal n
        q, body = m.group(1), m.group(2)
        if "{" not in body:
            n += 1
            return q + body + q
        parts: list[str] = []
        i = 0
        while i < len(body):
            j = body.find("{", i)
            if j < 0:
                parts.append(("L", body[i:]))
                break
            if j > i:
                parts.append(("L", body[i:j]))
            depth = 1
            k = j + 1
            while k < len(body) and depth > 0:
                if body[k] == "{":
                    depth += 1
                elif body[k] == "}":
                    depth -= 1
                k += 1
            expr = body[j + 1 : k - 1]
            # Strip any !r / !s / format-spec
            for sep in ("!", ":"):
                if sep in expr:
                    expr = expr.split(sep, 1)[0]
            parts.append(("E", expr))
            i = k
        out_terms: list[str] = []
        for kind, val in parts:
            if kind == "L":
                if val == "":
                    continue
                out_terms.append(q + val + q)
            else:
                out_terms.append("str(" + val.strip() + ")")
        n += 1
        if not out_terms:
            return q + q
        return " + ".join(out_terms)

    new = pat.sub(rewrite, s)
    return new, n


def apply_t5(code: str, lang: str | None) -> tuple[str, dict]:
    sql_before = sum(code.count(k) for k in _SQL_KEYWORDS)
    new = _lower_sql_keywords_in_strlit(code)
    sql_after = sum(new.count(k) for k in _SQL_KEYWORDS)
    sql_hits = sql_before - sql_after

    template_hits = 0
    if lang and lang.lower() in {"python", "py"}:
        new, template_hits = _fstring_to_concat_py(new)
    else:
        new, template_hits = _template_to_concat_js(new)

    return new, {"sql_hits": int(sql_hits), "template_hits": int(template_hits)}


# ------------------------------------------------------------------
# Probe + Gemma plumbing (matches adversarial_test.py exactly).
# ------------------------------------------------------------------
def _sigmoid_arr(x: np.ndarray) -> np.ndarray:
    out = np.empty_like(x, dtype=np.float64)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    e = np.exp(x[~pos])
    out[~pos] = e / (1.0 + e)
    return out


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_probe(probe_path: Path):
    npz = np.load(probe_path)
    return npz["w"].astype(np.float32), float(npz["b"]), int(npz["layer"])


def load_rows(jsonl_path: Path) -> list[dict]:
    rows: list[dict] = []
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def score_snippet(model, tokenizer, device, w, b, layer, code: str, max_length: int = 512) -> tuple[float, float]:
    ids = tokenizer.encode(code, return_tensors="pt", truncation=True, max_length=max_length).to(device)
    with torch.inference_mode():
        out = model(ids, output_hidden_states=True, use_cache=False)
    H = out.hidden_states[layer + 1][0].detach().to("cpu").float().numpy()
    logits = H @ w + b
    risks = _sigmoid_arr(logits)
    return float(risks[-1]), float(risks.max())


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=MODEL_ID_DEFAULT)
    ap.add_argument("--probe", default="data/probe.npz")
    ap.add_argument("--pairs", default="data/pairs.jsonl")
    ap.add_argument(
        "--seed-from",
        default="data/adversarial_eval.json",
        help="Read row_idx list from this JSON (per_example[].row_idx) to "
             "exactly reproduce the existing T1+T3 sample.",
    )
    ap.add_argument("--out", default="data/adversarial_full_suite.json")
    ap.add_argument("--max-length", type=int, default=512)
    args = ap.parse_args()

    w, b, layer = load_probe(Path(args.probe))
    print(f"[adv-full] probe layer={layer} dim={len(w)} b={b:.3f}", file=sys.stderr)

    rows = load_rows(Path(args.pairs))

    seed_report = json.loads(Path(args.seed_from).read_text())
    seed_examples = seed_report["per_example"]
    row_idxs = [e["row_idx"] for e in seed_examples]
    print(f"[adv-full] reusing {len(row_idxs)} examples from {args.seed_from}",
          file=sys.stderr)

    # Pre-compute transforms (cheap, no GPU).
    examples = []
    for gi in row_idxs:
        row = rows[gi]
        code = row["code"]
        lang = row.get("lang")
        t1_code, t1_hits = apply_t1(code)
        t2_code, t2_hits = apply_t2(code)
        t3_code = apply_t3(code, lang)
        t4_code = apply_t4(code, lang)
        t5_code, t5_meta = apply_t5(code, lang)
        examples.append({
            "row_idx": int(gi),
            "lang": lang,
            "cwe": row.get("cwe"),
            "baseline_code": code,
            "t1_code": t1_code, "t1_hits": int(t1_hits),
            "t2_code": t2_code, "t2_hits": int(t2_hits),
            "t3_code": t3_code,
            "t4_code": t4_code,
            "t5_code": t5_code, "t5_sql_hits": t5_meta["sql_hits"],
            "t5_template_hits": t5_meta["template_hits"],
        })

    # Load Gemma.
    from transformers import AutoTokenizer, AutoModelForCausalLM

    device = _device()
    print(f"[adv-full] device={device} model={args.model}", file=sys.stderr)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    dtype = torch.float16 if device != "cpu" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=dtype, attn_implementation="eager"
    )
    model.to(device)
    model.eval()
    print(f"[adv-full] model loaded in {time.time()-t0:.1f}s", file=sys.stderr)

    per_example_results = []
    t_loop = time.time()
    for k, ex in enumerate(examples):
        b_last, b_max = score_snippet(model, tokenizer, device, w, b, layer, ex["baseline_code"], args.max_length)
        t1_last, t1_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t1_code"], args.max_length)
        t2_last, t2_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t2_code"], args.max_length)
        t3_last, t3_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t3_code"], args.max_length)
        t4_last, t4_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t4_code"], args.max_length)
        t5_last, t5_max = score_snippet(model, tokenizer, device, w, b, layer, ex["t5_code"], args.max_length)
        per_example_results.append({
            "row_idx": ex["row_idx"],
            "lang": ex["lang"],
            "cwe": ex["cwe"],
            "t1_hits": ex["t1_hits"],
            "t2_hits": ex["t2_hits"],
            "t5_sql_hits": ex["t5_sql_hits"],
            "t5_template_hits": ex["t5_template_hits"],
            "baseline_last": b_last, "baseline_max": b_max,
            "t1_last": t1_last,       "t1_max": t1_max,
            "t2_last": t2_last,       "t2_max": t2_max,
            "t3_last": t3_last,       "t3_max": t3_max,
            "t4_last": t4_last,       "t4_max": t4_max,
            "t5_last": t5_last,       "t5_max": t5_max,
        })
        if (k + 1) % 5 == 0 or k == 0:
            rate = (k + 1) / max(time.time() - t_loop, 1e-6)
            eta = (len(examples) - (k + 1)) / max(rate, 0.01)
            print(f"[adv-full] {k+1}/{len(examples)}  {rate:.2f} ex/s  eta {eta:.0f}s",
                  file=sys.stderr)

    # Aggregate.
    def _mean(xs):
        return float(np.mean(xs)) if xs else 0.0

    def _flip_rate(scores_after):
        if not scores_after:
            return 0.0
        return float(np.mean([s < 0.5 for s in scores_after]))

    def _argextreme(es, key, baseline_key, kind):
        # Return the (row_idx, baseline, after, delta) with biggest |delta|
        # signed by direction (best = delta near 0 or positive; worst = most negative).
        deltas = [(e["row_idx"], e[baseline_key], e[key], e[key] - e[baseline_key]) for e in es]
        if not deltas:
            return None
        if kind == "worst":
            row = min(deltas, key=lambda t: t[3])
        else:
            row = max(deltas, key=lambda t: t[3])
        return {"row_idx": row[0], "baseline": row[1], "after": row[2], "delta": row[3]}

    baseline_last = [e["baseline_last"] for e in per_example_results]
    baseline_max = [e["baseline_max"] for e in per_example_results]

    transforms = ["t1", "t2", "t3", "t4", "t5"]
    summary: dict[str, dict] = {}
    for t in transforms:
        last = [e[f"{t}_last"] for e in per_example_results]
        mx = [e[f"{t}_max"] for e in per_example_results]
        summary[t] = {
            "mean_score": _mean(last),
            "delta": _mean(last) - _mean(baseline_last),
            "flip_rate": _flip_rate(last),
            "mean_score_maxpool": _mean(mx),
            "delta_maxpool": _mean(mx) - _mean(baseline_max),
            "flip_rate_maxpool": _flip_rate(mx),
            "worst_example_last": _argextreme(per_example_results, f"{t}_last", "baseline_last", "worst"),
            "best_example_last":  _argextreme(per_example_results, f"{t}_last", "baseline_last", "best"),
            "worst_example_max":  _argextreme(per_example_results, f"{t}_max", "baseline_max", "worst"),
            "best_example_max":   _argextreme(per_example_results, f"{t}_max", "baseline_max", "best"),
        }

    # T1/T2/T5 hit-only subsets.
    t1_subset = [e for e in per_example_results if e["t1_hits"] > 0]
    summary["t1"]["hit_subset"] = {
        "n": len(t1_subset),
        "baseline_mean": _mean([e["baseline_last"] for e in t1_subset]),
        "after_mean": _mean([e["t1_last"] for e in t1_subset]),
        "delta": (_mean([e["t1_last"] for e in t1_subset]) - _mean([e["baseline_last"] for e in t1_subset])) if t1_subset else 0.0,
    }
    t2_subset = [e for e in per_example_results if e["t2_hits"] > 0]
    summary["t2"]["hit_subset"] = {
        "n": len(t2_subset),
        "baseline_mean": _mean([e["baseline_last"] for e in t2_subset]),
        "after_mean": _mean([e["t2_last"] for e in t2_subset]),
        "delta": (_mean([e["t2_last"] for e in t2_subset]) - _mean([e["baseline_last"] for e in t2_subset])) if t2_subset else 0.0,
    }
    t5_subset = [e for e in per_example_results if (e["t5_sql_hits"] + e["t5_template_hits"]) > 0]
    summary["t5"]["hit_subset"] = {
        "n": len(t5_subset),
        "baseline_mean": _mean([e["baseline_last"] for e in t5_subset]),
        "after_mean": _mean([e["t5_last"] for e in t5_subset]),
        "delta": (_mean([e["t5_last"] for e in t5_subset]) - _mean([e["baseline_last"] for e in t5_subset])) if t5_subset else 0.0,
    }

    report = {
        "n_examples": len(per_example_results),
        "seed_source": str(args.seed_from),
        "model": args.model,
        "probe_layer": layer,
        "baseline_mean_score": _mean(baseline_last),
        "baseline_mean_score_maxpool": _mean(baseline_max),
        "t1_rename": summary["t1"],
        "t2_source": summary["t2"],
        "t3_comment": summary["t3"],
        "t4_deadcode": summary["t4"],
        "t5_caseconcat": summary["t5"],
        "per_example": per_example_results,
    }

    # Markdown table.
    def fmt_delta(x):
        return f"{x:+.3f}"

    labels = {
        "t1": "T1 rename",
        "t2": "T2 src",
        "t3": "T3 comm",
        "t4": "T4 dead",
        "t5": "T5 case",
    }
    print()
    print("| transform | mean Δ (last) | mean Δ (max-pool) | flip-rate (last) | flip-rate (max-pool) |")
    print("|-----------|---------------|--------------------|------------------|----------------------|")
    for t in transforms:
        s = summary[t]
        print(f"| {labels[t]:<9} | {fmt_delta(s['delta']):>13} | {fmt_delta(s['delta_maxpool']):>18} | {s['flip_rate']:>16.2f} | {s['flip_rate_maxpool']:>20.2f} |")
    print()
    print(f"[adv-full] baseline   last-token mean={_mean(baseline_last):.3f}  max-pool mean={_mean(baseline_max):.3f}")
    print(f"[adv-full] T1 hit-subset n={summary['t1']['hit_subset']['n']}  Δ={summary['t1']['hit_subset']['delta']:+.3f}")
    print(f"[adv-full] T2 hit-subset n={summary['t2']['hit_subset']['n']}  Δ={summary['t2']['hit_subset']['delta']:+.3f}")
    print(f"[adv-full] T5 hit-subset n={summary['t5']['hit_subset']['n']}  Δ={summary['t5']['hit_subset']['delta']:+.3f}")

    out_path = Path(args.out)
    out_path.write_text(json.dumps(report, indent=2))
    print(f"[adv-full] wrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
