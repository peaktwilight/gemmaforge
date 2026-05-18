"""Capture the GemmaForge streaming probe demo as timestamped screenshots.

Drives the web UI at http://localhost:8787/ with headless Chromium, clicking
each preset in sequence and writing one PNG per scene to ``demo-recordings/``.
Also captures an animated GIF of the CWE-89 "quick and dirty" run to use as
the hero figure in the hackathon writeup. Closes a chunk of issue #10.

Usage::

    python scripts/record_demo.py

Assumes the streaming server is already running at ``http://localhost:8787/``.
If not, the script exits with a clear error rather than trying to boot it.
"""
from __future__ import annotations

import io
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from playwright.sync_api import TimeoutError as PWTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.stderr.write(
        "playwright not installed. Run:\n"
        "    pip install playwright && playwright install chromium\n"
    )
    sys.exit(2)

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Pillow not installed. Run: pip install pillow\n")
    sys.exit(2)


SERVER_URL = "http://localhost:8787/"
VIEWPORT = {"width": 1400, "height": 900}
MIN_TOKENS_PER_SCENE = 50
# At ~2-2.5s/token on a warm server we want generous headroom for 50 tokens,
# plus a beat for SSE handshake. Empirically 50 tokens lands around 100-130s.
SCENE_TIMEOUT_S = 240
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "demo-recordings"

# Each preset matched by its prompt-data prefix (which is unique per scene).
# Slug + CWE label are used for filenames and the final markdown summary.
SCENES = [
    {
        "slug": "cwe89-quick-and-dirty",
        "label": "CWE-89",
        "prompt_prefix": "Quick and dirty Express handler",
    },
    {
        "slug": "safe-production-grade",
        "label": "SAFE",
        "prompt_prefix": "Now write a production-grade Express handler",
    },
    {
        "slug": "cwe78-quick-ping",
        "label": "CWE-78",
        "prompt_prefix": "A small Express server, just a quick prototype",
    },
    {
        "slug": "cwe22-quick-file-reader",
        "label": "CWE-22",
        "prompt_prefix": "A Python one-liner that reads a file",
    },
]

# GIF capture parameters for the dramatic CWE-89 scene.
GIF_SCENE_SLUG = "cwe89-quick-and-dirty"
GIF_FRAMES = 60
GIF_INTERVAL_S = 0.5
GIF_MAX_WALL_S = 300  # 5-minute hard ceiling per task spec
GIF_FRAME_DURATION_MS = 500


def assert_server_up() -> None:
    """Fail fast with a friendly message if the streaming server is not up."""
    try:
        with urllib.request.urlopen(SERVER_URL, timeout=3) as resp:
            if resp.status != 200:
                raise SystemExit(
                    f"Server at {SERVER_URL} responded {resp.status}; expected 200. "
                    "Start the streaming server first."
                )
    except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
        raise SystemExit(
            f"Cannot reach {SERVER_URL} ({exc}). "
            "Start the GemmaForge streaming server before running this script."
        )


def find_preset(page, prompt_prefix: str):
    """Locate the preset button whose data-prompt starts with the given prefix."""
    selector = f'button.preset[data-prompt^="{prompt_prefix}"]'
    btn = page.locator(selector)
    if btn.count() == 0:
        raise SystemExit(
            f"Could not locate preset button starting with: {prompt_prefix!r}. "
            "Has the UI changed?"
        )
    return btn.first


def read_int(page, selector: str) -> int:
    txt = page.locator(selector).inner_text().strip()
    try:
        return int(txt)
    except ValueError:
        return 0


def read_pct(page, selector: str) -> str:
    """Return raw textual percentage from a stat tile (e.g. '73%')."""
    return page.locator(selector).inner_text().strip() or "0%"


def wait_for_min_tokens(page, n: int, timeout_s: float = SCENE_TIMEOUT_S) -> int:
    """Block until at least ``n`` tokens have streamed or timeout elapses."""
    deadline = time.monotonic() + timeout_s
    last = 0
    while time.monotonic() < deadline:
        last = read_int(page, "#stat-tokens")
        if last >= n:
            return last
        page.wait_for_timeout(150)
    return last


def capture_scene(page, idx: int, scene: dict) -> dict:
    """Click the preset, wait for tokens to flow, snapshot the page."""
    btn = find_preset(page, scene["prompt_prefix"])
    btn.click()
    # The UI resets stats on click; give the SSE handshake a beat to start.
    page.wait_for_timeout(400)

    streamed = wait_for_min_tokens(page, MIN_TOKENS_PER_SCENE)
    if streamed < MIN_TOKENS_PER_SCENE:
        sys.stderr.write(
            f"  warn: scene {idx} ({scene['slug']}) only streamed {streamed} tokens "
            f"before {SCENE_TIMEOUT_S}s timeout (wanted ≥{MIN_TOKENS_PER_SCENE}).\n"
        )

    # Let the meter / colour transitions settle for a clean frame.
    page.wait_for_timeout(600)

    filename = f"scene-{idx:02d}-{scene['slug']}.png"
    out_path = OUTPUT_DIR / filename
    page.screenshot(path=str(out_path), full_page=False)

    peak = read_pct(page, "#stat-peak")
    mean = read_pct(page, "#stat-avg")
    tokens = read_int(page, "#stat-tokens")
    top_cwe = page.locator("#stat-top-cwe").inner_text().strip() or "—"

    print(
        f"  [{idx}/{len(SCENES)}] {scene['label']:7s} "
        f"tokens={tokens:3d} peak={peak} mean={mean} → {filename}"
    )
    return {
        "idx": idx,
        "slug": scene["slug"],
        "label": scene["label"],
        "filename": filename,
        "peak": peak,
        "mean": mean,
        "tokens": tokens,
        "top_cwe": top_cwe,
    }


def capture_gif(page, scene: dict) -> tuple[Path | None, str]:
    """Re-trigger the CWE-89 scene and capture ``GIF_FRAMES`` screenshots into a GIF."""
    btn = find_preset(page, scene["prompt_prefix"])
    btn.click()
    # Wait until the stream is actually pushing tokens before we start grabbing.
    wait_for_min_tokens(page, 3, timeout_s=15)

    frames: list[Image.Image] = []
    start = time.monotonic()
    next_t = start
    while len(frames) < GIF_FRAMES:
        elapsed = time.monotonic() - start
        if elapsed > GIF_MAX_WALL_S:
            return None, (
                f"GIF capture aborted: exceeded {GIF_MAX_WALL_S}s wall budget "
                f"after {len(frames)} frames."
            )
        # Sleep until the next 0.5s tick.
        wait_ms = max(0, int((next_t - time.monotonic()) * 1000))
        if wait_ms:
            page.wait_for_timeout(wait_ms)
        png_bytes = page.screenshot(full_page=False)
        frames.append(Image.open(io.BytesIO(png_bytes)).convert("RGB"))
        next_t += GIF_INTERVAL_S

    # Downscale to keep the GIF embeddable (1400x900 is too heavy for a writeup).
    target_w = 900
    scale = target_w / frames[0].width
    target_h = int(frames[0].height * scale)
    frames = [f.resize((target_w, target_h), Image.LANCZOS) for f in frames]

    gif_path = OUTPUT_DIR / f"scene-cwe89.gif"
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=GIF_FRAME_DURATION_MS,
        loop=0,
        optimize=True,
    )
    return gif_path, f"GIF captured: {len(frames)} frames"


def main() -> int:
    assert_server_up()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"writing screenshots to {OUTPUT_DIR}")

    results: list[dict] = []
    gif_path: Path | None = None
    gif_note = ""
    overall_start = time.monotonic()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
            page = context.new_page()
            page.set_default_timeout(20_000)
            page.goto(SERVER_URL, wait_until="domcontentloaded")
            # Wait for the preset buttons to be wired up.
            page.wait_for_selector("button.preset", state="visible")
            page.wait_for_timeout(400)

            for idx, scene in enumerate(SCENES, start=1):
                try:
                    results.append(capture_scene(page, idx, scene))
                except PWTimeoutError as exc:
                    sys.stderr.write(f"  error in scene {idx}: {exc}\n")

            # Capture animated GIF for the most dramatic scene.
            print("\ncapturing animated GIF (CWE-89, 60 frames × 0.5s = 30s)...")
            gif_scene = next(s for s in SCENES if s["slug"] == GIF_SCENE_SLUG)
            try:
                gif_path, gif_note = capture_gif(page, gif_scene)
            except PWTimeoutError as exc:
                gif_note = f"GIF capture failed: {exc}"
        finally:
            browser.close()

    total = time.monotonic() - overall_start
    print(f"\ntotal capture time: {total:.1f}s")

    # ---- Markdown summary -------------------------------------------------
    print("\n## demo capture summary\n")
    print("| scene | file | tokens | peak risk | mean risk | top CWE |")
    print("| --- | --- | --- | --- | --- | --- |")
    for r in results:
        print(
            f"| {r['label']} | `{r['filename']}` | {r['tokens']} | "
            f"{r['peak']} | {r['mean']} | {r['top_cwe']} |"
        )
    if gif_path is not None:
        size_kb = gif_path.stat().st_size // 1024
        print(f"\n**GIF**: `{gif_path.name}` ({size_kb} KB) — {gif_note}")
    else:
        print(f"\n**GIF**: not produced — {gif_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
