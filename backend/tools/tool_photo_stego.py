"""LSB-стеганография: визуализация младших битов и эвристики скрытых данных."""

from __future__ import annotations

import base64
import io
import math
import re
from typing import Any

import numpy as np
from PIL import Image

from .base import ToolBase


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


def _entropy(bits: np.ndarray) -> float:
    if bits.size == 0:
        return 0.0
    p1 = float(np.mean(bits))
    p0 = 1.0 - p1
    ent = 0.0
    for p in (p0, p1):
        if 0 < p < 1:
            ent -= p * math.log2(p)
    return ent


def _chi_square_lsb_score(channel: np.ndarray) -> float:
    """Чем выше — тем больше похоже на LSB-встраивание (упрощённый χ² по парам значений)."""
    flat = channel.astype(np.uint8).ravel()
    if flat.size < 256:
        return 0.0
    hist = np.bincount(flat, minlength=256)
    score = 0.0
    for k in range(0, 256, 2):
        h0 = float(hist[k])
        h1 = float(hist[k + 1])
        if h0 + h1 < 16:
            continue
        expected = (h0 + h1) / 2.0
        if expected > 0:
            score += ((h0 - expected) ** 2 + (h1 - expected) ** 2) / expected
    return score / 128.0


def _bits_to_text_preview(bits: np.ndarray, max_bytes: int = 512) -> str:
    if bits.size < 8:
        return ""
    n = min(bits.size // 8, max_bytes)
    packed = np.packbits(bits[: n * 8].astype(np.uint8))
    raw = packed.tobytes()
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    text = re.sub(r"[^\x20-\x7E\u0400-\u04FF\n\r\t]", ".", text)
    text = text.strip()
    if len(text) < 4:
        return ""
    return text[:400]


class ToolPhotoStego(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-stego"

    @property
    def name(self) -> str:
        return "LSB / стеганография"

    @property
    def description(self) -> str:
        return "Младшие биты (LSB), энтропия и поиск текстовых следов во встраивании."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            b64 = _strip_data_url(str(params.get("image_base64") or ""))
            if not b64:
                return {"success": False, "error": "Загрузите изображение."}

            raw = base64.b64decode(b64, validate=False)
            with Image.open(io.BytesIO(raw)) as img:
                rgb = img.convert("RGB")
                max_side = 1600
                if max(rgb.size) > max_side:
                    rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
                arr = np.array(rgb, dtype=np.uint8)

            r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
            lsb_r = (r & 1) * 255
            lsb_g = (g & 1) * 255
            lsb_b = (b & 1) * 255
            lsb_vis = np.stack([lsb_r, lsb_g, lsb_b], axis=-1).astype(np.uint8)

            bits_rgb = np.concatenate([(r & 1).ravel(), (g & 1).ravel(), (b & 1).ravel()])
            ent = _entropy(bits_rgb)
            chi = (_chi_square_lsb_score(r) + _chi_square_lsb_score(g) + _chi_square_lsb_score(b)) / 3.0
            ones_ratio = float(np.mean(bits_rgb))

            # Извлечение: R→G→B, построчно
            bits_msg = np.concatenate([(r & 1).ravel(), (g & 1).ravel(), (b & 1).ravel()])
            preview = _bits_to_text_preview(bits_msg)

            suspicious = chi > 1.0 or ent > 0.99 or abs(ones_ratio - 0.5) > 0.08
            if preview:
                verdict = "Возможны скрытые данные (читаемый фрагмент в LSB)"
            elif suspicious:
                verdict = "Подозрительная статистика LSB — стоит проверить вручную"
            else:
                verdict = "Явных признаков LSB-встраивания не обнаружено"

            buf = io.BytesIO()
            Image.fromarray(lsb_vis).save(buf, format="PNG")
            lsb_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

            return {
                "success": True,
                "lsb_image": f"data:image/png;base64,{lsb_b64}",
                "lsb_entropy": round(ent, 4),
                "lsb_ones_ratio": round(ones_ratio, 4),
                "chi_square_score": round(chi, 3),
                "verdict": verdict,
                "hidden_text_preview": preview or None,
                "note": "LSB-плоскость: белый = бит 1. Эвристики, не расшифровка стойкого стего.",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
