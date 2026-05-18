"""Stream Gemma 4 generation while scoring each token with the vuln probe.

Backend: HuggingFace transformers + MPS (matches `extract_activations.py`
so the probe trained on those activations transfers verbatim at inference
time — no representation mismatch).

For each generation step:
  1. Forward pass with output_hidden_states=True over the cached context.
  2. Take logits[-1] → next token.
  3. Take hidden_states[probe_layer+1][:, -1, :] → probe input.
  4. risk = sigmoid(w · h + b) → emit {token, risk}.

Usage:
  python -m src.stream_with_probe --prompt "Write an Express handler…"
  python -m src.stream_with_probe --serve
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from typing import Iterator

import numpy as np
import torch


def _device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def _load_probe(probe_path: Path) -> tuple[np.ndarray, float, int]:
    npz = np.load(probe_path)
    return npz["w"].astype(np.float32), float(npz["b"]), int(npz["layer"])


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + float(np.exp(-x)))
    e = float(np.exp(x))
    return e / (1.0 + e)


_cached: dict = {}


def _ensure_model(model_id: str):
    if "model" in _cached and _cached["model_id"] == model_id:
        return _cached["model"], _cached["tokenizer"], _cached["device"]
    from transformers import AutoModelForCausalLM, AutoTokenizer

    device = _device()
    print(f"[stream] loading {model_id} on {device}…", file=sys.stderr)
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    dtype = torch.float16 if device != "cpu" else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        model_id, dtype=dtype, attn_implementation="eager"
    )
    model.to(device)
    model.eval()
    print(f"[stream] loaded in {time.time()-t0:.1f}s", file=sys.stderr)
    _cached.update(model=model, tokenizer=tokenizer, device=device, model_id=model_id)
    return model, tokenizer, device


def stream(
    model_id: str,
    probe_path: Path,
    prompt: str,
    max_new_tokens: int = 200,
    temperature: float = 0.7,
) -> Iterator[dict]:
    model, tokenizer, device = _ensure_model(model_id)
    w, b, layer = _load_probe(probe_path)
    print(f"[stream] probe layer={layer} dim={len(w)} b={b:.3f}", file=sys.stderr)

    try:
        messages = [{"role": "user", "content": prompt}]
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        formatted = prompt

    input_ids = tokenizer.encode(formatted, return_tensors="pt").to(device)
    eos_id = tokenizer.eos_token_id

    # KV-cached streaming: prime the cache with the full prompt once, then
    # feed one token at a time and keep the cache alive. Cuts per-token cost
    # from O(seq_len) to O(1) attention ops.
    #
    # The probe is trained on SNIPPET-LEVEL last-token activations, so
    # per-token scores during streaming are noisy. We surface BOTH the
    # raw per-token risk and a sliding-window mean. The UI uses the smoothed
    # value for coloring (visually stable) and reports the raw for stats.
    SMOOTH_WIN = 8
    window: list[float] = []

    with torch.inference_mode():
        out = model(input_ids, output_hidden_states=True, use_cache=True)
        past_kv = out.past_key_values
        logits = out.logits[0, -1, :]

        for step in range(max_new_tokens):
            if temperature <= 0:
                next_id = int(torch.argmax(logits).item())
            else:
                probs = torch.softmax(logits / temperature, dim=-1)
                next_id = int(torch.multinomial(probs, 1).item())

            hs = out.hidden_states
            h = hs[layer + 1][0, -1, :].detach().to("cpu").float().numpy()
            raw_risk = _sigmoid(float(np.dot(w, h) + b))

            window.append(raw_risk)
            if len(window) > SMOOTH_WIN:
                window.pop(0)
            smooth_risk = sum(window) / len(window)

            try:
                tok_text = tokenizer.decode([next_id])
            except Exception:
                tok_text = "?"

            # `risk` is what the UI uses for color; `risk_raw` is per-token.
            yield {
                "event": "token",
                "token": tok_text,
                "risk": smooth_risk,
                "risk_raw": raw_risk,
                "step": step,
            }

            if eos_id is not None and next_id == eos_id:
                yield {"event": "done", "reason": "eos"}
                return

            # Feed the new token alone with the kept cache.
            step_ids = torch.tensor([[next_id]], device=device)
            out = model(
                step_ids,
                past_key_values=past_kv,
                output_hidden_states=True,
                use_cache=True,
            )
            past_kv = out.past_key_values
            logits = out.logits[0, -1, :]

    yield {"event": "done", "reason": "max_tokens"}


def main_cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="google/gemma-4-E2B-it")
    ap.add_argument("--probe", default="data/probe.npz")
    ap.add_argument("--prompt", required=False)
    ap.add_argument("--max-tokens", type=int, default=150)
    ap.add_argument("--temperature", type=float, default=0.6)
    ap.add_argument("--serve", action="store_true", help="Run as HTTP/SSE server on :8787")
    args = ap.parse_args()

    if args.serve:
        run_server(args)
        return

    if not args.prompt:
        print("--prompt required (or use --serve)", file=sys.stderr)
        sys.exit(2)

    for event in stream(args.model, Path(args.probe), args.prompt, args.max_tokens, args.temperature):
        if event.get("event") == "token":
            risk = event["risk"]
            colour = "\033[31m" if risk > 0.7 else "\033[33m" if risk > 0.4 else "\033[32m"
            sys.stdout.write(f"{colour}{event['token']}\033[0m")
            sys.stdout.flush()
        elif event.get("event") == "done":
            sys.stdout.write("\n")


def run_server(args) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from urllib.parse import urlparse, parse_qs
    import os

    print("[serve] preloading model…", file=sys.stderr)
    _ensure_model(args.model)

    web_dir = Path(__file__).resolve().parent.parent / "web"

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *largs):
            sys.stderr.write("[serve] " + fmt % largs + "\n")

        def _cors(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def do_OPTIONS(self):
            self.send_response(204)
            self._cors()
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/" or parsed.path == "/index.html":
                p = web_dir / "index.html"
                if p.exists():
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self._cors()
                    self.end_headers()
                    self.wfile.write(p.read_bytes())
                else:
                    self.send_response(404)
                    self._cors()
                    self.end_headers()
                return
            if parsed.path != "/stream":
                self.send_response(404)
                self._cors()
                self.end_headers()
                self.wfile.write(b"not found")
                return
            qs = parse_qs(parsed.query)
            prompt = qs.get("prompt", [""])[0]
            max_tokens = int(qs.get("max_tokens", ["150"])[0])
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self._cors()
            self.end_headers()
            try:
                for event in stream(args.model, Path(args.probe), prompt, max_tokens, args.temperature):
                    self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
                    self.wfile.flush()
            except Exception as e:
                self.wfile.write(f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n".encode())

    server = ThreadingHTTPServer(("0.0.0.0", 8787), Handler)
    print("[serve] listening on http://0.0.0.0:8787/  (UI: /  · SSE: /stream?prompt=…)", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main_cli()
