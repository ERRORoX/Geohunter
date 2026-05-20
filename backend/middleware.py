"""Middleware for GeoHunter (rate limit опционален)."""
from __future__ import annotations

from flask import Flask

from config import settings

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    _limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[f"{settings.rate_limit_per_minute} per minute"],
        storage_uri="memory://",
    )
except ImportError:
    Limiter = None  # type: ignore[misc, assignment]
    _limiter = None


def init_middleware(app: Flask) -> None:
    if settings.rate_limit_enabled and _limiter is not None:
        _limiter.init_app(app)
