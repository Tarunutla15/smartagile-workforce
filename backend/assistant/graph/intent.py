"""Intent: rule-based and optional small LLM classification."""

from __future__ import annotations

import json
import logging
import re

from django.conf import settings

from .llm_factory import invoke_messages_resilient, is_llm_configured

logger = logging.getLogger(__name__)

INTENTS = frozenset({"productivity", "tasks", "task_insights", "general", "report", "digest"})

# "email/send/share me ... report/summary/usage" -> user wants the report emailed.
_REPORT_SEND_RE = re.compile(r"\b(e-?mail|mail|send|share|forward)\b", re.IGNORECASE)
_REPORT_NOUN_RE = re.compile(
    r"\b(report|summary|recap|digest|usage|stats|statistics|activity|breakdown)\b",
    re.IGNORECASE,
)

# Recurring schedule words: a request to set up (or stop) an automatic, repeating digest
# rather than a one-off emailed report.
_DIGEST_SCHEDULE_RE = re.compile(
    r"\b(daily|every\s+day|each\s+day|weekly|every\s+week|each\s+week|once\s+a\s+week|"
    r"schedule[d]?|recurring|automatic(?:ally)?|subscribe|unsubscribe)\b",
    re.IGNORECASE,
)
_DIGEST_NOUN_RE = re.compile(r"\b(digest|report|summary|recap)\b", re.IGNORECASE)
_DIGEST_OFF_RE = re.compile(
    r"\b(stop|turn\s+off|disable|cancel|unsubscribe|no\s+more)\b.*\b(digest|report|summary|recap|email)\b",
    re.IGNORECASE,
)
# "now / immediately / right away" — an explicit immediate-send request.
_IMMEDIATE_RE = re.compile(
    r"\b(now|immediately|right\s+now|right\s+away|asap|instantly|straight\s+away)\b",
    re.IGNORECASE,
)

# Task analytics / planning phrases (read-only) — distinct from create/delete actions.
_TASK_INSIGHTS_RE = re.compile(
    r"\b(what\s+should\s+i\s+work\s+on|what\s+to\s+work\s+on|work\s+on\s+next|next\s+task|"
    r"prioriti[sz]e|priorit(?:y|ies)|completion\s+rate|how\s+many\s+tasks|task\s+(?:stats|summary|"
    r"progress|breakdown|overview|insights?)|stale\s+task|oldest\s+task|aging\s+task|workload|"
    r"task\s+load|am\s+i\s+on\s+track|how\s+am\s+i\s+doing\s+on\s+(?:my\s+)?tasks)\b",
    re.IGNORECASE,
)


def wants_email_report(user_text: str) -> bool:
    """True when the message asks to email/send a usage report (robust to wording)."""
    t = user_text or ""
    if wants_recurring_digest(t):
        return False
    return bool(_REPORT_SEND_RE.search(t) and _REPORT_NOUN_RE.search(t))


def wants_recurring_digest(user_text: str) -> bool:
    """
    True when the user wants to set up / change / stop a *recurring* digest (scheduling),
    as opposed to a one-off emailed report.
    """
    t = user_text or ""
    if _DIGEST_OFF_RE.search(t):
        return True
    if _DIGEST_SCHEDULE_RE.search(t) and _DIGEST_NOUN_RE.search(t):
        return True
    # "send me the digest/report now" -> immediate digest send (handled by the digest agent).
    return bool(_IMMEDIATE_RE.search(t) and _DIGEST_NOUN_RE.search(t))


def wants_task_insights(user_text: str) -> bool:
    """True for read-only task analytics / planning questions."""
    return bool(_TASK_INSIGHTS_RE.search(user_text or ""))


def classify_intent_rules(user_text: str) -> str:
    t = (user_text or "").lower()
    if wants_recurring_digest(user_text):
        return "digest"
    if wants_email_report(user_text):
        return "report"
    if wants_task_insights(user_text):
        return "task_insights"
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
                        '{"intent":"digest"} when the user wants to set up, change, or STOP a '
                        "RECURRING/scheduled usage digest (e.g. 'email me a daily digest', "
                        "'send a weekly summary every week', 'turn off my digest'); "
                        '{"intent":"report"} when the user asks to EMAIL/SEND/SHARE a usage '
                        "report or summary ONE time (not recurring); "
                        '{"intent":"productivity"} for focus/time/distraction/usage/apps/'
                        "websites/categories or comparing any of those across periods; "
                        '{"intent":"task_insights"} for READ-ONLY task analytics/planning '
                        "(what should I work on next, how many tasks, completion rate, stale/old "
                        "tasks, workload by project, task progress) — NOT creating/deleting/editing; "
                        '{"intent":"tasks"} for work items/sprints/projects/todo AND task actions '
                        "(create/delete/update/rename a task); "
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
