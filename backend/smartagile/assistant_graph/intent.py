"""Intent: rule-based and optional small LLM classification."""

from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from .llm_factory import invoke_messages_resilient, is_llm_configured

logger = logging.getLogger(__name__)

INTENTS = frozenset({"productivity", "tasks", "general"})


def classify_intent_rules(user_text: str) -> str:
    t = (user_text or "").lower()
    if any(
        k in t
        for k in (
            "task",
            "tasks",
            "sprint",
            "project",
            "todo",
            "jira",
            "backlog",
            "assign",
            "to do",
            "delete",
            "remove",
        )
    ):
        return "tasks"
    if any(
        k in t
        for k in (
            "focus",
            "distract",
            "productive",
            "productivity",
            "usage",
            "spent more time",
            "spend more time",
            "most time",
            "top app",
            "top apps",
            "which app",
            "which application",
            "application did i",
            "apps did i",
            "website",
            "websites",
            "visited",
            "browse",
            "browsed",
            "browser history",
            "chrome",
            "google chrome",
            "url",
            "urls",
            "app switch",
            "time track",
            "deep work",
            "context switch",
            "distraction",
        )
    ):
        return "productivity"
    return "general"


def _parse_intent_json(content: str) -> str | None:
    s = (content or "").strip()
    m = re.search(r"\{[^{}]*\}", s, re.DOTALL)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        v = str(o.get("intent", "")).lower().strip()
        if v in INTENTS:
            return v
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    return None


def classify_intent(user_text: str) -> str:
    """
    Return one of: productivity, tasks, general.
    Uses a tiny LLM call if ASSISTANT_LLM_CLASSIFY and API key; else rules.
    """
    if not getattr(settings, "ASSISTANT_LLM_CLASSIFY", False) or not is_llm_configured():
        return classify_intent_rules(user_text)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        raw, _ = invoke_messages_resilient(
            [
                SystemMessage(
                    content=(
                        "Classify the user message for a workplace app. "
                        "Reply with JSON only, no markdown: "
                        '{"intent":"productivity"} for focus/time/distraction/usage; '
                        '{"intent":"tasks"} for work items/sprints/projects/todo; '
                        '{"intent":"general"} for anything else (greetings, off-topic).'
                    )
                ),
                HumanMessage(content=user_text or ""),
            ]
        )
        j = _parse_intent_json(raw)
        if j:
            return j
    except Exception:  # pragma: no cover
        logger.exception("classify_intent LLM failed; falling back to rules")

    return classify_intent_rules(user_text)
