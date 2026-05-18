# GemmaForge VS Code Extension (PoC)

Real-time vulnerability-warning overlay backed by the GemmaForge streaming probe.
Advances [GitHub issue #5](https://github.com/peaktwilight/gemmaforge/issues/5).

## What it does

- Adds a command `GemmaForge: Probe current selection`. Select code, run the
  command, and the extension streams the selection through the local
  GemmaForge probe over Server-Sent Events.
- Lines whose smoothed token risk crosses `0.7` get a red wavy underline.
- A status-bar item (right side) shows the peak risk of the most-recent run.

Token-to-character mapping is approximate (PoC, not production): we colour
lines inside the selection by where we are in the token stream rather than
mapping tokens back to source offsets.

## Prerequisites

1. The GemmaForge streaming probe server running locally:
   ```bash
   python -m src.stream_with_probe --serve
   ```
   By default it listens on `http://localhost:8787`. Override via the
   `gemmaforge.serverUrl` setting if you need to point elsewhere.

## Install / run from source

```bash
cd extensions/vscode
npm install
npm run compile
```

Then open this folder in VS Code and press **F5** to launch the Extension
Development Host. In the dev host:

1. Open any file and select a chunk of text (e.g. a suspicious prompt or
   code block).
2. `Cmd-Shift-P` (or `Ctrl-Shift-P` on Linux/Windows) -> `GemmaForge: Probe
   current selection`.
3. Watch the status bar for peak risk; flagged lines get a red wavy
   underline.

## Configuration

| Setting                  | Default                 | Description                              |
| ------------------------ | ----------------------- | ---------------------------------------- |
| `gemmaforge.serverUrl`   | `http://localhost:8787` | Base URL of the GemmaForge probe server. |

## Limitations (known PoC trade-offs)

- No tokenizer round-trip: we don't know which source character each model
  token maps to, so decorations are spread across the selection range.
- One in-flight probe at a time per editor; running the command again
  replaces the previous decorations on the active editor.
- Smoothing is a simple EMA (`alpha=0.4`); the threshold `0.7` is hard-coded.
- No retry / cancellation UI — kill the dev host to abort a stuck stream.
