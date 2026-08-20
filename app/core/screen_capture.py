import os
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageGrab


class ScreenCaptureEngine:
    """Handles full screen capturing and in-place translated image rendering."""

    def __init__(self):
        self._font_cache: Dict[int, ImageFont.FreeTypeFont] = {}
        self._font_path = self._find_system_font()

    def _find_system_font(self) -> str:
        """Finds a modern Chinese-compatible font from Windows font directory."""
        candidates = [
            r"C:\Windows\Fonts\msyh.ttc",       # Microsoft YaHei
            r"C:\Windows\Fonts\msyhbd.ttc",     # Microsoft YaHei Bold
            r"C:\Windows\Fonts\simhei.ttf",     # SimHei
            r"C:\Windows\Fonts\segoeui.ttf",    # Segoe UI
            r"C:\Windows\Fonts\arial.ttf",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        return "arial.ttf"

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont:
        size = max(10, min(size, 80))
        if size not in self._font_cache:
            try:
                self._font_cache[size] = ImageFont.truetype(self._font_path, size)
            except Exception:
                self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def capture_fullscreen(self) -> Image.Image:
        """Captures the full screen."""
        try:
            img = ImageGrab.grab(all_screens=True)
            return img.convert("RGB")
        except Exception:
            img = ImageGrab.grab()
            return img.convert("RGB")

    def _get_dominant_color(self, crop: Image.Image) -> Tuple[int, int, int]:
        """Calculates dominant/average background color from boundary pixels of the text block."""
        try:
            arr = np.array(crop)
            if arr.size == 0 or len(arr.shape) < 3:
                return (255, 255, 255)
            # Sample border pixels (top, bottom, left, right edges)
            top = arr[0, :, :3]
            bottom = arr[-1, :, :3]
            left = arr[:, 0, :3]
            right = arr[:, -1, :3]
            border_pixels = np.concatenate([top, bottom, left, right], axis=0)
            avg_color = np.median(border_pixels, axis=0).astype(int)
            return (int(avg_color[0]), int(avg_color[1]), int(avg_color[2]))
        except Exception:
            return (240, 240, 240)

    def _get_contrast_text_color(self, bg_color: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Returns high-contrast text color (dark text for light bg, white text for dark bg)."""
        r, g, b = bg_color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        if luminance > 135:
            return (20, 20, 20)
        else:
            return (245, 245, 245)

    def render_inplace_translation(
        self, original_image: Image.Image, blocks: List[Dict[str, Any]], translated_texts: List[str]
    ) -> Image.Image:
        """Draws translated text in-place onto the original image at detected bounding box positions."""
        result_img = original_image.copy().convert("RGBA")
        draw = ImageDraw.Draw(result_img, "RGBA")

        for i, block in enumerate(blocks):
            if i >= len(translated_texts):
                break
            
            trans_text = translated_texts[i].strip()
            if not trans_text:
                continue

            rect = block["rect"]  # (x, y, w, h)
            x, y, w, h = rect
            
            if w <= 0 or h <= 0:
                continue

            # Crop original area to find background color
            pad = 2
            x0 = max(0, x - pad)
            y0 = max(0, y - pad)
            x1 = min(original_image.width, x + w + pad)
            y1 = min(original_image.height, y + h + pad)

            crop_area = original_image.crop((x0, y0, x1, y1))
            bg_color = self._get_dominant_color(crop_area)
            text_color = self._get_contrast_text_color(bg_color)

            # Draw background rectangle to cover original foreign text
            bg_rgba = (bg_color[0], bg_color[1], bg_color[2], 245)
            draw.rectangle([x0, y0, x1, y1], fill=bg_rgba)

            # Calculate appropriate font size
            # Start with height-based estimation
            target_font_size = int(h * 0.75)
            target_font_size = max(11, min(target_font_size, 48))
            
            font = self._get_font(target_font_size)

            # Calculate text wrapping if text width exceeds box width
            wrapped_lines = self._wrap_text(trans_text, font, max(w, 50))
            
            # Recalculate font size if lines overflow height
            total_text_h = len(wrapped_lines) * (target_font_size + 2)
            if total_text_h > (y1 - y0 + 10) and target_font_size > 12:
                target_font_size = max(11, int(target_font_size * 0.75))
                font = self._get_font(target_font_size)
                wrapped_lines = self._wrap_text(trans_text, font, max(w, 50))

            # Draw text lines
            curr_y = y0 + max(0, (y1 - y0 - len(wrapped_lines) * (target_font_size + 2)) // 2)
            for line in wrapped_lines:
                draw.text((x0 + 2, curr_y), line, fill=text_color + (255,), font=font)
                curr_y += target_font_size + 3

        return result_img.convert("RGB")

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
        """Wraps text into multiple lines if it exceeds max_width."""
        lines = []
        curr_line = ""
        
        for char in text:
            test_line = curr_line + char
            try:
                bbox = font.getbbox(test_line)
                line_w = bbox[2] - bbox[0]
            except Exception:
                line_w = len(test_line) * (font.size or 12) * 0.6

            if line_w <= max_width or not curr_line:
                curr_line = test_line
            else:
                lines.append(curr_line)
                curr_line = char
        
        if curr_line:
            lines.append(curr_line)
        return lines


screen_capture = ScreenCaptureEngine()
