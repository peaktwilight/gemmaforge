"""Analyse a captured SSE stream from the streaming probe server."""
import json, re, sys

path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/sse-long.txt"
tokens = []
for line in open(path):
    if line.startswith("data:"):
        try:
            d = json.loads(line[5:].strip())
            if d.get("event") == "token":
                tokens.append((d["token"], d["risk"], d.get("risk_raw", 0)))
        except Exception:
            pass

text = "".join(t for t, _, _ in tokens)
print(f"total tokens: {len(tokens)}")
if not tokens:
    print("NO TOKENS — check that the stream returned data")
    sys.exit(1)

sms = [s for _, s, _ in tokens]
peak_i = max(range(len(tokens)), key=lambda i: tokens[i][1])
ctx = "".join(t for t, _, _ in tokens[max(0, peak_i - 8):peak_i + 6])
print(f"smoothed peak: {max(sms)*100:.1f}%   smoothed mean: {sum(sms)/len(sms)*100:.1f}%")
print(f"peak context (step {peak_i}): {ctx!r}")

print("\n--- output excerpt (first 600 chars) ---")
print(text[:600])
print("\n--- output excerpt (last 600 chars) ---")
print(text[-600:])

print("\n--- smoothed timeline (every 25 tokens + all >60%) ---")
shown = set()
for i, (tok, smooth, raw) in enumerate(tokens):
    if i % 25 == 0 or smooth > 0.6:
        if i in shown:
            continue
        shown.add(i)
        print(f"  {i:3d}  S{smooth*100:5.1f}% R{raw*100:5.1f}%  {tok!r}")
