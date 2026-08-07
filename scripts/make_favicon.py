#!/usr/bin/env python3
"""Generate web/favicon.ico — a light-blue plane facing RIGHT on the dark-blue bg.

Plane = --accent (#4da3ff), bg = --bg (#0b1020). The silhouette is drawn upward,
rotated to face right, cropped to its content, then scaled to fill the icon
edge-to-edge (so no dark/blank margin shows in the tab).
"""
from pathlib import Path

from PIL import Image, ImageDraw

BG = (11, 16, 32, 255)       # #0b1020
PLANE = (77, 163, 255, 255)  # #4da3ff
SS = 1024                    # supersample canvas
FILL = 0.98                  # fraction of the icon the plane spans
OUT = Path(__file__).resolve().parents[1] / "web" / "favicon.ico"

# Right half of an upward-pointing jet (x>=0.5), nose -> tail; left half mirrored.
RIGHT = [
    (0.500, 0.060), (0.548, 0.300), (0.955, 0.575), (0.955, 0.660),
    (0.560, 0.520), (0.560, 0.790), (0.790, 0.930), (0.790, 0.980),
    (0.520, 0.855), (0.500, 0.965),
]


def main() -> None:
    # 1. draw the plane (upward) on a transparent layer
    layer = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    pts = RIGHT + [(1 - x, y) for x, y in reversed(RIGHT)]
    ImageDraw.Draw(layer).polygon([(x * SS, y * SS) for x, y in pts], fill=PLANE)

    # 2. face right, then crop to the plane's actual bounds
    layer = layer.transpose(Image.ROTATE_270)   # 90° clockwise: nose up -> nose right
    plane = layer.crop(layer.getbbox())

    # 3. scale to fill the icon and paste centered on the dark background
    canvas = Image.new("RGBA", (SS, SS), BG)
    pw, ph = plane.size
    scale = min(SS * FILL / pw, SS * FILL / ph)
    plane = plane.resize((round(pw * scale), round(ph * scale)), Image.LANCZOS)
    nw, nh = plane.size
    canvas.alpha_composite(plane, ((SS - nw) // 2, (SS - nh) // 2))

    base = canvas.resize((256, 256), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    base.save(OUT, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    base.resize((64, 64), Image.LANCZOS).save(OUT.parent / "favicon-64.png")
    print("wrote", OUT, "and favicon-64.png")


if __name__ == "__main__":
    main()
