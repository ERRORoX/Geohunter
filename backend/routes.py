"""API routes for GeoHunter."""
from __future__ import annotations

import base64
import io
import json
import logging
import math
from datetime import datetime
from typing import Any
import requests
from flask import jsonify, redirect, request, Response, send_file, send_from_directory
from PIL import Image

from config import settings
from exceptions import ValidationError, ProcessingError
from modules.reverse_search import build_reverse_response
from modules.search_queries import build_queries, build_search_results
from modules.shadow_latitude import compute_shadow_latitude_data
from services import (
    compute_sun_position,
    exif_has_metadata,
    extract_camera_info,
    extract_dates,
    build_gps_response,
    extract_privacy_warnings,
    extract_shooting_params,
    extract_software_info,
    process_exif_data,
)
from tools import run_tool

logger = logging.getLogger(__name__)


def register_routes(app) -> None:
    """Register all routes with the Flask app."""

    @app.errorhandler(413)
    def payload_too_large(_e):
        return jsonify(
            {"success": False, "error": f"Тело запроса больше лимита (MAX_UPLOAD_MB={int(settings.max_upload_mb)} МБ)."}
        ), 413

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        return jsonify({"success": False, "error": e.message}), e.status_code

    @app.errorhandler(ProcessingError)
    def handle_processing_error(e):
        return jsonify({"success": False, "error": e.message}), e.status_code

    @app.route("/")
    def root():
        return redirect("/photo/", code=302)

    @app.route("/photo")
    def photo_page_no_slash():
        return redirect("/photo/", code=302)

    @app.route("/photo/")
    def photo_page():
        base = app.static_folder
        if not base:
            return jsonify({"error": "Static folder not configured"}), 500
        index_path = f"{base}/photo/index.html"
        if not index_path:
            return jsonify({"error": "Страница не найдена", "page": "photo"}), 404
        return send_from_directory(f"{base}/photo", "index.html")

    @app.route("/api/exif", methods=["POST"])
    def api_photo_exif():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        
        if not image_b64:
            raise ValidationError("imageBase64 обязателен")

        exiftool_enabled = data.get("exiftool")
        exiftool_enabled = True if exiftool_enabled is None else bool(exiftool_enabled)
        geocode_enabled = data.get("geocode") is not False

        raw_fn = data.get("filename") or data.get("name") or ""
        safe_filename = None
        if isinstance(raw_fn, str):
            base = raw_fn.strip().replace("\\", "/").split("/")[-1]
            if base and ".." not in base and "\x00" not in base:
                safe_filename = base[:240]

        try:
            res = process_exif_data(image_b64, safe_filename, exiftool_enabled, geocode_enabled)
        except ProcessingError as e:
            raise e
        except Exception as e:
            logger.error(f"EXIF processing error: {e}")
            raise ProcessingError(str(e))

        gps_out = build_gps_response(res, geocode_enabled=geocode_enabled)

        exif_summary = res.get("exif_summary") if isinstance(res.get("exif_summary"), dict) else {}
        camera = extract_camera_info(exif_summary)
        dates = extract_dates(exif_summary)
        software = extract_software_info(exif_summary)
        shooting = extract_shooting_params(exif_summary)
        privacy = extract_privacy_warnings(exif_summary, gps_out)

        et_full = res.get("exiftool")
        exiftool_lite = None
        if isinstance(et_full, dict):
            exiftool_lite = {}
            if et_full.get("error"):
                exiftool_lite["error"] = et_full["error"]
            if et_full.get("skipped") or et_full.get("ok") is False:
                exiftool_lite["skipped"] = True

        exiftool_tag_count = None
        if isinstance(et_full, dict) and isinstance(et_full.get("record"), dict):
            exiftool_tag_count = len(et_full["record"])

        has_meta = exif_has_metadata(
            camera=camera,
            dates=dates,
            shooting=shooting,
            software=software,
            gps=gps_out,
            exiftool_tag_count=exiftool_tag_count,
        )

        return jsonify(
            {
                "success": True,
                "has_metadata": has_meta,
                "gps": gps_out,
                "camera": camera,
                "dates": dates,
                "software": software,
                "shooting": shooting,
                "privacy": privacy,
                "sun": compute_sun_position(gps_out, dates),
                "hashes": res.get("hashes"),
                "perceptual": res.get("perceptual"),
                "meta": res.get("meta"),
                "file_stats": res.get("file_stats"),
                "exiftool_tag_count": exiftool_tag_count,
                "exiftool": exiftool_lite if exiftool_lite else None,
            }
        )

    @app.route("/api/exif/strip", methods=["POST"])
    def api_photo_exif_strip():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        if not image_b64:
            raise ValidationError("imageBase64 обязателен")
        try:
            s = str(image_b64).strip()
            if s.startswith("data:"):
                comma = s.find(",")
                if comma != -1:
                    s = s[comma + 1 :]
            raw = base64.b64decode(s, validate=False)
            with Image.open(io.BytesIO(raw)) as img:
                img.load()
                fmt = (img.format or "PNG").upper()
                out = io.BytesIO()
                save_fmt = "JPEG" if fmt in {"JPG", "JPEG"} else "PNG"
                if save_fmt == "JPEG":
                    img.convert("RGB").save(out, format="JPEG", quality=92, optimize=True)
                    mime, fname = "image/jpeg", "clean.jpg"
                else:
                    img.save(out, format="PNG", optimize=True)
                    mime, fname = "image/png", "clean.png"
            out.seek(0)
            return send_file(out, mimetype=mime, as_attachment=True, download_name=fname)
        except Exception as e:
            logger.error(f"EXIF strip error: {e}")
            raise ProcessingError(str(e))

    @app.route("/api/exif/exiftool/json", methods=["POST"])
    def api_photo_exif_exiftool_json():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        if not image_b64:
            raise ValidationError("imageBase64 обязателен")

        exiftool_enabled = data.get("exiftool")
        exiftool_enabled = True if exiftool_enabled is None else bool(exiftool_enabled)
        geocode_enabled = data.get("geocode") is not False
        raw_fn = data.get("filename") or data.get("name") or ""
        safe_filename = None
        if isinstance(raw_fn, str):
            base = raw_fn.strip().replace("\\", "/").split("/")[-1]
            if base and ".." not in base and "\x00" not in base:
                safe_filename = base[:240]

        try:
            res = process_exif_data(image_b64, safe_filename, exiftool_enabled, geocode_enabled)
        except ProcessingError as e:
            raise e

        et_full = res.get("exiftool")
        if not isinstance(et_full, dict) or et_full.get("skipped") or et_full.get("error"):
            raise ProcessingError((et_full or {}).get("error") or "ExifTool недоступен")
        record = et_full.get("record") if isinstance(et_full.get("record"), dict) else None
        if record is None:
            raise ProcessingError("ExifTool record отсутствует")

        return jsonify(
            {
                "success": True,
                "tag_count": et_full.get("tag_count") or len(record),
                "record_truncated": bool(et_full.get("record_truncated")),
                "record": record,
            }
        )

    @app.route("/api/exif/exiftool/txt", methods=["POST"])
    def api_photo_exif_exiftool_txt():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        if not image_b64:
            raise ValidationError("imageBase64 обязателен")

        exiftool_enabled = data.get("exiftool")
        exiftool_enabled = True if exiftool_enabled is None else bool(exiftool_enabled)
        geocode_enabled = data.get("geocode") is not False
        raw_fn = data.get("filename") or data.get("name") or ""
        safe_filename = None
        if isinstance(raw_fn, str):
            base = raw_fn.strip().replace("\\", "/").split("/")[-1]
            if base and ".." not in base and "\x00" not in base:
                safe_filename = base[:240]

        try:
            res = process_exif_data(image_b64, safe_filename, exiftool_enabled, geocode_enabled)
        except ProcessingError as e:
            raise e

        et_full = res.get("exiftool")
        if not isinstance(et_full, dict) or et_full.get("skipped") or et_full.get("error"):
            raise ProcessingError((et_full or {}).get("error") or "ExifTool недоступен")

        txt = (et_full.get("formatted_text") or "").strip()
        if not txt:
            rec = et_full.get("record") if isinstance(et_full.get("record"), dict) else {}
            lines = []
            for k, v in rec.items():
                try:
                    vv = (
                        v.get("val")
                        if isinstance(v, dict) and "val" in v
                        else (v.get("value") if isinstance(v, dict) and "value" in v else v)
                    )
                except Exception:
                    vv = v
                lines.append(f"{k}: {vv}")
            txt = "\n".join(lines) or "Метаданные не найдены."

        fname = "exiftool.txt"
        if safe_filename:
            stem = safe_filename.rsplit(".", 1)[0]
            if stem:
                fname = f"{stem}.exiftool.txt"

        resp = Response(txt, mimetype="text/plain; charset=utf-8")
        resp.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
        return resp

    @app.route("/api/reverse-search", methods=["POST"])
    def api_photo_reverse_search():
        data = request.get_json(silent=True) or {}
        image_url = (data.get("imageUrl") or data.get("image_url") or "").strip()
        return jsonify(build_reverse_response(image_url or None))

    @app.route("/api/search", methods=["POST"])
    def api_photo_web_search():
        """Поисковые запросы и ссылки на Google/Yandex/DuckDuckGo/Bing."""
        data = request.get_json(silent=True) or {}
        raw_queries = data.get("queries")
        if isinstance(raw_queries, list) and raw_queries:
            queries = [str(q).strip() for q in raw_queries if str(q).strip()][:12]
        else:
            exif_ctx = data.get("exif") if isinstance(data.get("exif"), dict) else None
            ocr_ctx = data.get("ocr") if isinstance(data.get("ocr"), dict) else None
            queries = build_queries(exif=exif_ctx, ocr=ocr_ctx)
        return jsonify({"success": True, "queries": queries, "results": build_search_results(queries)})

    @app.route("/api/export-report", methods=["POST"])
    def api_photo_export_report():
        data = request.get_json(silent=True) or {}
        results = data.get("results") or {}
        search_results = data.get("searchResults") or []
        image_url = (data.get("imageUrl") or "").strip()
        lines = ["# GeoHunter — отчёт по фото", ""]
        if image_url:
            lines += [f"**Image URL**: {image_url}", ""]
        if isinstance(results, dict) and results:
            lines += ["## Результаты", ""]
            for k in sorted(results.keys()):
                v = results.get(k)
                try:
                    preview = json.dumps(v, ensure_ascii=False, indent=2)[:4000]
                except Exception:
                    preview = str(v)[:4000]
                lines += [f"### {k}", "", "```json", preview, "```", ""]
        if isinstance(search_results, list) and search_results:
            lines += ["## Web search", "", "```json", json.dumps(search_results, ensure_ascii=False, indent=2)[:4000], "```", ""]
        return jsonify({"success": True, "report": "\n".join(lines)})

    @app.route("/api/export-json", methods=["POST"])
    def api_export_json():
        """Полный дамп результатов анализа в один JSON-файл."""
        data = request.get_json(silent=True) or {}
        payload = {
            "geoHunterExport": 1,
            "imageUrl": (data.get("imageUrl") or "").strip(),
            "uploadFileName": data.get("uploadFileName"),
            "results": data.get("results") if isinstance(data.get("results"), dict) else {},
            "searchResults": data.get("searchResults") if isinstance(data.get("searchResults"), list) else [],
            "reverseLinks": data.get("reverseLinks"),
        }
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        resp = Response(body, mimetype="application/json; charset=utf-8")
        resp.headers["Content-Disposition"] = 'attachment; filename="geohunter-export.json"'
        return resp

    @app.route("/api/ocr", methods=["POST"])
    def api_photo_ocr():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        if not image_b64:
            raise ValidationError("OCR офлайн: передайте imageBase64.")
        lang = (data.get("lang") or "eng+rus").strip()
        res = run_tool("photo-ocr", {"image_base64": image_b64, "lang": lang})
        if not res.get("success"):
            raise ProcessingError(res.get("error") or "OCR ошибка")
        return jsonify(res)

    @app.route("/api/qr-barcode", methods=["POST"])
    def api_photo_qr():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        if not image_b64:
            raise ValidationError("QR офлайн: передайте imageBase64.")
        res = run_tool("photo-qr", {"image_base64": image_b64})
        if not res.get("success"):
            raise ProcessingError(res.get("error") or "QR ошибка")
        return jsonify(res)

    @app.route("/api/forensics/ela", methods=["POST"])
    def api_photo_ela():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        quality = data.get("quality", 90)
        scale = data.get("scale", 20.0)
        res = run_tool("photo-forensics", {"image_base64": image_b64, "quality": quality, "scale": scale})
        return jsonify(res)

    @app.route("/api/forensics/noise", methods=["POST"])
    def api_photo_noise():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        res = run_tool("photo-noise", {"image_base64": image_b64})
        return jsonify(res)

    @app.route("/api/forensics/stego", methods=["POST"])
    def api_photo_stego():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        res = run_tool("photo-stego", {"image_base64": image_b64})
        return jsonify(res)

    @app.route("/api/forensics/faces", methods=["POST"])
    def api_photo_faces():
        data = request.get_json(silent=True) or {}
        image_b64 = data.get("imageBase64") or data.get("image_base64") or ""
        res = run_tool("photo-faces", {"image_base64": image_b64})
        return jsonify(res)

    @app.route("/api/forensics/sun")
    def api_photo_sun():
        res = run_tool("photo-sun", {
            "lat": request.args.get("lat"),
            "lon": request.args.get("lon"),
            "dt": request.args.get("dt")
        })
        return jsonify(res)

    @app.route("/api/forensics/shadow-solve", methods=["POST"])
    def api_photo_shadow_solve():
        from modules.exif_datetime import parse_exif_datetime

        data = request.get_json(silent=True) or {}
        try:
            h = float(data.get("objectHeight", data.get("object_height", 1)))
            l = float(data.get("shadowLength", data.get("shadow_length", 1.5)))
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Некорректные размеры объекта или тени."}), 200

        dt_str = (data.get("dt") or data.get("date") or "").strip()
        if not dt_str:
            return jsonify({
                "success": False,
                "error": "Нет даты съёмки в EXIF. Сделайте фото камерой с датой или укажите дату вручную.",
            }), 200

        dt = parse_exif_datetime(dt_str)
        if not dt:
            return jsonify({
                "success": False,
                "error": f"Не удалось разобрать дату: {dt_str[:40]}",
            }), 200

        try:
            result = compute_shadow_latitude_data(h, l, dt)
        except ImportError as e:
            return jsonify({"success": False, "error": str(e)}), 200
        except Exception as e:
            logger.error("Shadow solve: %s", e)
            return jsonify({"success": False, "error": str(e)}), 200

        return jsonify({
            "success": True,
            "objectHeight": h,
            "shadowLength": l,
            **result,
        })

    @app.route("/api/ui/host-os")
    def api_host_os():
        try:
            import platform
            u = platform.uname()
            return jsonify(
                {
                    "system": u.system,
                    "release": u.release,
                    "version": u.version,
                    "machine": u.machine,
                    "node": u.node,
                }
            )
        except OSError as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/<path:path>")
    def static_files(path):
        pl = path.lower()
        if pl.endswith((".py", ".pyc", ".pyo")):
            return jsonify({"error": "Not found"}), 404
        return send_from_directory(app.static_folder, path)
