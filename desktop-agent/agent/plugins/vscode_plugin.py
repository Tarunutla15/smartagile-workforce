"""
Editor plugin (VS Code / Cursor / VSCodium).

Window titles look like ``"engine.py - smartagile - Visual Studio Code"`` (a leading
``●`` marks unsaved changes). This extracts the file + workspace as the activity and
splits by title so time is attributed per file rather than lumped into one "(session)".
"""

from __future__ import annotations

import os
import re

from .base import Enrichment, Plugin, RawWindow

_EDITORS = {
    "code.exe": "Visual Studio Code",
    "code - insiders.exe": "VS Code Insiders",
    "codium.exe": "VSCodium",
    "cursor.exe": "Cursor",
}

_EDITOR_SUFFIX_RE = re.compile(
    r"\s+-\s+(Visual Studio Code(?:\s+-\s+Insiders)?|VSCodium|Cursor)\s*$", re.IGNORECASE
)


class VSCodePlugin(Plugin):
    name = "editor"
    priority = 20
    source_type = "application"
    splits_by_title = True

    def __init__(self, classifier) -> None:
        self.classifier = classifier

    def _exe_base(self, raw: RawWindow) -> str:
        return os.path.basename((raw.exe_path or "").replace("/", "\\")).lower()

    def matches(self, raw: RawWindow) -> bool:
        return self._exe_base(raw) in _EDITORS

    def enrich(self, raw: RawWindow) -> Enrichment:
        app = _EDITORS.get(self._exe_base(raw)) or self.classifier.app_software_name(
            raw.exe_path, raw.window_title
        )
        activity = _EDITOR_SUFFIX_RE.sub("", (raw.window_title or "").strip()).strip()
        activity = activity.lstrip("●").strip() or None
        category = self.classifier.predict_app_category(raw.exe_path)
        return Enrichment(app=app, activity=activity, category=category)
