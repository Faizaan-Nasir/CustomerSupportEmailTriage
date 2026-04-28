"""Application configuration for the backend runtime.

This module loads environment variables from the repository root `.env`
and `apps/backend/.env`, normalizes a few documented naming variants, and
exposes a single validated `settings` object for the rest of the app.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a simple dotenv file without mutating process environment."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        values[key] = value

    return values


def _merge_env_sources() -> dict[str, str]:
    """Merge environment sources, preferring project-local env files."""
    backend_root = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[3]

    merged: dict[str, str] = {}
    merged.update(os.environ)
    merged.update(_read_env_file(repo_root / ".env"))
    merged.update(_read_env_file(backend_root / ".env"))
    return merged


def _get_first(values: Mapping[str, str], *names: str, default: str | None = None) -> str | None:
    """Return the first non-empty environment value from a list of aliases."""
    for name in names:
        value = values.get(name)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return default


def _require(values: Mapping[str, str], *names: str) -> str:
    """Return the first valid value or raise a descriptive config error."""
    value = _get_first(values, *names)
    if value is None:
        joined = ", ".join(names)
        raise ConfigError(f"Missing required environment variable. Expected one of: {joined}")
    return value


def _parse_int(name: str, value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer. Received: {value!r}") from exc


def _parse_float(name: str, value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a float. Received: {value!r}") from exc


@dataclass(frozen=True)
class Settings:
    """Strongly typed backend settings."""

    supabase_url: str
    supabase_service_role_key: str
    supabase_anon_key: str | None
    gemini_api_key: str

    gmail_client_id: str | None
    gmail_client_secret: str | None
    gmail_refresh_token: str | None
    gmail_sender_email: str | None

    smtp_host: str | None
    smtp_port: int | None
    smtp_user: str | None
    smtp_password: str | None
    smtp_sender_email: str | None

    embedding_model: str
    embedding_dimension: int

    app_env: str
    log_level: str
    interaction_limit: int
    confidence_threshold: float
    redis_url: str | None

    backend_root: Path
    repo_root: Path

    @property
    def SUPABASE_URL(self) -> str:
        return self.supabase_url

    @property
    def SUPABASE_SERVICE_ROLE_KEY(self) -> str:
        return self.supabase_service_role_key

    @property
    def SUPABASE_ANON_KEY(self) -> str | None:
        return self.supabase_anon_key

    @property
    def GEMINI_API_KEY(self) -> str:
        return self.gemini_api_key

    @property
    def SMTP_HOST(self) -> str | None:
        return self.smtp_host

    @property
    def SMTP_PORT(self) -> int | None:
        return self.smtp_port

    @property
    def SMTP_USER(self) -> str | None:
        return self.smtp_user

    @property
    def SMTP_PASSWORD(self) -> str | None:
        return self.smtp_password

    @property
    def EMBEDDING_MODEL(self) -> str:
        return self.embedding_model

    @property
    def INTERACTION_LIMIT(self) -> int:
        return self.interaction_limit

    @property
    def CONFIDENCE_THRESHOLD(self) -> float:
        return self.confidence_threshold

    @classmethod
    def from_env(cls) -> "Settings":
        values = _merge_env_sources()

        backend_root = Path(__file__).resolve().parents[1]
        repo_root = Path(__file__).resolve().parents[3]

        smtp_host = _get_first(values, "SMTP_HOST", "GMAIL_SMTP_HOST")
        smtp_port_raw = _get_first(values, "SMTP_PORT", "GMAIL_SMTP_PORT")
        smtp_user = _get_first(values, "SMTP_USER", "GMAIL_SMTP_USER")
        smtp_password = _get_first(values, "SMTP_PASSWORD", "GMAIL_SMTP_PASSWORD")
        smtp_sender_email = _get_first(
            values,
            "SMTP_SENDER_EMAIL",
            "GMAIL_SENDER_EMAIL",
            "GMAIL_SMTP_USER",
            "SMTP_USER",
        )

        gmail_client_id = _get_first(values, "GMAIL_CLIENT_ID")
        gmail_client_secret = _get_first(values, "GMAIL_CLIENT_SECRET")
        gmail_refresh_token = _get_first(values, "GMAIL_REFRESH_TOKEN")
        gmail_sender_email = _get_first(values, "GMAIL_SENDER_EMAIL")

        has_gmail_api = all(
            [gmail_client_id, gmail_client_secret, gmail_refresh_token, gmail_sender_email]
        )
        has_smtp = all([smtp_host, smtp_port_raw, smtp_user, smtp_password])

        if not has_gmail_api and not has_smtp:
            raise ConfigError(
                "Email configuration is incomplete. Configure either Gmail API "
                "(GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN, "
                "GMAIL_SENDER_EMAIL) or SMTP (SMTP_* or GMAIL_SMTP_* variables)."
            )

        return cls(
            supabase_url=_require(values, "SUPABASE_URL"),
            supabase_service_role_key=_require(values, "SUPABASE_SERVICE_ROLE_KEY"),
            supabase_anon_key=_get_first(
                values,
                "SUPABASE_ANON_KEY",
                "SUPABASE_PUBLISHABLE_KEY",
            ),
            gemini_api_key=_require(values, "GEMINI_API_KEY"),
            gmail_client_id=gmail_client_id,
            gmail_client_secret=gmail_client_secret,
            gmail_refresh_token=gmail_refresh_token,
            gmail_sender_email=gmail_sender_email,
            smtp_host=smtp_host,
            smtp_port=_parse_int("SMTP_PORT", smtp_port_raw) if smtp_port_raw else None,
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_sender_email=smtp_sender_email,
            embedding_model=_get_first(values, "EMBEDDING_MODEL", default="text-embedding-004") or "text-embedding-004",
            embedding_dimension=_parse_int(
                "EMBEDDING_DIMENSION",
                _get_first(values, "EMBEDDING_DIMENSION", default="1536") or "1536",
            ),
            app_env=_get_first(values, "APP_ENV", default="development") or "development",
            log_level=_get_first(values, "LOG_LEVEL", default="info") or "info",
            interaction_limit=_parse_int(
                "INTERACTION_LIMIT",
                _get_first(values, "INTERACTION_LIMIT", default="2") or "2",
            ),
            confidence_threshold=_parse_float(
                "CONFIDENCE_THRESHOLD",
                _get_first(values, "CONFIDENCE_THRESHOLD", default="0.75") or "0.75",
            ),
            redis_url=_get_first(values, "REDIS_URL"),
            backend_root=backend_root,
            repo_root=repo_root,
        )


settings = Settings.from_env()
