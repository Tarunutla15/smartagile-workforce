from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings

from .intent import INTENTS
from .llm_factory import invoke_system_human_resilient, is_llm_configured

logger = logging.getLogger(__name__)


ROUTER_SYSTEM = """
You are SmartAgile's ROUTER for an in-app productivity + tasks assistant.

Your job: decide what the backend should execute for the user's message.

## Intents (pick one)
- productivity: questions about focus, usage, apps, websites, productivity, time spent
- tasks: anything about tasks/projects/todo AND task actions (create/delete)
- general: greetings, app help, anything else

## Tools (optional; only if intent=tasks and user wants an ACTION)
Available tools:
1) create_task
   args: {"title":"<string>","status":"todo|inProgress|done"}
2) delete_task
   args: {"id":<int>} OR {"title":"<string>"} OR {} (for "delete this" based on recent chat context)
3) update_task_status
   args: {"id":<int>,"status":"todo|inProgress|done"} OR {"title":"<string>","status":"..."}
   OR {"status":"todo|inProgress|done"} alone when the user refers to the task just created / last changed in this chat (e.g. "make it in progress", "mark it done").
4) rename_task
   args: {"id":<int>,"title":"<string>"} OR {"from_title":"<string>","to_title":"<string>"}

## Hard rules
- Output JSON ONLY (no markdown, no extra text).
- Only choose tool when the user clearly wants an action.
- If the user provides a quoted title, use it.
- `recent_messages` is the current session history (oldest first). Pronouns like "it", "that", "this task" refer to the **most recent** task or subject the user and assistant were discussing — i.e. the **latest** relevant mention **immediately before** the current `user_message` in that transcript (usually the last assistant turn about a task, or the last named thing).
- Do NOT treat arbitrary numbers as ids (e.g. "6 PM" is not an id). Only treat as id if user explicitly says "id 12" or "task 12".
- If uncertain, set confidence below 0.6.

## Output schema (JSON only)
{
  "intent": "productivity|tasks|general",
  "confidence": 0.0,
  "tool": "create_task|delete_task|update_task_status|rename_task|none",
  "args": {},
  "reason": "short"
}
""".strip()


def _parse_json_obj(content: str) -> dict[str, Any] | None:
    s = (content or "").strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        return o if isinstance(o, dict) else None
    except Exception:
        return None


def route_message(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Returns router decision:
      - intent: productivity|tasks|general
      - tool: create_task|delete_task|none
      - args: dict
      - confidence: float
    Falls back to rule-based routing when LLM unavailable.
    """
    t = (user_text or "").strip()
    n = int(getattr(settings, "ASSISTANT_SESSION_MESSAGE_LIMIT", 24))
    recent = (recent_messages or [])[-n:]

    # LLM-only router.
    if not is_llm_configured():
        return {
            "intent": "general",
            "tool": "none",
            "args": {},
            "confidence": 0.0,
            "reason": "llm_not_configured",
            "error": "No LLM configured (set GROQ_API_KEY or OPENAI_API_KEY).",
        }

    try:
        human = json.dumps(
            {"user_message": t, "recent_messages": recent},
            ensure_ascii=False,
            default=str,
        )[:14000]
        raw, _ = invoke_system_human_resilient(ROUTER_SYSTEM, human)
        o = _parse_json_obj(raw) or {}
        intent = str(o.get("intent") or "").strip().lower()
        if intent not in INTENTS:
            intent = "general"
        tool = str(o.get("tool") or "none").strip()
        if tool not in ("create_task", "delete_task", "update_task_status", "rename_task", "none"):
            tool = "none"
        args = o.get("args") if isinstance(o.get("args"), dict) else {}
        try:
            conf = float(o.get("confidence") or 0.0)
        except Exception:
            conf = 0.0
        if conf < 0.6:
            # treat as "no tool routing" rather than risky execution
            tool = "none"
        return {
            "intent": intent,
            "tool": tool,
            "args": args,
            "confidence": conf,
            "reason": str(o.get("reason") or "")[:200],
        }
    except Exception:
        logger.exception("route_message LLM failed")
        return {
            "intent": "general",
            "tool": "none",
            "args": {},
            "confidence": 0.0,
            "reason": "llm_router_failed",
            "error": "LLM router failed; cannot route without LLM.",
        }

