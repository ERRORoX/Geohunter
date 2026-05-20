"""Формирование поисковых запросов и ссылок на поисковики из EXIF/OCR."""
from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus


def _clean(s: Any, max_len: int = 120) -> str:
    if s is None:
        return ""
    t = str(s).strip()
    if not t or t in ("—", "-", "null"):
        return ""
    return t[:max_len]


def build_queries(
    *,
    exif: dict[str, Any] | None = None,
    ocr: dict[str, Any] | None = None,
    extra: list[str] | None = None,
    limit: int = 12,
) -> list[str]:
    """Собирает уникальные поисковые строки из метаданных и OCR."""
    seen: set[str] = set()
    out: list[str] = []

    def add(q: str) -> None:
        q = _clean(q, 200)
        if not q or len(q) < 2:
            return
        key = q.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(q)

    ex = exif or {}
    oc = ocr or {}

    camera = ex.get("camera") if isinstance(ex.get("camera"), dict) else {}
    make = _clean(camera.get("Make"))
    model = _clean(camera.get("Model"))
    lens = _clean(camera.get("LensModel"))
    if make and model:
        add(f"{make} {model}")
    elif model:
        add(model)
    if lens:
        add(lens)

    software = ex.get("software") if isinstance(ex.get("software"), dict) else {}
    sw = _clean(software.get("Software"))
    if sw:
        add(sw)

    gps = ex.get("gps") if isinstance(ex.get("gps"), dict) else {}
    addr = _clean(gps.get("display_name"), 160)
    if addr:
        add(addr)

    shooting = ex.get("shooting") if isinstance(ex.get("shooting"), dict) else {}
    iso = shooting.get("ISOSpeedRatings") or shooting.get("PhotographicSensitivity")
    if iso not in (None, ""):
        add(f"ISO {iso} {model}".strip())

    for key in ("emails", "phones", "urls", "vins", "auto_ru"):
        arr = oc.get(key)
        if isinstance(arr, list):
            for item in arr[:3]:
                add(str(item))

    text = _clean(oc.get("fullText"), 500)
    if text:
        for line in text.splitlines():
            line = line.strip()
            if 4 <= len(line) <= 120:
                add(line)
                if len(out) >= limit:
                    break

    for q in extra or []:
        add(str(q))

    return out[:limit]


def search_engine_links(query: str) -> dict[str, str]:
    """Ссылки для ручного веб-поиска по запросу (без скрапинга)."""
    q = quote_plus(query)
    return {
        "google": f"https://www.google.com/search?q={q}",
        "yandex": f"https://yandex.ru/search/?text={q}",
        "duckduckgo": f"https://duckduckgo.com/?q={q}",
        "bing": f"https://www.bing.com/search?q={q}",
    }


def build_search_results(queries: list[str]) -> list[dict[str, Any]]:
    return [{"query": q, "links": search_engine_links(q)} for q in queries]
