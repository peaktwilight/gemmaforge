"""Ollama-compatible HTTP shim that proxies to Google AI Studio Gemma 4.

Pwnkit's ``--runtime ollama`` posts to ``${OLLAMA_HOST}/api/chat`` with an
Ollama-shaped body. This shim accepts those requests on a configurable
port and forwards them to Google AI Studio's Gemma 4 31B endpoint,
translating both directions (messages, tools, tool calls, usage stats).

Required env var:
    GEMINI_API_KEY            Google AI Studio API key with Gemma access.

Optional env var:
    OLLAMA_SHIM_MODEL         Default Gemma model id (default gemma-4-31b-it).

Endpoints:
    GET  /                    Health / banner
    GET  /api/tags            Mimic Ollama's model list (returns one model).
    POST /api/chat            Translate + forward to Google AI Studio.

Stream mode (``stream: true``) is not implemented — pwnkit's Ollama
runtime sets ``stream: false`` so the non-streaming path is enough.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 11434
DEFAULT_MODEL = os.environ.get("OLLAMA_SHIM_MODEL", "gemma-4-31b-it")
GOOGLE_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _err(msg: str) -> None:
    sys.stderr.write(f"[ollama-shim] {msg}\n")
    sys.stderr.flush()


def _to_google_contents(messages: list[dict]) -> tuple[list[dict], str | None]:
    """Translate Ollama message array → Google `contents` + extracted system instruction.

    Ollama roles: system / user / assistant / tool
    Google roles: user / model      (system goes into `systemInstruction`)

    Tool result messages from Ollama (`role:"tool"`, `name:`, `tool_call_id:`)
    become a Google `user` turn with a `functionResponse` part — Google's
    convention for returning the result of a previous functionCall.
    """
    system_instruction: str | None = None
    contents: list[dict] = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")
        if role == "system":
            system_instruction = (system_instruction or "") + content + "\n"
            continue
        if role == "tool":
            # Ollama tool turn: { role:"tool", name:<func>, content:<result string> }
            name = msg.get("name") or msg.get("tool_call_id") or "tool"
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": name,
                                "response": {"result": content},
                            }
                        }
                    ],
                }
            )
            continue
        # Plain text user / assistant.
        g_role = "model" if role == "assistant" else "user"
        if content.strip():
            contents.append({"role": g_role, "parts": [{"text": content}]})
    return contents, (system_instruction.strip() if system_instruction else None)


def _to_google_tools(ollama_tools: list[dict] | None) -> list[dict] | None:
    """Translate Ollama tools array → Google `tools` (function_declarations)."""
    if not ollama_tools:
        return None
    decls: list[dict] = []
    for t in ollama_tools:
        fn = t.get("function") or {}
        decls.append(
            {
                "name": fn.get("name", "unknown"),
                "description": fn.get("description", ""),
                "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return [{"functionDeclarations": decls}]


def _from_google_response(g_resp: dict, model: str) -> dict:
    """Translate Google AI Studio response → Ollama `/api/chat` response shape."""
    candidates = g_resp.get("candidates") or []
    cand = candidates[0] if candidates else {}
    parts = (cand.get("content") or {}).get("parts") or []

    text_chunks: list[str] = []
    tool_calls: list[dict] = []
    tc_index = 0
    for part in parts:
        if part.get("thought") is True:
            continue  # Gemma 4 emits reasoning traces marked thought=true; suppress.
        if "text" in part and part["text"]:
            text_chunks.append(part["text"])
        elif "functionCall" in part:
            fc = part["functionCall"]
            tool_calls.append(
                {
                    "id": f"call_{tc_index}",
                    "function": {
                        "name": fc.get("name", "unknown"),
                        "arguments": fc.get("args") or {},
                    },
                }
            )
            tc_index += 1

    usage = g_resp.get("usageMetadata") or {}
    finish = cand.get("finishReason", "STOP")
    done_reason = "length" if finish == "MAX_TOKENS" else "stop"

    return {
        "model": model,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "message": {
            "role": "assistant",
            "content": "".join(text_chunks),
            **({"tool_calls": tool_calls} if tool_calls else {}),
        },
        "done": True,
        "done_reason": done_reason,
        "prompt_eval_count": usage.get("promptTokenCount", 0),
        "eval_count": usage.get("candidatesTokenCount", 0),
        "total_duration": 0,
    }


def call_google(model: str, contents: list[dict], system: str | None, tools: list[dict] | None, temperature: float, api_key: str, timeout: float) -> dict:
    body: dict = {"contents": contents}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if tools:
        body["tools"] = tools
    body["generationConfig"] = {"temperature": temperature}

    url = f"{GOOGLE_BASE}/models/{model}:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def make_handler(model: str, api_key: str, timeout: float):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *largs):
            sys.stderr.write("[ollama-shim] " + fmt % largs + "\n")

        def _json(self, status: int, body: dict) -> None:
            data = json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/api/version"):
                self._json(200, {"version": "shim-0.1", "model": model})
                return
            if self.path == "/api/tags":
                self._json(
                    200,
                    {
                        "models": [
                            {
                                "name": model,
                                "model": model,
                                "details": {
                                    "format": "google-ai-studio",
                                    "family": "gemma4",
                                    "parameter_size": "31B",
                                    "quantization_level": "API",
                                },
                                "modified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                "size": 0,
                            }
                        ]
                    },
                )
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self):
            if self.path != "/api/chat":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                req_body = json.loads(raw)
            except json.JSONDecodeError as e:
                self._json(400, {"error": f"invalid json: {e}"})
                return

            req_model = req_body.get("model") or model
            messages = req_body.get("messages") or []
            tools = req_body.get("tools")
            options = req_body.get("options") or {}
            temperature = float(options.get("temperature", 0.0))

            contents, system = _to_google_contents(messages)
            g_tools = _to_google_tools(tools)

            try:
                g_resp = call_google(req_model, contents, system, g_tools, temperature, api_key, timeout)
            except urllib.error.HTTPError as e:
                err_body = e.read().decode("utf-8", errors="replace")
                _err(f"upstream {e.code}: {err_body[:300]}")
                self._json(e.code, {"error": err_body})
                return
            except Exception as e:
                _err(f"upstream error: {e}")
                self._json(502, {"error": str(e)})
                return

            ollama_resp = _from_google_response(g_resp, req_model)
            self._json(200, ollama_resp)

    return Handler


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--timeout", type=float, default=120.0)
    args = ap.parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_API_KEY")
    if not api_key:
        _err("error: GEMINI_API_KEY (or GOOGLE_AI_API_KEY) env var is required")
        return 1

    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.model, api_key, args.timeout))
    _err(f"listening on http://{args.host}:{args.port}/  model={args.model}  upstream=Google AI Studio")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _err("bye")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
