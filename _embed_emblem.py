# -*- coding: utf-8 -*-
"""Вставляет любое изображение в SVG 64×64 как base64 (1:1).

Пример:
    python _embed_emblem.py --image subaru.png
    python _embed_emblem.py --image subaru.png --out front/games/profile/emblems/subaru.svg
"""
from __future__ import annotations

import argparse
import base64
import io
from pathlib import Path

from PIL import Image

DEFAULT_OUT = Path("front/games/profile/emblems/subaru.svg")


def main() -> int:
    parser = argparse.ArgumentParser(description="Вставить фото в SVG 64x64")
    parser.add_argument("--image", required=True, help="исходное изображение")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="куда записать SVG")
    args = parser.parse_args()

    source = Path(args.image)
    image = Image.open(source).convert("RGBA")
    image.thumbnail((64, 64), Image.LANCZOS)
    canvas = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    canvas.paste(image, ((64 - image.width) // 2, (64 - image.height) // 2), image)
    buffer = io.BytesIO()
    canvas.save(buffer, "PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'viewBox="0 0 64 64" width="64" height="64">\n'
        f'  <image x="0" y="0" width="64" height="64" '
        f'xlink:href="data:image/png;base64,{encoded}"/>\n'
        '</svg>\n'
    )
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg, encoding="utf-8")
    print(f"{target}: {len(svg)} байт, 64x64")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())