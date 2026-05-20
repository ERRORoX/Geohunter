"""Custom exceptions for GeoHunter."""
from __future__ import annotations


class GeoHunterError(Exception):
    """Base exception for GeoHunter."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class ValidationError(GeoHunterError):
    """Validation error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=400)


class ProcessingError(GeoHunterError):
    """Processing error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=500)


class ExternalServiceError(GeoHunterError):
    """External service error."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=502)
