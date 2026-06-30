"""Run the assistant graph and return (assistant_text, result_json) for the message API."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def run_assistant_graph(
    user,
    user_text: str,
    *,
    session_id: int | None = None,
    scope: str | None = None,
    project_id: int | None = None,
) -> tuple[str, dict[str, Any]]:
    from .graph import build_compiled_assistant_graph
    from ..brain import build_productivity_snapshot

    try:
        app = build_compiled_assistant_graph(user)
        out: dict[str, Any] = app.invoke(
            {
                "user_text": (user_text or "").strip(),
                "session_id": session_id,
                "scope": scope,
                "project_id": project_id,
            }
        )
        text = (out or {}).get("assistant_text") or ""
        rj = (out or {}).get("result_json") or {}
        if not text:
            return build_productivity_snapshot(user)
        return text, rj
    except Exception:  # pragma: no cover
        logger.exception("run_assistant_graph failed; using deterministic productivity snapshot")
        return build_productivity_snapshot(user)
