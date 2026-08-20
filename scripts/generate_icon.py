import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RES_DIR = PROJECT_ROOT / "app" / "resources"
RES_DIR.mkdir(parents=True, exist_ok=True)

ICO_PATH = RES_DIR / "icon.ico"
PNG_PATH = RES_DIR / "icon.png"


def create_base_icon_image(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Draw outer subtle glow / shadow
    pad = int(size * 0.04)
    r = size // 2
    cx, cy = size // 2, size // 2

    # Draw gradient blue circle
    # Simulating vertical gradient: Top #1E90FF (30, 144, 255), Bottom #0078D4 (0, 120, 212)
    circle_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    circle_draw = ImageDraw.Draw(circle_img)

    for y in range(pad, size - pad):
        factor = (y - pad) / max(1, (size - 2 * pad))
        # Interpolate color
        cr = int(30 * (1 - factor) + 0 * factor)
        cg = int(144 * (1 - factor) + 120 * factor)
        cb = int(255 * (1 - factor) + 212 * factor)
        circle_draw.line([(pad, y), (size - pad, y)], fill=(cr, cg, cb, 255))

    # Mask circle
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([pad, pad, size - pad, size - pad], fill=255)

    img.paste(circle_img, (0, 0), mask)

    # 2. Draw crisp white outer border
    border_width = max(2, int(size * 0.03))
    border_draw = ImageDraw.Draw(img)
    border_draw.ellipse(
        [pad, pad, size - pad, size - pad],
        outline=(255, 255, 255, 220),
        width=border_width,
    )

    # 3. Draw bold "译" character in center
    font_size = int(size * 0.52)
    font = None

    # Try standard Windows Chinese fonts
    font_candidates = [
        "msyhbd.ttc",  # Microsoft YaHei Bold
        "msyh.ttc",    # Microsoft YaHei
        "simhei.ttf",   # SimHei
        "C:\\Windows\\Fonts\\msyhbd.ttc",
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\simhei.ttf",
    ]

    for fc in font_candidates:
        try:
            font = ImageFont.truetype(fc, font_size)
            break
        except Exception:
            continue

    if font is None:
        font = ImageFont.load_default()

    text = "译"
    # Calculate bounding box
    bbox = border_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 - bbox[1] - int(size * 0.02)

    border_draw.text((tx, ty), text, fill=(255, 255, 255, 250), font=font)

    return img


def generate_icons():
    base_img = create_base_icon_image(256)
    base_img.save(PNG_PATH, format="PNG")
    print(f"[IconGen] Saved PNG icon to: {PNG_PATH}")

    # Generate multi-resolution ICO (16, 24, 32, 48, 64, 128, 256)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_images = []
    for s in sizes:
        icon_images.append(create_base_icon_image(s[0]))

    icon_images[0].save(
        ICO_PATH,
        format="ICO",
        sizes=sizes,
        append_images=icon_images[1:],
    )
    print(f"[IconGen] Saved multi-resolution ICO to: {ICO_PATH}")


if __name__ == "__main__":
    generate_icons()
