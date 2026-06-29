"""
Outlook plugin.

Classic Outlook titles look like ``"Inbox - you@org.com - Outlook"`` or
``"Re: Sprint review - Message (HTML)"``. The new Outlook (``olk.exe``) is similar. This
surfaces the mail subject / folder as the activity instead of a generic "(session)".
"""

from __future__ import annotations

import os
import re

from .base import Enrichment, Plugin, RawWindow

_OUTLOOK_EXES = {"outlook.exe": "Outlook", "olk.exe": "Outlook"}

_OUTLOOK_SUFFIX_RE = re.compile(
    r"\s+-\s+(Outlook|Message\s+\([^)]*\))\s*$", re.IGNORECASE
)


class OutlookPlugin(Plugin):
    name = "outlook"
    priority = 20
    source_type = "application"
    splits_by_title = True

    def __init__(self, classifier) -> None:
        self.classifier = classifier

    def _exe_base(self, raw: RawWindow) -> str:
        return os.path.basename((raw.exe_path or "").replace("/", "\\")).lower()

    def matches(self, raw: RawWindow) -> bool:
        return self._exe_base(raw) in _OUTLOOK_EXES

    def enrich(self, raw: RawWindow) -> Enrichment:
        app = _OUTLOOK_EXES.get(self._exe_base(raw), "Outlook")
        activity = _OUTLOOK_SUFFIX_RE.sub("", (raw.window_title or "").strip()).strip() or None
        category = self.classifier.predict_app_category(raw.exe_path)
        return Enrichment(app=app, activity=activity, category=category)
