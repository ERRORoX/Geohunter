"""GeoHunter: Flask API и статика раздела «Фото». Запуск: python run.py или python backend/geohunter_blueprint.py"""
from __future__ import annotations

import logging
import os
import sys

from flask import Flask

try:
    from flask_cors import CORS
except ImportError:  # pragma: no cover
    CORS = None

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_GH_ROOT = os.path.dirname(_BACKEND_DIR)

if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from config import settings
from middleware import init_middleware
from routes import register_routes
from env_check import log_startup_checks

logging.basicConfig(level=getattr(logging, settings.log_level), format=settings.log_format)

app = Flask(__name__, static_folder=str(settings.static_dir), static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length

if CORS is not None:
    CORS(app, resources={r"/*": {"origins": settings.cors_origins}})

init_middleware(app)
register_routes(app)

log_startup_checks()


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", str(settings.port)))
    host = os.environ.get("HOST", settings.host)
    debug = os.environ.get("FLASK_DEBUG", str(settings.debug)).strip().lower() not in ("0", "false", "no", "off")
    app.run(host=host, port=port, debug=debug)
