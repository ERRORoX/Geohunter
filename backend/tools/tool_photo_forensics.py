"""
Инструмент: Фото-криминалистика (ELA).
Error Level Analysis (ELA) позволяет обнаружить области с разным уровнем сжатия, что указывает на редактирование.
"""

from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image, ImageChops, ImageEnhance

from .base import ToolBase


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


class ToolPhotoForensics(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-forensics"

    @property
    def name(self) -> str:
        return "Фото-криминалистика (ELA)"

    @property
    def description(self) -> str:
        return "Анализ уровня сжатия (ELA) для поиска следов монтажа."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            b64 = _strip_data_url(str(params.get("image_base64") or ""))
            if not b64:
                return {"success": False, "error": "Загрузите изображение."}

            quality = int(params.get("quality", 90))
            scale = float(params.get("scale", 20.0))

            raw = base64.b64decode(b64, validate=False)
            with Image.open(io.BytesIO(raw)) as original:
                # Конвертируем в RGB если нужно
                if original.mode != "RGB":
                    original = original.convert("RGB")

                # Сохраняем с заданным качеством во временный буфер
                buffer = io.BytesIO()
                original.save(buffer, format="JPEG", quality=quality)
                buffer.seek(0)

                # Загружаем сжатую версию
                with Image.open(buffer) as compressed:
                    # Вычисляем разницу
                    diff = ImageChops.difference(original, compressed)

                    # Усиливаем разницу для визуализации
                    extrema = diff.getextrema()
                    max_diff = max([ex[1] for ex in extrema])
                    if max_diff == 0:
                        max_diff = 1

                    # Масштабируем яркость
                    enhancer = ImageEnhance.Brightness(diff)
                    diff = enhancer.enhance(scale)

                    # Сохраняем результат
                    out_buffer = io.BytesIO()
                    diff.save(out_buffer, format="PNG")
                    res_b64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")

            return {
                "success": True,
                "ela_image": f"data:image/png;base64,{res_b64}",
                "quality": quality,
                "scale": scale,
                "note": "Области с ярким цветом или сильным шумом могут указывать на вставки или ретушь."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
