"""
Модуль EXIF Inspector для OSINT Panel: ExifTool + категоризированный вывод + текстовый разбор.
Используется бэкендом инструмента «Поиск по фотографии» при наличии `exiftool` в PATH.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from .inspector_full import EXIFProcessor
from .styles import EXIF_CATEGORIES, FIELD_NAMES

__all__ = [
    "EXIF_CATEGORIES",
    "FIELD_NAMES",
    "exiftool_installed",
    "analyze_image_path",
]


def exiftool_installed() -> bool:
    return shutil.which("exiftool") is not None


def _sanitize_record(rec: Any, *, max_keys: int = 900, max_str: int = 4000) -> tuple[Any, bool]:
    """Укладываем ответ в JSON: обрезаем огромные строки и лишние ключи."""
    if not isinstance(rec, dict):
        return rec, False
    truncated = False
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate(rec.items()):
        if i >= max_keys:
            truncated = True
            break
        if isinstance(v, str) and len(v) > max_str:
            out[k] = v[:max_str] + f"… (обрезано, было {len(v)} символов)"
            truncated = True
        else:
            try:
                json.dumps(v, default=str)
                out[k] = v
            except TypeError:
                out[k] = str(v)[:max_str]
                truncated = True
    return out, truncated


def analyze_image_path(
    path: str,
    *,
    geocode: bool = False,
) -> dict[str, Any]:
    """
    Полный разбор файла через ExifTool + форматирование + текстовый разбор (detective_analysis).

    geocode: если True — при наличии GPS в записи ExifTool один запрос к Nominatim (reverse);
    при отсутствии координат внешний вызов не выполняется.
    """
    if not exiftool_installed():
        return {
            "ok": False,
            "error": "Утилита exiftool не найдена в PATH. Установите пакет libimage-exiftool-perl (Debian/Ubuntu) или exiftool.",
        }
    if not path or not os.path.isfile(path):
        return {"ok": False, "error": "Файл не найден."}

    proc = EXIFProcessor()
    raw = proc.get_all_exif_data(path)
    if not raw:
        return {"ok": False, "error": "ExifTool не вернул данные (ошибка чтения или таймаут)."}

    rec = raw[0] if isinstance(raw, list) else raw
    if not isinstance(rec, dict):
        return {"ok": False, "error": "Неожиданный формат ответа ExifTool."}

    formatted_text = proc.format_exif_data(rec)
    detective_report = proc.detective_analysis(rec, geocode=geocode)

    geocode_result: dict[str, Any] | None = None
    if geocode:
        try:
            lat_f = lon_f = None
            try:
                backend = Path(__file__).resolve().parents[2] / "backend"
                if str(backend) not in sys.path:
                    sys.path.insert(0, str(backend))
                from modules.gps_coords import coords_from_gps_dict, parse_gps_position, parse_gps_scalar  # noqa: PLC0415

                lat_raw = proc.find_exif_value(rec, ":GPSLatitude")
                lon_raw = proc.find_exif_value(rec, ":GPSLongitude")
                lat_ref = proc.find_exif_value(rec, ":GPSLatitudeRef")
                lon_ref = proc.find_exif_value(rec, ":GPSLongitudeRef")
                pos_raw = proc.find_exif_value(rec, ":GPSPosition")
                pair = parse_gps_position(pos_raw)
                if pair:
                    lat_f, lon_f = pair
                else:
                    lat_f = parse_gps_scalar(lat_raw, lat_ref)
                    lon_f = parse_gps_scalar(lon_raw, lon_ref)
                if lat_f is None or lon_f is None:
                    pair2 = coords_from_gps_dict({"latitude": lat_raw, "longitude": lon_raw})
                    if pair2:
                        lat_f, lon_f = pair2
            except ImportError:
                lat_raw = proc.find_exif_value(rec, ":GPSLatitude")
                lon_raw = proc.find_exif_value(rec, ":GPSLongitude")
                lat_f = float(lat_raw) if lat_raw is not None else None
                lon_f = float(lon_raw) if lon_raw is not None else None
            if lat_f is not None and lon_f is not None:
                # Reverse geocode via Nominatim (external network; respect OSM limits)
                import requests  # noqa: PLC0415

                resp = requests.get(
                    "https://nominatim.openstreetmap.org/reverse",
                    params={"format": "json", "lat": lat_f, "lon": lon_f, "zoom": 18, "addressdetails": 1},
                    headers={"User-Agent": "OSINT-Panel-EXIF/1.0"},
                    timeout=8,
                )
                if resp.status_code == 200:
                    nd = resp.json() or {}
                    address = nd.get("address") if isinstance(nd.get("address"), dict) else {}
                    geocode_result = {
                        "display_name": (nd.get("display_name") or "").strip(),
                        "address": address,
                        "lat": lat_f,
                        "lon": lon_f,
                    }
        except Exception:
            geocode_result = None

    safe_rec, did_trunc = _sanitize_record(rec)

    return {
        "ok": True,
        "tag_count": len(rec),
        "formatted_text": formatted_text,
        "detective_report": detective_report,
        "geocode": geocode_result,
        "record": safe_rec,
        "record_truncated": did_trunc,
    }
