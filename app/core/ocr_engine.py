from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from PIL import Image
from rapidocr_onnxruntime import RapidOCR


class OCREngine:
    """Wrapper around RapidOCR for fast, offline text and bounding box detection."""

    def __init__(self):
        self._engine: Optional[RapidOCR] = None

    def _get_engine(self) -> RapidOCR:
        if self._engine is None:
            # Initialize RapidOCR on demand to save initial startup time
            self._engine = RapidOCR()
        return self._engine

    def recognize(self, image: Union[Image.Image, np.ndarray, str]) -> List[Dict[str, Any]]:
        """Performs OCR on an image and returns detected text blocks with coordinates.
        Returns:
            List of dicts:
            [
                {
                    "box": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]],
                    "rect": (x, y, width, height),
                    "text": "detected text",
                    "score": 0.98
                }, ...
            ]
        """
        engine = self._get_engine()

        if isinstance(image, Image.Image):
            img_np = np.array(image)
        elif isinstance(image, str):
            img_pil = Image.open(image).convert("RGB")
            img_np = np.array(img_pil)
        else:
            img_np = image

        ocr_result, _ = engine(img_np)
        if not ocr_result:
            return []

        blocks = []
        for item in ocr_result:
            # item format: [box, text, score]
            box_points = item[0]
            text = str(item[1]).strip()
            score = float(item[2])

            if not text:
                continue

            xs = [p[0] for p in box_points]
            ys = [p[1] for p in box_points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
            width = max(1, x_max - x_min)
            height = max(1, y_max - y_min)

            blocks.append({
                "box": box_points,
                "rect": (int(x_min), int(y_min), int(width), int(height)),
                "text": text,
                "score": score,
            })

        return blocks


ocr_engine = OCREngine()
