"""Intent: rule-based and optional small LLM classification."""

from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from .llm_factory import invoke_messages_resilient, is_llm_configured

logger = logging.getLogger(__name__)

INTENTS = frozenset({"productivity", "tasks", "general", "report"})

# "email/send/share me ... report/summary/usage" -> user wants the report emailed.
_REPORT_SEND_RE = re.compile(r"\b(e-?mail|mail|send|share|forward)\b", re.IGNORECASE)
_REPORT_NOUN_RE = re.compile(
    r"\b(report|summary|recap|digest|usage|stats|statistics|activity|breakdown)\b",
    re.IGNORECASE,
)


def wants_email_report(user_text: str) -> bool:
    """True when the message asks to email/send a usage report (robust to wording)."""
    t = user_text or ""
    return bool(_REPORT_SEND_RE.search(t) and _REPORT_NOUN_RE.search(t))


def classify_intent_rules(user_text: str) -> str:
    t = (user_text or "").lower()
    if wants_email_report(user_text):
        return "report"
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
            "site",
            "sites",
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
            "category",
            "categories",
            "time on",
            "spending",
            "compare",
            "compared",
            "more than",
            "less than",
            "trend",
            "trending",
            "over time",
            "work time",
            "hurting",
            "improve",
            "improving",
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


def _classify_intent_llm(user_text: str) -> str | None:
    """One small LLM classification call. Returns an intent or None on any failure."""
    try:
        from langchain_core.messages import HumanMessage, SystemMessage

        raw, _ = invoke_messages_resilient(
            [
                SystemMessage(
                    content=(
                        "Classify the user message for a workplace app. Be robust to typos "
                        "and paraphrasing. Reply with JSON only, no markdown: "
                        '{"intent":"report"} when the user asks to EMAIL/SEND/SHARE a usage '
                        "report or summary to an address; "
                        '{"intent":"productivity"} for focus/time/distraction/usage/apps/'
                        "websites/categories or comparing any of those across periods; "
                        '{"intent":"tasks"} for work items/sprints/projects/todo; '
                        '{"intent":"general"} for anything else (greetings, off-topic).'
                    )
                ),
                HumanMessage(content=user_text or ""),
            ]
        )
        return _parse_intent_json(raw)
    except Exception:  # pragma: no cover
        logger.exception("classify_intent LLM failed")
        return None


def classify_intent(user_text: str) -> str:
    """
    Return one of: productivity, tasks, general.

    Strategy (robust to spelling mistakes without paying for an LLM call every time):
    - No LLM available -> rules only.
    - ASSISTANT_LLM_CLASSIFY on -> always ask the LLM (rules as fallback).
    - Default -> trust a confident rule hit (productivity/tasks); only when rules find
      nothing ("general") do we escalate to the LLM, which catches typos/paraphrases.
    """
    if not is_llm_configured():
        return classify_intent_rules(user_text)

    always_llm = getattr(settings, "ASSISTANT_LLM_CLASSIFY", False)
    rule_guess = classify_intent_rules(user_text)
    if not always_llm and rule_guess != "general":
        return rule_guess

    return _classify_intent_llm(user_text) or rule_guess
