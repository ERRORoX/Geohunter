"""
Инструмент: Анализ цифрового шума (Noise Analysis).
Помогает обнаружить области ретуши или использования "штампа" (Clone Stamp) за счет анализа локальной дисперсии шума.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np
from PIL import Image, ImageFilter
from scipy.ndimage import uniform_filter

from .base import ToolBase


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


class ToolPhotoNoise(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-noise"

    @property
    def name(self) -> str:
        return "Анализ шума"

    @property
    def description(self) -> str:
        return "Выявляет аномалии в структуре шума (следы ретуши, кисти, затирания объектов)."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            b64 = _strip_data_url(str(params.get("image_base64") or ""))
            if not b64:
                return {"success": False, "error": "Загрузите изображение."}

            raw = base64.b64decode(b64, validate=False)
            with Image.open(io.BytesIO(raw)) as img:
                if img.mode != "L":
                    img = img.convert("L")

                # Переводим в numpy для быстрой обработки
                arr = np.array(img, dtype=np.float32)

                # Вычисляем локальное среднее
                mean = uniform_filter(arr, size=5)
                # Вычисляем локальную дисперсию (шум)
                mean_sq = uniform_filter(arr**2, size=5)
                variance = mean_sq - mean**2

                # Нормализуем для визуализации
                variance = np.clip(variance, 0, 255)
                res_img = Image.fromarray(variance.astype(np.uint8))

                # Усиливаем контраст шума
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(res_img)
                res_img = enhancer.enhance(3.0)

                out_buffer = io.BytesIO()
                res_img.save(out_buffer, format="PNG")
                res_b64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")

            return {
                "success": True,
                "noise_image": f"data:image/png;base64,{res_b64}",
                "note": "Однородные области на этой карте шума указывают на возможную ретушь или использование инструментов типа 'Кисть' и 'Штамп'."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
