from __future__ import annotations

import math

from PIL import Image, ImageDraw


def _lerp(a: int, b: int, t: float) -> int:
    return int(a + (b - a) * t)


def _lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    return (_lerp(c1[0], c2[0], t), _lerp(c1[1], c2[1], t), _lerp(c1[2], c2[2], t))


def _draw_sky(img: Image.Image, horizon_y: int) -> None:
    """Небо: тёплые лучи солнца у горизонта, голубое выше."""
    width, _ = img.size
    top = (25, 118, 210)
    mid = (255, 183, 77)
    warm = (255, 224, 130)
    for y in range(horizon_y):
        t = y / max(horizon_y - 1, 1)
        if t < 0.45:
            color = _lerp_color(warm, mid, t / 0.45)
        else:
            color = _lerp_color(mid, top, (t - 0.45) / 0.55)
        ImageDraw.Draw(img).line([(0, y), (width, y)], fill=color)


def _draw_sea(img: Image.Image, horizon_y: int) -> None:
    """Море с лёгким градиентом глубины."""
    width, height = img.size
    surface = (33, 150, 243)
    deep = (13, 71, 161)
    for y in range(horizon_y, height):
        t = (y - horizon_y) / max(height - horizon_y - 1, 1)
        color = _lerp_color(surface, deep, t)
        ImageDraw.Draw(img).line([(0, y), (width, y)], fill=color)


def _draw_sun_rays(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, size: int) -> None:
    """Солнце и лучи над горизонтом."""
    glow = (255, 236, 120)
    core = (255, 249, 196)
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=glow,
    )
    draw.ellipse(
        [cx - radius // 2, cy - radius // 2, cx + radius // 2, cy + radius // 2],
        fill=core,
    )

    ray_len = int(size * 0.42)
    ray_width = max(1, size // 32)
    for angle_deg in range(0, 360, 30):
        angle = math.radians(angle_deg)
        x2 = cx + int(math.cos(angle) * ray_len)
        y2 = cy + int(math.sin(angle) * ray_len)
        draw.line([(cx, cy), (x2, y2)], fill=(255, 213, 79), width=ray_width)


def _draw_waves(draw: ImageDraw.ImageDraw, size: int, horizon_y: int) -> None:
    """Лёгкие волны на поверхности моря."""
    wave_color = (100, 181, 246)
    amplitude = max(1, size // 40)
    for row in range(2):
        base_y = horizon_y + int(size * (0.12 + row * 0.18))
        points: list[tuple[int, int]] = [(0, base_y)]
        step = max(2, size // 16)
        for x in range(0, size + step, step):
            offset = int(math.sin((x / size) * math.pi * 4 + row) * amplitude)
            points.append((x, base_y + offset))
        points.append((size, base_y))
        draw.line(points, fill=wave_color, width=max(1, size // 64))


def _draw_sailboat(draw: ImageDraw.ImageDraw, size: int, horizon_y: int) -> None:
    """Силуэт парусного корабля на фоне солнца."""
    hull_color = (26, 35, 51)
    sail_color = (15, 23, 42)

    cx = int(size * 0.56)
    hull_w = int(size * 0.34)
    hull_h = max(2, int(size * 0.07))
    hull_top = horizon_y + int(size * 0.04)
    hull_left = cx - hull_w // 2
    hull_right = cx + hull_w // 2
    hull_bottom = hull_top + hull_h

    draw.polygon(
        [
            (hull_left, hull_top),
            (hull_right, hull_top),
            (hull_right - int(hull_w * 0.12), hull_bottom),
            (hull_left + int(hull_w * 0.12), hull_bottom),
        ],
        fill=hull_color,
    )

    mast_x = cx - int(size * 0.02)
    mast_top = int(size * 0.18)
    draw.line([(mast_x, hull_top), (mast_x, mast_top)], fill=hull_color, width=max(1, size // 48))

    main_sail = [
        (mast_x, mast_top + int(size * 0.03)),
        (mast_x, hull_top - int(size * 0.01)),
        (cx + int(size * 0.16), hull_top - int(size * 0.02)),
    ]
    draw.polygon(main_sail, fill=sail_color)

    jib = [
        (mast_x, mast_top + int(size * 0.05)),
        (mast_x, hull_top),
        (cx - int(size * 0.15), hull_top + int(size * 0.01)),
    ]
    draw.polygon(jib, fill=(22, 32, 48))


def draw_icon(size: int) -> Image.Image:
    """Парусник на море в лучах заходящего солнца."""
    img = Image.new("RGB", (size, size), (255, 224, 130))
    horizon_y = int(size * 0.58)

    _draw_sky(img, horizon_y)
    _draw_sea(img, horizon_y)

    draw = ImageDraw.Draw(img)
    sun_x = int(size * 0.34)
    sun_y = int(size * 0.36)
    sun_r = max(3, int(size * 0.12))
    _draw_sun_rays(draw, sun_x, sun_y, sun_r, size)

    _draw_waves(draw, size, horizon_y)
    _draw_sailboat(draw, size, horizon_y)

    return img


sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = [draw_icon(s) for s, _ in sizes]

rgb_icons: list[Image.Image] = []
for icon in icons:
    rgb_icons.append(icon if icon.mode == "RGB" else icon.convert("RGB"))

try:
    rgb_icons[0].save(
        "app.ico",
        format="ICO",
        sizes=sizes,
        append_images=rgb_icons[1:],
    )
    print("✅ Иконка 'app.ico' создана!")
    print("   Дизайн: силуэт парусника на море в лучах солнца")
except Exception as e:
    print(f"❌ Ошибка при сохранении: {e}")
    print("Попытка альтернативного метода сохранения...")
    rgb_icons[0].save("app.ico", format="ICO")
    print("✅ Иконка 'app.ico' создана (только один размер)")
