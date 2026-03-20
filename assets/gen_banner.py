"""Generate the TARS repo banner in the same spirit as kerb-map."""

import math
import random

from PIL import Image, ImageDraw, ImageFont, ImageFilter

WIDTH, HEIGHT = 1070, 300
BG = (8, 8, 12)

# Colors matching kerb-map vibe
CYAN = (0, 230, 230)
RED = (240, 70, 70)
SUBTITLE_COLOR = (160, 155, 150)
TAGLINE_COLOR = (120, 115, 110)

# Fonts
FONT_TITLE = ImageFont.truetype("/usr/share/fonts/OTF/SF-Mono-Heavy.otf", 96)
FONT_SUB = ImageFont.truetype("/usr/share/fonts/OTF/SF-Mono-Medium.otf", 22)
FONT_TAG = ImageFont.truetype("/usr/share/fonts/OTF/SF-Mono-Regular.otf", 16)


def draw_noise(img: Image.Image) -> None:
    """Add subtle grain/smoke texture to the background."""
    pixels = img.load()
    rng = random.Random(42)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            r, g, b = pixels[x, y]
            noise = rng.randint(-8, 8)
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise)),
            )


def draw_glow_circles(draw: ImageDraw.ImageDraw) -> None:
    """Draw faint radial glows for atmosphere."""
    rng = random.Random(7)
    for _ in range(6):
        cx = rng.randint(0, WIDTH)
        cy = rng.randint(0, HEIGHT)
        radius = rng.randint(80, 200)
        for r in range(radius, 0, -2):
            alpha = int(12 * (1 - r / radius))
            color = (20 + alpha, 20 + alpha, 25 + alpha)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)


def draw_scanlines(draw: ImageDraw.ImageDraw) -> None:
    """Faint horizontal scanlines."""
    for y in range(0, HEIGHT, 4):
        draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0), width=1)


def center_text(draw, text, font, y, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    x = (WIDTH - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)
    return tw


def main():
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.ImageDraw(img)

    # Atmospheric background
    draw_glow_circles(draw)
    draw_noise(img)
    draw = ImageDraw.ImageDraw(img)  # re-init after pixel manipulation
    draw_scanlines(draw)

    # Thin accent line
    line_y = 175
    draw.line([(WIDTH // 4, line_y), (3 * WIDTH // 4, line_y)], fill=(60, 20, 20), width=1)

    # Title: "T A R S" — spaced out, red like kerb-map
    title = "T  A  R  S"
    center_text(draw, title, FONT_TITLE, 50, RED)

    # Faint cyan glow behind title (draw on separate layer and composite)
    glow_layer = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    glow_draw = ImageDraw.ImageDraw(glow_layer)
    center_text(glow_draw, title, FONT_TITLE, 50, (0, 40, 40))
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=18))
    img = Image.composite(
        img,
        Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0)),
        Image.new("L", (WIDTH, HEIGHT), 255),
    )
    # Additive blend for glow
    from PIL import ImageChops
    img = ImageChops.add(img, glow_layer)
    draw = ImageDraw.ImageDraw(img)

    # Subtitle
    center_text(draw, "H Y B R I D   A I   C O M M A N D   A S S I S T A N T", FONT_SUB, 190, SUBTITLE_COLOR)

    # Tagline
    center_text(draw, "LOCAL LLM   \u2022   CLAUDE API   \u2022   SSH EXECUTION", FONT_TAG, 228, TAGLINE_COLOR)

    # Save
    img.save("banner.png", "PNG")
    print(f"Banner saved: {WIDTH}x{HEIGHT}")


if __name__ == "__main__":
    main()
