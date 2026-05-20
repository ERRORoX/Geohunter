"""
Инструмент: Поиск по фотографии (анализ + подготовка к reverse image search).
Только офлайн-анализ: метаданные, EXIF, хэши (md5/sha/ahash/dhash).
"""

from __future__ import annotations

import base64
import hashlib
import io
import math
import os
import sys
import tempfile
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

from PIL import ExifTags, Image, TiffImagePlugin

try:
    from PIL.ExifTags import IFD as ExifIFD
except ImportError:  # pragma: no cover
    ExifIFD = None  # type: ignore[misc, assignment]

from .base import ToolBase


def _run_exif_inspector_module(
    raw: bytes,
    filename: str | None,
    params: dict[str, Any],
) -> dict[str, Any] | None:
    """Опционально: полный дамп через ExifTool + модуль tools/exif_inspector."""
    root = Path(__file__).resolve().parents[2]
    tools_dir = root / "tools"
    t = str(tools_dir)
    if t not in sys.path:
        sys.path.insert(0, t)
    try:
        import exif_inspector as ei  # noqa: PLC0415
    except ImportError as e:
        return {"ok": False, "skipped": True, "error": str(e)}

    if not ei.exiftool_installed():
        return {
            "ok": False,
            "skipped": True,
            "error": "exiftool не найден в PATH (установите libimage-exiftool-perl или аналог).",
        }
    if params.get("exiftool") is False:
        return {"ok": False, "skipped": True, "error": "Расширенный режим отключён (exiftool=false)."}

    ext = ".jpg"
    if filename and "." in filename:
        suf = "." + filename.rsplit(".", 1)[-1].lower()
        if len(suf) <= 8:
            ext = suf

    tmp_path: str | None = None
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=ext)
        os.write(fd, raw)
        os.close(fd)
        return ei.analyze_image_path(tmp_path, geocode=bool(params.get("geocode")))
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _strip_data_url(s: str) -> str:
    s = (s or "").strip()
    if s.startswith("data:"):
        comma = s.find(",")
        if comma != -1:
            return s[comma + 1 :]
    return s


def _hashes(data: bytes) -> dict[str, str]:
    return {
        "md5": hashlib.md5(data).hexdigest(),
        "sha1": hashlib.sha1(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _crc32_hex(data: bytes) -> str:
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def _shannon_entropy(data: bytes) -> float:
    """Бит на байт; ~8 для шифротекста/шума, ниже для сильно сжатых изображений."""
    if not data:
        return 0.0
    n = len(data)
    counts = Counter(data)
    return round(-sum((c / n) * math.log2(c / n) for c in counts.values()), 4)


def _mime_from_magic(data: bytes) -> str:
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 2 and data[:2] == b"BM":
        return "image/bmp"
    if len(data) >= 4 and data[:4] in (b"II*\x00", b"MM\x00*"):
        return "image/tiff"
    return "application/octet-stream"


def _ahash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size, size))
    px = list(g.getdata())
    avg = sum(px) / len(px)
    bits = "".join("1" if p >= avg else "0" for p in px)
    return f"ahash{size}_" + hex(int(bits, 2))[2:].zfill((size * size + 3) // 4)


def _dhash(img: Image.Image, size: int = 8) -> str:
    g = img.convert("L").resize((size + 1, size))
    px = list(g.getdata())
    bits = []
    for y in range(size):
        row = px[y * (size + 1) : (y + 1) * (size + 1)]
        for x in range(size):
            bits.append("1" if row[x] > row[x + 1] else "0")
    bitstr = "".join(bits)
    return f"dhash{size}_" + hex(int(bitstr, 2))[2:].zfill((size * size + 3) // 4)


def _to_float_ratio(x: Any) -> float:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, TiffImagePlugin.IFDRational):
        return float(x)
    if hasattr(x, "numerator") and hasattr(x, "denominator"):
        try:
            d = float(x.denominator)
            return float(x.numerator) / d if d else 0.0
        except Exception:
            return 0.0
    if isinstance(x, (tuple, list)) and len(x) == 2:
        try:
            a, b = float(x[0]), float(x[1])
            return a / b if b else 0.0
        except Exception:
            return 0.0
    return 0.0


def _dms_to_decimal(dms: Any, ref: Any) -> float | None:
    if not dms or ref is None:
        return None
    try:
        parts = list(dms) if isinstance(dms, (tuple, list)) else [dms]
        if len(parts) < 3:
            return None
        dd = _to_float_ratio(parts[0]) + _to_float_ratio(parts[1]) / 60.0 + _to_float_ratio(parts[2]) / 3600.0
        r = str(ref).strip().upper()[:1]
        if r in ("S", "W"):
            dd = -dd
        return round(dd, 6)
    except Exception:
        return None


def _get_gps_ifd_raw(exif: Any) -> dict[Any, Any] | None:
    """Сырой GPS IFD. Pillow 10+ хранит GPS отдельно от основного EXIF."""
    if not exif:
        return None

    if ExifIFD is not None and hasattr(exif, "get_ifd"):
        try:
            gps_raw = exif.get_ifd(ExifIFD.GPSInfo)
            if gps_raw:
                return dict(gps_raw)
        except (KeyError, OSError, TypeError, ValueError):
            pass

    tag_map = {v: k for k, v in ExifTags.TAGS.items()}
    gps_id = tag_map.get("GPSInfo")
    if gps_id is None:
        return None
    try:
        if gps_id not in exif:
            return None
    except TypeError:
        return None
    raw = exif.get(gps_id)
    return raw if isinstance(raw, dict) else None


def _gps_tags_to_result(raw: dict[Any, Any]) -> dict[str, Any] | None:
    gps = {ExifTags.GPSTAGS.get(t, str(t)): raw[t] for t in raw}
    lat = _dms_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
    lon = _dms_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
    if lat is None or lon is None:
        if not gps:
            return None
        return {"raw_tags": len(gps), "note": "GPSInfo есть, но координаты не удалось разобрать."}
    return {
        "latitude": lat,
        "longitude": lon,
        "note": "Приблизительное место съёмки по EXIF. Может содержать персональные данные — не публикуйте без необходимости.",
    }


def _gps_from_exif(exif: Any) -> dict[str, Any] | None:
    raw = _get_gps_ifd_raw(exif)
    if not raw:
        return None
    return _gps_tags_to_result(raw)


def _unwrap_et_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "val" in value:
            return value["val"]
        if "value" in value:
            return value["value"]
    if isinstance(value, list) and value:
        return _unwrap_et_value(value[0])
    return value


def _gps_from_exiftool(et: dict[str, Any] | None) -> dict[str, Any] | None:
    from modules.gps_coords import coords_from_gps_dict, parse_gps_position, parse_gps_scalar

    if not isinstance(et, dict) or not et.get("ok"):
        return None
    gc = et.get("geocode")
    if isinstance(gc, dict):
        pair = coords_from_gps_dict(gc)
        if pair:
            lat, lon = pair
            out: dict[str, Any] = {
                "latitude": lat,
                "longitude": lon,
                "note": "Координаты из ExifTool (геокод).",
            }
            if gc.get("display_name"):
                out["display_name"] = gc["display_name"]
            if gc.get("address"):
                out["address"] = gc["address"]
            return out
    rec = et.get("record")
    if not isinstance(rec, dict):
        return None

    lat_val = lon_val = lat_ref = lon_ref = None
    position_val = None
    for key, val in rec.items():
        k = str(key)
        if k.endswith(":GPSLatitude") or k == "GPSLatitude":
            lat_val = _unwrap_et_value(val)
        elif k.endswith(":GPSLongitude") or k == "GPSLongitude":
            lon_val = _unwrap_et_value(val)
        elif k.endswith(":GPSLatitudeRef") or k == "GPSLatitudeRef":
            lat_ref = _unwrap_et_value(val)
        elif k.endswith(":GPSLongitudeRef") or k == "GPSLongitudeRef":
            lon_ref = _unwrap_et_value(val)
        elif "GPSPosition" in k or k.endswith(":Location"):
            position_val = _unwrap_et_value(val)

    pos_pair = parse_gps_position(position_val)
    if pos_pair:
        return {
            "latitude": pos_pair[0],
            "longitude": pos_pair[1],
            "note": "Координаты из ExifTool (GPSPosition).",
        }

    lat = parse_gps_scalar(lat_val, lat_ref)
    lon = parse_gps_scalar(lon_val, lon_ref)
    if lat is not None and lon is not None:
        return {
            "latitude": lat,
            "longitude": lon,
            "note": "Координаты из ExifTool.",
        }
    return None


def _merge_gps(
    primary: dict[str, Any] | None,
    fallback: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if primary and primary.get("latitude") is not None and primary.get("longitude") is not None:
        return primary
    return fallback or primary


def _json_safe(obj: Any, depth: int = 0) -> Any:
    if depth > 24:
        return "<max-depth>"
    if obj is None or isinstance(obj, (bool, str)):
        return obj
    if isinstance(obj, int) and not isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, TiffImagePlugin.IFDRational):
        try:
            return float(obj)
        except Exception:
            return str(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")[:8000]
    if isinstance(obj, (tuple, list)):
        return [_json_safe(x, depth + 1) for x in obj]
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key = ExifTags.TAGS.get(k, str(k)) if isinstance(k, int) else str(k)
            out[str(key)] = _json_safe(v, depth + 1)
        return out
    if hasattr(obj, "numerator") and hasattr(obj, "denominator"):
        try:
            d = float(obj.denominator)
            return float(obj.numerator) / d if d else 0.0
        except Exception:
            return str(obj)
    return str(obj)[:4000]


def _exif_dict(img: Image.Image) -> dict[str, Any]:
    out: dict[str, Any] = {}
    try:
        exif = img.getexif()
    except Exception:
        exif = None
    if not exif:
        return out

    for k, v in exif.items():
        name = ExifTags.TAGS.get(k, str(k))
        try:
            if isinstance(v, bytes):
                out[name] = v.decode("utf-8", errors="replace")
            else:
                out[name] = v
        except Exception:
            out[name] = str(v)

    try:
        gps_raw = _get_gps_ifd_raw(exif)
        if gps_raw:
            out["GPSInfo"] = {ExifTags.GPSTAGS.get(t, str(t)): gps_raw[t] for t in gps_raw}
    except Exception:
        pass

    return _json_safe(out)


_SUMMARY_KEYS = (
    "Make",
    "Model",
    "LensModel",
    "Software",
    "DateTime",
    "DateTimeOriginal",
    "DateTimeDigitized",
    "Artist",
    "Copyright",
    "Orientation",
    "ISOSpeedRatings",
    "PhotographicSensitivity",
    "ExposureTime",
    "FNumber",
    "FocalLength",
    "Flash",
    "WhiteBalance",
    "ImageUniqueID",
    "BodySerialNumber",
)


def _exif_summary(flat_exif: dict[str, Any]) -> dict[str, Any]:
    s: dict[str, Any] = {}
    for key in _SUMMARY_KEYS:
        if key not in flat_exif:
            continue
        val = flat_exif[key]
        if val in (None, ""):
            continue
        if isinstance(val, list) and len(val) == 0:
            continue
        if isinstance(val, dict) and key != "GPSInfo":
            continue
        if isinstance(val, list) and len(val) > 12:
            continue
        s[key] = val
    return s


def _collect_extra_meta(img: Image.Image, raw: bytes) -> dict[str, Any]:
    n_frames = int(getattr(img, "n_frames", 1) or 1)
    mode = img.mode or ""
    has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in (img.info or {})
    icc = (img.info or {}).get("icc_profile")
    xmp = (img.info or {}).get("XML:com.adobe.xmp")
    w, h = img.size
    return {
        "megapixels": round((w * h) / 1_000_000, 3),
        "frame_count": n_frames,
        "animated": n_frames > 1,
        "has_alpha": bool(has_alpha),
        "has_icc_profile": bool(icc),
        "has_xmp": bool(xmp),
        "compression": (img.info or {}).get("compression"),
        "dpi": _json_safe((img.info or {}).get("dpi")),
    }


class ToolPhotoSearch(ToolBase):
    @property
    def tool_id(self) -> str:
        return "photo-search"

    @property
    def name(self) -> str:
        return "Поиск по фотографии"

    @property
    def description(self) -> str:
        return "Загрузка фото: Pillow + опционально ExifTool (модуль tools/exif_inspector), хэши, reverse image search."

    def run(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            b64 = _strip_data_url(str(params.get("image_base64") or ""))
            if not b64:
                return {"success": False, "error": "Загрузите изображение (image_base64)."}
            raw = base64.b64decode(b64, validate=False)
            if len(raw) > 12 * 1024 * 1024:
                return {"success": False, "error": "Файл слишком большой (лимит 12MB)."}

            filename = (params.get("filename") or "").strip() or None
            mime_magic = _mime_from_magic(raw)
            h = _hashes(raw)
            crc = _crc32_hex(raw)
            entropy = _shannon_entropy(raw)

            with Image.open(io.BytesIO(raw)) as img:
                img.load()
                fmt = (img.format or "").upper()
                w, hh = img.size
                mode = img.mode

                try:
                    exif_raw = img.getexif()
                except Exception:
                    exif_raw = None

                exif = _exif_dict(img)
                gps = _gps_from_exif(exif_raw)
                summary = _exif_summary(exif) if isinstance(exif, dict) else {}

                phash = {
                    "ahash": _ahash(img, 8),
                    "dhash": _dhash(img, 8),
                }
                extra = _collect_extra_meta(img, raw)

            meta: dict[str, Any] = {
                "filename": filename,
                "format": fmt,
                "mime_detected": mime_magic,
                "width": w,
                "height": hh,
                "mode": mode,
                "bytes": len(raw),
                "header_hex": raw[:64].hex() if raw else "",
                **extra,
            }

            out: dict[str, Any] = {
                "success": True,
                "meta": meta,
                "hashes": {**h, "crc32": crc},
                "file_stats": {
                    "entropy_bits_per_byte": entropy,
                    "hint": "Очень высокая энтропия может указывать на шифрование/случайные данные; низкая — на сильное сжатие или простые паттерны.",
                },
                "perceptual": phash,
                "exif": exif,
                "exif_summary": summary,
                "gps": gps,
            }

            try:
                out["exiftool"] = _run_exif_inspector_module(raw, filename, params)
            except Exception as ex:
                out["exiftool"] = {"ok": False, "error": str(ex)}

            from modules.gps_coords import enrich_gps_dict

            out["gps"] = enrich_gps_dict(_merge_gps(gps, _gps_from_exiftool(out.get("exiftool"))))

            return out
        except Exception as e:
            return {"success": False, "error": str(e)}
