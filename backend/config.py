"""Configuration settings for GeoHunter."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Server
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=5050, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")

    # Upload limits
    max_upload_mb: float = Field(default=16.0, ge=1.0, le=100.0, description="Max upload size in MB")

    # CORS
    cors_origins: str = Field(default="*", description="CORS allowed origins")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, ge=1, description="Requests per minute")

    # Security
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        min_length=32,
        description="Secret key for session signing"
    )
    csrf_enabled: bool = Field(default=True, description="Enable CSRF protection")

    # External services
    nominatim_timeout: int = Field(default=8, ge=1, le=30, description="Nominatim API timeout")
    user_agent: str = Field(default="GeoHunter-EXIF/1.0", description="User agent for requests")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: str = Field(
        default="%(levelname)s %(name)s: %(message)s",
        description="Log format"
    )

    # Paths
    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent)
    static_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "static")
    upload_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "uploads")
    temp_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent / "temp")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if v == "*":
            return ["*"]
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    @property
    def max_content_length(self) -> int:
        """Calculate max content length in bytes."""
        return int(self.max_upload_mb * 1024 * 1024)

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.static_dir.mkdir(parents=True, exist_ok=True)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
