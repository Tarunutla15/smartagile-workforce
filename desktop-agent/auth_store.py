"""Persist API base URL + JWT access/refresh outside the browser (user profile dir)."""

from __future__ import annotations

import json
import os
import base64
from pathlib import Path
from typing import Any

_DEFAULT_API = "http://127.0.0.1:8000"
_FILE_NAME = "auth.json"


def _store_path() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / "SmartAgile" / _FILE_NAME
    return Path.home() / ".config" / "smartagile" / _FILE_NAME


def store_path() -> str:
    """Public path to auth.json (for logs / support)."""
    return str(_store_path())


def load() -> dict[str, Any]:
    p = _store_path()
    if not p.is_file():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save(
    *,
    access: str | None,
    refresh: str | None,
    api_base: str | None = None,
) -> None:
    p = _store_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    cur = load()
    if access is not None:
        cur["access"] = access
    if refresh is not None:
        cur["refresh"] = refresh
    if api_base is not None:
        cur["api_base"] = str(api_base).rstrip("/")
    # Store paired user id (best-effort) so UI can warn on account mismatch.
    uid = _jwt_user_id(access) or _jwt_user_id(refresh)
    if uid is not None:
        cur["paired_user_id"] = int(uid)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(cur, f, indent=0)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def get_api_base() -> str:
    v = (load().get("api_base") or os.environ.get("SMARTAGILE_API_BASE") or _DEFAULT_API)
    return str(v).rstrip("/")


def get_access() -> str:
    return str(load().get("access") or "")


def get_refresh() -> str:
    return str(load().get("refresh") or "")


def get_paired_user_id() -> int | None:
    v = load().get("paired_user_id")
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _jwt_user_id(token: str | None) -> int | None:
    """
    Decode JWT payload without verifying signature.
    Works with SimpleJWT payloads: {"user_id": 1} or {"sub": "1"}.
    """
    t = (token or "").strip()
    if not t or "." not in t:
        return None
    try:
        parts = t.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        # Add padding for base64url
        payload_b64 += "=" * (-len(payload_b64) % 4)
        raw = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            return None
        if "user_id" in obj:
            return int(obj["user_id"])
        if "sub" in obj:
            return int(obj["sub"])
    except Exception:
        return None
    return None
