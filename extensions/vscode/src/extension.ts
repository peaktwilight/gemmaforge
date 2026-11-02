import * as vscode from "vscode";
import * as http from "http";
import * as https from "https";
import { URL } from "url";

// Risk threshold above which we flag a token's line as suspicious.
const RISK_THRESHOLD = 0.7;
// Exponential moving average factor for smoothing per-token risk.
const EMA_ALPHA = 0.4;

interface TokenEvent {
  event: string;
  token?: string;
  risk?: number;
  risk_raw?: number;
  step?: number;
}

let warningDecoration: vscode.TextEditorDecorationType;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
  warningDecoration = vscode.window.createTextEditorDecorationType({
    textDecoration: "underline wavy red",
    overviewRulerColor: "red",
    overviewRulerLane: vscode.OverviewRulerLane.Right,
    backgroundColor: "rgba(255, 0, 0, 0.08)",
  });

  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100,
  );
  statusBarItem.text = "$(shield) GemmaForge: idle";
  statusBarItem.tooltip = "GemmaForge peak risk of last probe run";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem, warningDecoration);

  const cmd = vscode.commands.registerCommand(
    "gemmaforge.probeSelection",
    async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("GemmaForge: no active editor.");
        return;
      }
      const selection = editor.selection;
      const prompt = editor.document.getText(selection).trim();
      if (!prompt) {
        vscode.window.showWarningMessage(
          "GemmaForge: select some text first.",
        );
        return;
      }

      const cfg = vscode.workspace.getConfiguration("gemmaforge");
      const baseUrl: string = cfg.get("serverUrl", "http://localhost:8787");

      statusBarItem.text = "$(sync~spin) GemmaForge: streaming...";
      const startLine = selection.start.line;
      const endLine = selection.end.line;
      const flaggedLines = new Set<number>();
      let peakRisk = 0;
      let ema = 0;
      let tokenIdx = 0;

      try {
        const destination = new URL(baseUrl).origin;
        if (destination !== "http://localhost:8787") {
          const confirmation = await vscode.window.showWarningMessage(
            `GemmaForge will send the selected text to ${destination}. Continue?`,
            { modal: true },
            "Send selection",
          );
          if (confirmation !== "Send selection") {
            statusBarItem.text = "$(shield) GemmaForge: idle";
            return;
          }
        }

        await streamSSE(baseUrl, prompt, (evt) => {
          if (evt.event !== "token" || typeof evt.risk !== "number") return;
          ema = tokenIdx === 0 ? evt.risk : EMA_ALPHA * evt.risk + (1 - EMA_ALPHA) * ema;
          tokenIdx++;
          if (ema > peakRisk) peakRisk = ema;
          // PoC: tokens don't map 1:1 to source positions, so we colour
          // selection lines proportionally to where we are in the stream.
          if (ema >= RISK_THRESHOLD) {
            const span = Math.max(1, endLine - startLine + 1);
            const lineIdx = startLine + (tokenIdx % span);
            flaggedLines.add(lineIdx);
            applyDecorations(editor, flaggedLines);
          }
          statusBarItem.text = `$(shield) GemmaForge: peak ${peakRisk.toFixed(2)}`;
        });
        statusBarItem.text = `$(shield) GemmaForge: peak ${peakRisk.toFixed(2)}`;
        if (peakRisk >= RISK_THRESHOLD) {
          vscode.window.showWarningMessage(
            `GemmaForge flagged this selection (peak risk ${peakRisk.toFixed(2)}).`,
          );
        } else {
          vscode.window.showInformationMessage(
            `GemmaForge clean (peak risk ${peakRisk.toFixed(2)}).`,
          );
        }
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        statusBarItem.text = "$(error) GemmaForge: error";
        vscode.window.showErrorMessage(`GemmaForge probe failed: ${msg}`);
      }
    },
  );
  context.subscriptions.push(cmd);
}

function applyDecorations(editor: vscode.TextEditor, lines: Set<number>) {
  const ranges: vscode.DecorationOptions[] = [];
  for (const line of lines) {
    if (line < 0 || line >= editor.document.lineCount) continue;
    const text = editor.document.lineAt(line);
    ranges.push({
      range: text.range,
      hoverMessage: "GemmaForge: high streaming-probe risk on this line.",
    });
  }
  editor.setDecorations(warningDecoration, ranges);
}

function streamSSE(
  baseUrl: string,
  prompt: string,
  onEvent: (evt: TokenEvent) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const url = new URL("/stream", baseUrl);
    url.searchParams.set("prompt", prompt);
    const client = url.protocol === "https:" ? https : http;
    const req = client.get(url.toString(), { headers: { Accept: "text/event-stream" } }, (res) => {
      if (res.statusCode && res.statusCode >= 400) {
        reject(new Error(`HTTP ${res.statusCode}`));
        res.resume();
        return;
      }
      let buf = "";
      res.setEncoding("utf8");
      res.on("data", (chunk: string) => {
        buf += chunk;
        let idx: number;
        while ((idx = buf.indexOf("\n\n")) !== -1) {
          const frame = buf.slice(0, idx);
          buf = buf.slice(idx + 2);
          for (const line of frame.split("\n")) {
            if (!line.startsWith("data:")) continue;
            const payload = line.slice(5).trim();
            if (!payload) continue;
            try {
              onEvent(JSON.parse(payload) as TokenEvent);
            } catch {
              // ignore malformed frame
            }
          }
        }
      });
      res.on("end", () => resolve());
      res.on("error", reject);
    });
    req.on("error", reject);
    req.setTimeout(60_000, () => req.destroy(new Error("SSE timeout")));
  });
}

export function deactivate() {
  warningDecoration?.dispose();
  statusBarItem?.dispose();
}
