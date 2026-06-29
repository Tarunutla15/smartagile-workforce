"""
Plugin contract.

The core engine produces a coarse :class:`RawWindow` (exe path + window title) for the
foreground app. A plugin turns that into a richer :class:`Enrichment`:

    chrome.exe + "React Tutorial - YouTube - Google Chrome"
        -> Enrichment(app="YouTube", activity="React Tutorial", source_type="browser")

Plugins are *additive*: if no plugin matches (or a plugin returns ``None``), the engine
falls back to the default behaviour (ML category + exe->software name). ``matches`` must
be cheap (it runs on every poll); the (potentially expensive) work belongs in ``enrich``,
which only runs at a segment boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RawWindow:
    """A foreground observation, before any enrichment."""

    exe_path: str           # full process image path, or "pid:123" / "" when unknown
    window_title: str       # raw window/tab title
    pid: int = 0


@dataclass
class Enrichment:
    """What a plugin contributes for a usage segment. Any field may be None."""

    app: str | None = None        # display name override, e.g. "YouTube", "Cursor"
    activity: str | None = None   # specific context, e.g. "React Tutorial", "engine.py"
    category: str | None = None   # category override (usually None -> ML classifier)
    detail: dict[str, Any] | None = None  # extra structured data (url, domain, ...)


class Plugin:
    """Base class for context enrichers."""

    name: str = "plugin"
    # Lower runs first; the default catch-all plugin uses a high number.
    priority: int = 100
    # "application" or "browser" -> drives UsageEvent.source_type.
    source_type: str = "application"
    # When True, different window titles are treated as separate segments (browsers,
    # editors: per-tab / per-file attribution). When False, one segment per app.
    splits_by_title: bool = False

    def matches(self, raw: RawWindow) -> bool:  # pragma: no cover - interface
        raise NotImplementedError

    def enrich(self, raw: RawWindow) -> Enrichment | None:  # pragma: no cover - interface
        raise NotImplementedError

    def segment_title(self, raw: RawWindow) -> str:
        """Title used for the stable-activity key when ``splits_by_title`` is True."""
        return raw.window_title or ""
