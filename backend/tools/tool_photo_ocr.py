"""OCR (Tesseract) с фильтрацией шума по уверенности."""

from __future__ import annotations

import base64
import io
import os
import re
import shutil
from typing import Any

from PIL import Image, ImageEnhance, ImageOps

from .base import ToolBase

_RE_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_RE_URL = re.compile(r"\bhttps?://[^\s<>()\"']+\b", re.I)
_RE_PHONE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
_RE_LINE_OK = re.compile(r"^[\w\s\d.,;:!?№«»\"'()/\-–—+@#%&]+$", re.UNICODE)

_TESS_HINT = (
    "Tesseract не найден: sudo apt install -y tesseract-ocr tesseract-ocr-rus tesseract-ocr-eng"
)


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        i = s.find(",")
        if i != -1:
            return s[i + 1 :]
    return s


def _tesseract_cmd() -> str | None:
    env = (os.environ.get("TESSERACT_CMD") or "").strip()
    if env and os.path.isfile(env):
        return env
    w = shutil.which("tesseract")
    if w:
        return w
    for p in ("/usr/bin/tesseract", "/usr/local/bin/tesseract", "/snap/bin/tesseract"):
        if os.path.isfile(p):
            return p
    return None


def _prepare(img: Image.Image) -> Image.Image:
    rgb = img.convert("RGB")
    w, h = rgb.size
    if max(w, h) < 1200:
        s = 1200 / max(w, h)
        rgb = rgb.resize((int(w * s), int(h * s)), Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(ImageOps.grayscale(rgb))
    return ImageEnhance.Contrast(gray).enhance(1.35)


def _valid_line(line: str) -> bool:
    line = line.strip()
    if len(line) < 2:
        return False
    if not _RE_LINE_OK.match(line):
        return False
    letters = sum(c.isalpha() or ("\u0400" <= c <= "\u04FF") for c in line)
    if letters < 1 and not re.search(r"\d{2,}", line):
        return False
  # отсечь одиночные «слова» из 1–2 символов подряд
    words = line.split()
    if len(words) == 1 and len(words[0]) <= 2:
        return False
    return True


def _ocr_lines(pytesseract, img: Image.Image, lang: str, min_conf: int = 60) -> list[str]:
    try:
        data = pytesseract.image_to_data(
            img, lang=lang, config="--psm 6 -c preserve_interword_spaces=1",
            output_type=pytesseract.Output.DICT,
        )
    except Exception:
        raw = pytesseract.image_to_string(img, lang=lang, config="--psm 6") or ""
        return [x.strip() for x in raw.splitlines() if _valid_line(x.strip())]

    by_line: dict[tuple[int, int, int], list[tuple[str, float]]] = {}
    texts = data.get("text", [])
    for i, word in enumerate(texts):
        w = (word or "").strip()
        if len(w) < 2:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1
        if 0 <= conf < min_conf:
            continue
        key = (
            int(data.get("block_num", [0])[i] or 0),
            int(data.get("par_num", [0])[i] or 0),
            int(data.get("line_num", [0])[i] or 0),
        )
        by_line.setdefault(key, []).append((w, conf))

    lines: list[str] = []
    for key in sorted(by_line.keys()):
        text = " ".join(t[0] for t in by_line[key]).strip()
        if _valid_line(text):
            lines.append(text)
    return lines


class ToolPhotoOCR(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-ocr"

    @property
    def name(self) -> str:
        return "OCR"

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import pytesseract
        except Exception as e:
            return {"success": False, "error": f"pytesseract: {e}"}

        cmd = _tesseract_cmd()
        if not cmd:
            return {"success": False, "error": _TESS_HINT}
        pytesseract.pytesseract.tesseract_cmd = cmd

        b64 = _strip_data_url(str(params.get("image_base64") or params.get("imageBase64") or ""))
        if not b64:
            return {"success": False, "error": "Загрузите изображение."}

        try:
            raw = base64.b64decode(b64, validate=False)
            with Image.open(io.BytesIO(raw)) as img:
                img.load()
                prepared = _prepare(img)
                lang = (params.get("lang") or "rus+eng").strip()
                lines = _ocr_lines(pytesseract, prepared, lang)
        except Exception as e:
            err = str(e)
            if "tesseract" in err.lower():
                return {"success": False, "error": f"{_TESS_HINT} ({err})"}
            return {"success": False, "error": f"OCR: {err}"}

        text_norm = "\n".join(lines).strip()
        emails = sorted({m.group(0) for m in _RE_EMAIL.finditer(text_norm)})[:30]
        urls = sorted({m.group(0) for m in _RE_URL.finditer(text_norm)})[:30]
        phones = sorted({m.group(0) for m in _RE_PHONE.finditer(text_norm)})[:30]

        if not text_norm:
            return {
                "success": True,
                "fullText": "",
                "emails": [],
                "urls": [],
                "phones": [],
                "hint": "Текст не распознан. Нужны tesseract-ocr-rus и контрастное фото.",
            }

        return {
            "success": True,
            "fullText": text_norm,
            "emails": emails,
            "urls": urls,
            "phones": phones,
            "lang": lang,
        }
