"""
Инструмент: Фото — офлайн QR/штрихкоды (pyzbar).

Требует:
- pip: pyzbar
- system: libzbar (zbar) в системе
"""

from __future__ import annotations

import base64
import io
from typing import Any

from PIL import Image

from .base import ToolBase


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


class ToolPhotoQR(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-qr"

    @property
    def name(self) -> str:
        return "Фото: QR/штрихкоды (офлайн)"

    @property
    def description(self) -> str:
        return "Декодирование QR/штрихкодов на изображении (zbar/pyzbar)."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            from pyzbar.pyzbar import decode  # noqa: PLC0415
        except Exception as e:
            return {"success": False, "error": f"pyzbar/libzbar недоступны: {e}"}

        b64 = _strip_data_url(str(params.get("image_base64") or params.get("imageBase64") or ""))
        if not b64:
            return {"success": False, "error": "Передайте image_base64 (data URL или base64)."}
        try:
            raw = base64.b64decode(b64, validate=False)
        except Exception as e:
            return {"success": False, "error": f"base64 decode: {e}"}

        try:
            with Image.open(io.BytesIO(raw)) as img:
                img.load()
                if img.mode not in ("RGB", "L"):
                    img = img.convert("RGB")
                items = decode(img)
        except Exception as e:
            return {"success": False, "error": f"QR decode ошибка: {e}"}

        decoded: list[str] = []
        meta: list[dict[str, Any]] = []
        for it in items or []:
            try:
                s = (it.data or b"").decode("utf-8", errors="replace").strip()
            except Exception:
                s = str(it.data)
            if s:
                decoded.append(s)
            meta.append(
                {
                    "type": str(getattr(it, "type", "") or ""),
                    "data": s,
                    "rect": dict(getattr(it, "rect", {}) or {}),
                }
            )

        return {"success": True, "decoded": decoded, "count": len(decoded), "items": meta}

