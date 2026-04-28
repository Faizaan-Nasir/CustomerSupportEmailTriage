"""Supabase client factory for backend repositories."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.config import settings


def _import_supabase() -> tuple[Any, Any]:
    """Import Supabase lazily so config remains importable without the package."""
    try:
        from supabase import Client, create_client
    except ImportError as exc:
        raise ImportError(
            "The 'supabase' package is required to use the Supabase client. "
            "Install backend dependencies before running this module."
        ) from exc

    return Client, create_client


@lru_cache(maxsize=1)
def get_client() -> Any:
    """Return a singleton Supabase client configured with the service role key."""
    _client_type, create_client = _import_supabase()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase_client() -> Any:
    """Compatibility alias matching the technical document naming."""
    return get_client()

