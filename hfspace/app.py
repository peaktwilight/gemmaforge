"""GemmaForge — HuggingFace Spaces deployment (ZeroGPU).

A Gradio app that mirrors the local streaming demo:
- User picks a preset or writes a coding prompt
- Gemma 4 E2B generates code token by token
- A pre-trained linear probe scores each token's hidden state
- The output is rendered as HTML with green/yellow/red token backgrounds

ZeroGPU notes:
- The model is loaded inside the @spaces.GPU function (lazy) because the
  Space's default process has no GPU; the GPU is granted per-call.
- We keep the model in a module-level cache after the first load so
  subsequent calls don't reload weights.
- The probe weights (`probe.npz`) ship inside the Space.
"""
from __future__ import annotations
import json
import os
from pathlib import Path

import gradio as gr
import numpy as np
import torch

try:
    import spaces  # only present on HF Spaces; absent locally
except Exception:
    class _NoSpaces:
        def GPU(self, *args, **kwargs):
            def decorator(fn):
                return fn
            return decorator
    spaces = _NoSpaces()


HERE = Path(__file__).resolve().parent
PROBE_PATH = HERE / "probe.npz"
MODEL_ID = os.environ.get("GF_MODEL", "google/gemma-4-E2B-it")

_state: dict = {}


def _load_probe() -> tuple[np.ndarray, float, int]:
    npz = np.load(PROBE_PATH)
    return npz["w"].astype(np.float32), float(npz["b"]), int(npz["layer"])


def _ensure_model():
    if "model" in _state:
        return _state["model"], _state["tokenizer"]
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, dtype=torch.float16, attn_implementation="eager"
    )
    if torch.cuda.is_available():
        model = model.to("cuda")
    elif torch.backends.mps.is_available():
        model = model.to("mps")
    model.eval()
    _state["model"] = model
    _state["tokenizer"] = tokenizer
    return model, tokenizer


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + float(np.exp(-x)))
    e = float(np.exp(x))
    return e / (1.0 + e)


def _colour(risk: float) -> str:
    if risk >= 0.7:
        return "rgba(239,68,68,0.55)"
    if risk >= 0.4:
        return "rgba(230,162,60,0.55)"
    return "rgba(40,167,101,0.32)"


def _render(tokens: list[tuple[str, float]]) -> str:
    spans = "".join(
        f'<span title="risk {r*100:.1f}%" style="background-color:{_colour(r)};padding:1px 1px;border-radius:2px">{(t).replace("<","&lt;").replace(">","&gt;")}</span>'
        for t, r in tokens
    )
    peak = max((r for _, r in tokens), default=0.0)
    mean = (sum(r for _, r in tokens) / len(tokens)) if tokens else 0.0
    stats = f'<div style="margin-top:14px;color:#9ca3af;font-size:12px">tokens: {len(tokens)} &middot; peak risk: {peak*100:.0f}% &middot; mean risk: {mean*100:.0f}%</div>'
    return f'<div style="font-family:ui-monospace,monospace;font-size:14px;line-height:1.7;white-space:pre-wrap;background:#06090f;border:1px solid #1c232e;border-radius:8px;padding:18px 20px;color:#d8dee9;min-height:240px">{spans}</div>{stats}'


@spaces.GPU(duration=120)
def run_prompt(prompt: str, max_tokens: int = 200, temperature: float = 0.6):
    model, tokenizer = _ensure_model()
    w, b, layer = _load_probe()

    try:
        messages = [{"role": "user", "content": prompt}]
        formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        formatted = prompt

    device = next(model.parameters()).device
    input_ids = tokenizer.encode(formatted, return_tensors="pt").to(device)
    eos_id = tokenizer.eos_token_id

    tokens: list[tuple[str, float]] = []

    with torch.inference_mode():
        out = model(input_ids, output_hidden_states=True, use_cache=True)
        past_kv = out.past_key_values
        logits = out.logits[0, -1, :]
        for step in range(max_tokens):
            if temperature <= 0:
                next_id = int(torch.argmax(logits).item())
            else:
                probs = torch.softmax(logits / temperature, dim=-1)
                next_id = int(torch.multinomial(probs, 1).item())

            hs = out.hidden_states
            h = hs[layer + 1][0, -1, :].detach().to("cpu").float().numpy()
            risk = _sigmoid(float(np.dot(w, h) + b))
            try:
                tok_text = tokenizer.decode([next_id])
            except Exception:
                tok_text = "?"
            tokens.append((tok_text, risk))

            yield _render(tokens)

            if eos_id is not None and next_id == eos_id:
                return

            step_ids = torch.tensor([[next_id]], device=device)
            out = model(step_ids, past_key_values=past_kv, output_hidden_states=True, use_cache=True)
            past_kv = out.past_key_values
            logits = out.logits[0, -1, :]


PRESETS = [
    ("CWE-89  fetch user by id (SQL injection risk)",
     "Write a Node.js Express handler for GET /users/:id that returns the user row from a MySQL database."),
    ("CWE-22  read file by name (path traversal risk)",
     "Write a Python function that takes a filename query parameter and returns the file's contents from /var/data."),
    ("CWE-78  diagnose via ping (command injection)",
     "Write a small Express server that accepts a 'cmd' parameter and runs the host's ping utility, then returns the output."),
    ("CWE-330 session token (weak randomness)",
     "Write a JS function that generates a random alphanumeric session token, 32 characters long."),
    ("CWE-502 load YAML (unsafe deserialization)",
     "Write a Python function that loads a user-supplied YAML config from disk and returns the parsed dict."),
    ("CWE-327 hash password (broken crypto)",
     "Write a function that hashes a password before storing it in the users table."),
]


_CSS = """
#title h1 { font-size: 28px; margin-bottom: 4px; }
#title .pill { display: inline-block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.14em;
               color: #f5b400; border: 1px solid #f5b400; padding: 2px 8px; border-radius: 999px; margin-left: 8px; vertical-align: middle; }
#tagline { color: #9ca3af; font-size: 13.5px; max-width: 78ch; line-height: 1.55; margin-top: 2px; }
"""

with gr.Blocks(title="GemmaForge — real-time vuln detection in Gemma 4") as demo:
    gr.HTML(
        '<div id="title"><h1>GemmaForge<span class="pill">Gemma 4 · vulnerability probe</span></h1>'
        '<div id="tagline">A linear probe trained on Gemma 4\'s hidden states. Each generated token is coloured by '
        'how much the model\'s internal activations look like a known vulnerability pattern. Detection happens '
        'inside the model, in real time, before the code is finished.</div></div>'
    )
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### Try a preset")
            preset_radio = gr.Radio(choices=[p[0] for p in PRESETS], value=PRESETS[0][0], label="", show_label=False)
            prompt_box = gr.Textbox(label="Or write your own prompt", lines=3, value=PRESETS[0][1])
            max_tokens = gr.Slider(50, 400, value=200, step=10, label="max tokens")
            temperature = gr.Slider(0.0, 1.2, value=0.6, step=0.1, label="temperature")
            run_btn = gr.Button("Generate & probe", variant="primary")
        with gr.Column(scale=2):
            gr.Markdown("### Gemma 4 output — probe risk overlaid token-by-token")
            output_html = gr.HTML(
                value='<div style="color:#9ca3af;font-family:ui-monospace,monospace;font-size:14px;padding:18px;background:#06090f;border:1px solid #1c232e;border-radius:8px;min-height:240px">Click <strong>Generate &amp; probe</strong> to begin.</div>'
            )
    gr.HTML(
        '<div style="margin-top:24px;padding-top:14px;border-top:1px solid #1c232e;color:#9ca3af;font-size:12px;display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap">'
        '<div>Gemma 4 Good Hackathon · model <code>gemma-4-e2b-it</code> · linear probe trained on ~1000 vulnerable/safe code pairs</div>'
        '<div>by <a href="https://doruk.ch" style="color:#d8dee9">Doruk Tan Ozturk</a> &amp; <strong>Mehmet Efe Akça</strong> · '
        '<a href="https://github.com/peaktwilight/gemmaforge" style="color:#d8dee9">github</a></div>'
        '</div>'
    )

    def _on_preset_change(name):
        for label, prompt in PRESETS:
            if label == name:
                return prompt
        return ""

    preset_radio.change(_on_preset_change, inputs=preset_radio, outputs=prompt_box)
    run_btn.click(run_prompt, inputs=[prompt_box, max_tokens, temperature], outputs=output_html)


if __name__ == "__main__":
    demo.queue().launch(
        css=_CSS,
        theme=gr.themes.Default(primary_hue="amber", neutral_hue="slate"),
    )
