"""Generate TARS app icon — Interstellar monolith-inspired design."""

from PIL import Image, ImageDraw, ImageFont, ImageFilter

SIZE = 1024
CORNER_RADIUS = 180


def rounded_mask(size, radius):
    """Create a rounded-rectangle alpha mask."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return mask


def main():
    img = Image.new("RGB", (SIZE, SIZE), (12, 12, 16))
    draw = ImageDraw.Draw(img)

    # Subtle radial gradient background
    cx, cy = SIZE // 2, SIZE // 2
    for r in range(SIZE, 0, -2):
        intensity = int(18 * (r / SIZE))
        color = (8 + intensity, 8 + intensity, 14 + intensity)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

    # TARS monolith body — tall rectangle, slightly off-center for depth
    monolith_w = 200
    monolith_h = 580
    mx = (SIZE - monolith_w) // 2
    my = (SIZE - monolith_h) // 2 - 20

    # Shadow
    shadow_offset = 8
    draw.rounded_rectangle(
        [mx + shadow_offset, my + shadow_offset,
         mx + monolith_w + shadow_offset, my + monolith_h + shadow_offset],
        radius=12,
        fill=(0, 0, 0),
    )

    # Main body — dark metallic grey with slight gradient
    for i in range(monolith_h):
        y = my + i
        # Gradient from slightly lighter top to darker bottom
        g = int(55 - (i / monolith_h) * 20)
        draw.line([(mx, y), (mx + monolith_w, y)], fill=(g, g, g + 5))

    # Rounded rectangle overlay for clean edges
    draw.rounded_rectangle(
        [mx, my, mx + monolith_w, my + monolith_h],
        radius=12,
        outline=(70, 70, 75),
        width=2,
    )

    # Segmentation lines (TARS has articulated panels)
    segment_gap = monolith_h // 4
    for i in range(1, 4):
        y = my + segment_gap * i
        draw.line([(mx + 4, y), (mx + monolith_w - 4, y)], fill=(30, 30, 35), width=2)

    # Cyan indicator light (eye) — top panel
    eye_y = my + segment_gap // 2
    eye_x = SIZE // 2
    # Glow
    for r in range(30, 0, -1):
        alpha = int(80 * (1 - r / 30))
        glow_color = (0, alpha, alpha)
        draw.ellipse([eye_x - r, eye_y - r // 2, eye_x + r, eye_y + r // 2], fill=glow_color)
    # Core light
    draw.ellipse([eye_x - 8, eye_y - 4, eye_x + 8, eye_y + 4], fill=(0, 230, 230))

    # "TARS" text below monolith
    try:
        font = ImageFont.truetype("/usr/share/fonts/OTF/SF-Mono-Bold.otf", 64)
    except Exception:
        font = ImageFont.truetype("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 64)

    text = "TARS"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    tx = (SIZE - tw) // 2
    ty = my + monolith_h + 40
    draw.text((tx, ty), text, font=font, fill=(0, 210, 210))

    # Apply rounded corners
    mask = rounded_mask(SIZE, CORNER_RADIUS)
    output = Image.new("RGB", (SIZE, SIZE), (0, 0, 0))
    output.paste(img, mask=mask)

    output.save("icon_1024.png", "PNG")
    print("App icon saved: 1024x1024")

    # Also generate smaller sizes for Xcode asset catalog
    for s in [180, 120, 87, 80, 60, 40]:
        resized = output.resize((s, s), Image.LANCZOS)
        resized.save(f"icon_{s}.png", "PNG")
        print(f"  icon_{s}.png")


if __name__ == "__main__":
    main()
