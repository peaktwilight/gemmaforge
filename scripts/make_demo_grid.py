"""Assemble the four demo screenshots into a 2x2 grid for the writeup.

Reads the four ``scene-NN-*.png`` files produced by ``scripts/record_demo.py``
from ``demo-recordings/`` and pastes them into a single 2800x1800 image at
``web/demo-grid.png`` for use as the "demo at a glance" figure.

Usage::

    python scripts/make_demo_grid.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.stderr.write("Pillow not installed. Run: pip install pillow\n")
    sys.exit(2)


ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = ROOT / "demo-recordings"
OUTPUT_PATH = ROOT / "web" / "demo-grid.png"

GRID_W, GRID_H = 2800, 1800
CELL_W, CELL_H = GRID_W // 2, GRID_H // 2  # 1400 x 900 — matches viewport

# Filenames matching the slugs written by record_demo.py, in reading order.
SCENE_FILES = [
    "scene-01-cwe89-quick-and-dirty.png",
    "scene-02-safe-production-grade.png",
    "scene-03-cwe78-quick-ping.png",
    "scene-04-cwe22-quick-file-reader.png",
]


def main() -> int:
    if not INPUT_DIR.is_dir():
        sys.stderr.write(
            f"No demo-recordings directory at {INPUT_DIR}. "
            "Run scripts/record_demo.py first.\n"
        )
        return 1

    missing = [f for f in SCENE_FILES if not (INPUT_DIR / f).is_file()]
    if missing:
        sys.stderr.write(
            "Missing scene screenshots:\n  - "
            + "\n  - ".join(missing)
            + "\nRun scripts/record_demo.py first.\n"
        )
        return 1

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    grid = Image.new("RGB", (GRID_W, GRID_H), color=(7, 9, 12))  # match panel bg
    for i, name in enumerate(SCENE_FILES):
        row, col = divmod(i, 2)
        img = Image.open(INPUT_DIR / name).convert("RGB")
        # device_scale_factor=2 in record_demo produces ~2800x1800 pixel images.
        # Resize to the target cell while preserving aspect ratio.
        if img.size != (CELL_W, CELL_H):
            img = img.resize((CELL_W, CELL_H), Image.LANCZOS)
        grid.paste(img, (col * CELL_W, row * CELL_H))

    grid.save(OUTPUT_PATH, format="PNG", optimize=True)
    size_kb = OUTPUT_PATH.stat().st_size // 1024
    print(f"wrote {OUTPUT_PATH} ({GRID_W}x{GRID_H}, {size_kb} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
