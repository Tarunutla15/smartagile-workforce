"""
Default application plugin (catch-all).

Reproduces the original non-browser behaviour: ML category from the executable, the
exe -> friendly software name, and a generic ``"(session)"`` context (one aggregate
segment per app). Always matches, so it is the lowest-priority fallback in the registry.
"""

from __future__ import annotations

from .base import Enrichment, Plugin, RawWindow

SESSION_CONTEXT = "(session)"


class DefaultAppPlugin(Plugin):
    name = "application"
    priority = 1000  # last resort
    source_type = "application"
    splits_by_title = False

    def __init__(self, classifier) -> None:
        self.classifier = classifier

    def matches(self, raw: RawWindow) -> bool:
        return True

    def enrich(self, raw: RawWindow) -> Enrichment:
        app = self.classifier.app_software_name(raw.exe_path, raw.window_title)
        category = self.classifier.predict_app_category(raw.exe_path)
        return Enrichment(app=app, activity=SESSION_CONTEXT, category=category)
