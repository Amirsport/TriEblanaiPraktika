# -*- coding: utf-8 -*-
"""Генерирует иконки PWA (192x192, 512x512, maskable 512x512)."""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "front" / "icons"
OUT.mkdir(parents=True, exist_ok=True)


def leaf_layer(size: int, scale: float = 1.0) -> Image.Image:
    """Рисует лист на прозрачном фоне и возвращает слой размером size x size."""
    import math

    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    cx, cy = size / 2, size / 2
    length = size * 0.62 * scale
    half_w = size * 0.21 * scale

    top, bottom = [], []
    steps = 160
    for i in range(steps + 1):
        t = i / steps
        x = cx + (t - 0.5) * length
        y = math.sin(math.pi * t) ** 0.82 * half_w
        top.append((x, cy - y))
        bottom.append((x, cy + y))

    body = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(body).polygon(top + list(reversed(bottom)), fill=(255, 255, 255, 240))
    body = body.rotate(-38, resample=Image.BICUBIC, center=(cx, cy))
    layer = Image.alpha_composite(layer, body)

    # центральная жилка (вдоль листа)
    blade = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(blade).line(
        [(cx - length * 0.40, cy), (cx + length * 0.40, cy)],
        fill=(79, 154, 72, 255), width=max(2, int(size * 0.016)),
    )
    blade = blade.rotate(-38, resample=Image.BICUBIC, center=(cx, cy))
    layer = Image.alpha_composite(layer, blade)

    # черешок (стебелёк) снизу слева
    stem = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(stem).line(
        [(cx - length * 0.34, cy + length * 0.12), (cx - length * 0.52, cy + length * 0.34)],
        fill=(235, 245, 230, 230), width=max(2, int(size * 0.02)),
    )
    return Image.alpha_composite(layer, stem)


def make_icon(size: int, maskable: bool = False) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # фон: зелёный градиент сверху вниз
    top, bottom = (108, 190, 96), (56, 122, 56)
    for y in range(size):
        ratio = y / max(1, size - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line([(0, y), (size, y)], fill=color + (255,))

    if not maskable:
        return Image.alpha_composite(image, leaf_layer(size, 1.0))

    # maskable: содержимое должно умещаться в безопасную зону (~80 %)
    safe = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    safe.paste(image, (0, 0))
    safe = Image.alpha_composite(safe, leaf_layer(size, 0.62))
    return safe


make_icon(192).save(OUT / "icon-192.png")
make_icon(512).save(OUT / "icon-512.png")
make_icon(512, maskable=True).save(OUT / "icon-maskable-512.png")
print("Иконки созданы:", ", ".join(sorted(p.name for p in OUT.glob("*.png"))))
