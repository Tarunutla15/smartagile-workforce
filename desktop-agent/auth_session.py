"""Use stored refresh token to keep a valid access token (no copy-paste after first pairing)."""

from __future__ import annotations

import logging
import os
import time

import requests

import auth_store

logger = logging.getLogger(__name__)

# Dev override: env still wins
_access_cache: str | None = None
_cache_until = 0.0
_REFRESH_URL = "/api/token/refresh/"


def get_api_base() -> str:
    b = os.environ.get("SMARTAGILE_API_BASE", "").rstrip("/")
    if b:
        return b
    return auth_store.get_api_base()


def _from_env() -> str:
    return os.environ.get("SMARTAGILE_ACCESS_TOKEN") or os.environ.get(
        "SMARTAGILE_TAB_TOKEN", ""
    )


def refresh_access_token() -> str | None:
    """POST refresh; on success update auth file and return new access token."""
    refresh = auth_store.get_refresh()
    if not refresh:
        return None
    base = get_api_base()
    url = f"{base}{_REFRESH_URL}"
    try:
        r = requests.post(
            url,
            json={"refresh": refresh},
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        if r.status_code != 200:
            logger.warning("token refresh failed: %s %s", r.status_code, (r.text or "")[:200])
            return None
        data = r.json()
        access = data.get("access")
        if not access:
            return None
        auth_store.save(access=access, refresh=refresh, api_base=base)
        return access
    except Exception as exc:
        logger.warning("token refresh error: %s", exc)
        return None


def get_valid_access_token() -> str:
    """
    Access token for API calls.
    Order: env override → disk cache; refresh on demand when missing or after 401 (caller may retry).
    """
    global _access_cache, _cache_until
    now = time.monotonic()
    env = _from_env()
    if env:
        return env
    if _access_cache and now < _cache_until:
        return _access_cache

    access = auth_store.get_access()
    if access:
        _access_cache = access
        _cache_until = now + 120.0
        return access
    new_access = refresh_access_token()
    if new_access:
        _access_cache = new_access
        _cache_until = now + 120.0
        return new_access
    return ""


def clear_memory_cache() -> None:
    global _access_cache, _cache_until
    _access_cache = None
    _cache_until = 0.0
