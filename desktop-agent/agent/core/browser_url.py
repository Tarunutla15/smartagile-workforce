"""
Optional browser-URL capture (best-effort, OFF by default).

The agent normally only sees the *window title*. With this enabled it tries to read the
active tab's URL from the browser address bar via Windows UI Automation. This is inherently
fragile (depends on the browser's accessibility tree) and requires the optional
``uiautomation`` package, so every failure path degrades silently to "no URL".

Enable with the env var ``SMARTAGILE_BROWSER_URL=1`` (and ``pip install uiautomation``).
"""

from __future__ import annotations

import logging
import os
import re
import time

logger = logging.getLogger(__name__)

_DISABLED_LOGGED = False
_uia = None
_uia_failed = False

# Accessibility names used by the address bar across Chromium / Firefox.
_ADDRESS_BAR_NAMES = (
    "Address and search bar",
    "Address",
    "Search or enter address",
    "Search with Google or enter address",
    "Search or enter website name",
)

_URL_LIKE_RE = re.compile(r"^[a-z][a-z0-9+.\-]*://|^[\w\-]+\.[\w\-.]+", re.IGNORECASE)


def is_enabled() -> bool:
    """On by default; only an explicit off-value disables URL capture."""
    raw = os.environ.get("SMARTAGILE_BROWSER_URL")
    if raw is None or not str(raw).strip():
        return True
    return str(raw).strip().lower() not in ("0", "false", "no", "off")


def _load_uia():
    """Lazily import ``uiautomation`` once; returns the module or None."""
    global _uia, _uia_failed
    if _uia is not None or _uia_failed:
        return _uia
    try:
        import uiautomation as uia  # type: ignore

        _uia = uia
        return _uia
    except Exception as exc:  # noqa: BLE001
        _uia_failed = True
        logger.info("Browser URL capture requested but 'uiautomation' is unavailable: %s", exc)
        return None


def _normalize(value: str | None) -> str | None:
    v = (value or "").strip()
    if not v:
        return None
    if not _URL_LIKE_RE.search(v):
        return None
    if "://" not in v and not v.startswith("//"):
        v = "https://" + v
    return v


def get_active_url(timeout: float = 0.4) -> str | None:
    """
    Best-effort active-tab URL for the foreground browser window. Returns None on any
    failure (disabled, dependency missing, control not found, timeout).
    """
    global _DISABLED_LOGGED
    if not is_enabled():
        if not _DISABLED_LOGGED:
            _DISABLED_LOGGED = True
            logger.debug("Browser URL capture disabled (set SMARTAGILE_BROWSER_URL=1 to enable).")
        return None
    uia = _load_uia()
    if uia is None:
        return None
    try:
        deadline = time.monotonic() + max(0.1, timeout)
        window = uia.GetForegroundControl()
        if window is None:
            return None
        for name in _ADDRESS_BAR_NAMES:
            if time.monotonic() > deadline:
                break
            try:
                edit = window.EditControl(searchDepth=12, Name=name)
            except Exception:  # noqa: BLE001
                continue
            if edit is None or not edit.Exists(0, 0):
                continue
            try:
                value = edit.GetValuePattern().Value
            except Exception:  # noqa: BLE001
                value = getattr(edit, "Name", "")
            url = _normalize(value)
            if url:
                return url
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("URL capture failed: %s", exc)
        return None


def registrable_domain(url: str | None) -> str | None:
    """Coarse registrable domain from a URL ('https://www.youtube.com/x' -> 'youtube.com')."""
    if not url:
        return None
    m = re.match(r"^[a-z][a-z0-9+.\-]*://([^/]+)", url, re.IGNORECASE)
    host = (m.group(1) if m else url).split("/")[0].split(":")[0].lower()
    if host.startswith("www."):
        host = host[4:]
    if not host or "." not in host:
        return host or None
    parts = host.split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host
