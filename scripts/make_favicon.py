#!/usr/bin/env python3
"""Generate web/favicon.ico — a light-blue plane on the dark-blue brand background.

Colors match the SlotEx theme: plane = --accent (#4da3ff), bg = --bg (#0b1020).
Drawn as a vector silhouette, supersampled for clean edges, saved multi-size.
"""
from pathlib import Path

from PIL import Image, ImageDraw

BG = (11, 16, 32, 255)       # #0b1020
PLANE = (77, 163, 255, 255)  # #4da3ff
SS = 1024                    # supersample canvas
OUT = Path(__file__).resolve().parents[1] / "web" / "favicon.ico"

# Right half of an upward-pointing jet (x>=0.5), nose -> tail; left half is mirrored.
RIGHT = [
    (0.500, 0.060), (0.548, 0.300), (0.955, 0.575), (0.955, 0.660),
    (0.560, 0.520), (0.560, 0.790), (0.790, 0.930), (0.790, 0.980),
    (0.520, 0.855), (0.500, 0.965),
]


def main() -> None:
    img = Image.new("RGBA", (SS, SS), BG)
    d = ImageDraw.Draw(img)
    pts = RIGHT + [(1 - x, y) for x, y in reversed(RIGHT)]
    d.polygon([(x * SS, y * SS) for x, y in pts], fill=PLANE)
    base = img.resize((256, 256), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.save(OUT, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    base.resize((64, 64), Image.LANCZOS).save(OUT.parent / "favicon-64.png")
    print("wrote", OUT, "and favicon-64.png")


if __name__ == "__main__":
    main()
