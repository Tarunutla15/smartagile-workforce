from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings
from django.utils import timezone

from .llm_factory import invoke_system_human_resilient, is_llm_configured


def _recent_window(recent_messages: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    n = int(getattr(settings, "ASSISTANT_SESSION_MESSAGE_LIMIT", 24))
    r = recent_messages or []
    return r[-n:] if len(r) > n else r

logger = logging.getLogger(__name__)


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


_TOOL_ROUTER_SYSTEM = """
You are a STRICT tool router for SmartAgile tasks.

You must decide if the user wants an ACTION (tool call) or is just asking a question.

## Available tools
1) create_task
   - Use when the user asks to create/add a task.
   - Args JSON schema: {"title": "<string>", "status": "todo|inProgress|done"}

2) delete_task
   - Use when the user asks to delete/remove a task.
   - Args JSON schema: {"id": <int>} OR {"title": "<string>"} OR {} (when user says "delete this" and we should use chat context)

3) update_task_status
   - Use when the user asks to mark a task done/todo/in progress, or change its status.
   - Args JSON schema: {"id": <int>, "status":"todo|inProgress|done"} OR {"title":"<string>","status":"todo|inProgress|done"}

4) rename_task
   - Use when the user asks to change/rename the title of a task.
   - Args JSON schema:
     - {"id": <int>, "title": "<new title>"} OR
     - {"from_title": "<old title>", "to_title": "<new title>"}

## Rules
- Output JSON ONLY (no markdown, no extra text).
- If user intent is unclear, output tool="none".
- `recent_messages` lists prior turns (oldest first). For pronouns ("it", "that task"), tie the action to the **latest** matching subject in that history (nearest to the bottom before the current message).
- Only choose from: tool = "create_task" | "delete_task" | "update_task_status" | "rename_task" | "none".
- If status is mentioned as "inprogress" / "in progress" → "inProgress".
- If the user provides a quoted task title, use it as title.
- DO NOT treat arbitrary numbers as task ids (e.g., "6 PM" is not an id). Only treat id when message explicitly says "id 12" or "task 12".

## Output format (JSON only)
{"tool":"<tool-name>","confidence":0.0,"args":{...},"reason":"short"}
""".strip()


COMPOUND_PLAN_SYSTEM = """
You plan SmartAgile TASK actions from ONE user message.
The user may combine several commands (e.g. "delete that task and create one named …", "mark done and delete it",
"rename X to Y then set it in progress"). Typoes like "nad" instead of "and" still mean two actions.

Output JSON ONLY:
{"steps":[{"tool":"<create_task|delete_task|update_task_status|rename_task>","args":{}}]}

Rules:
- **Order matters**: list steps in the order they should run (usually delete/remove before create/replace when the user says delete … and create …).
- Args (same as single-step tools):
  - create_task: {"title":"<string>","status":"todo|inProgress|done"}
  - delete_task: {"id":<int>} OR {"title":"<string>"} OR {} when they mean "that task" / "the one we updated" — use {} and rely on chat/session.
  - update_task_status: {"id":<int>,"status":"..."} OR {"title":"<string>","status":"..."} OR {"status":"..."} only.
  - rename_task: {"id":<int>,"title":"<new>"} OR {"from_title":"<old>","to_title":"<new>"}.
- Use recent_messages + user_message to interpret "the updated task", "that", "it".
- If there is only one action in the message, still return {"steps":[ one step ]}.
- Maximum 8 steps. Numbers from times like "6 PM" are NOT task ids unless they say "task 12" / "id 12".
""".strip()


def plan_compound_task_steps(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]] | None:
    """
    Parse 1..N task tool steps from one user message.
    Returns None when LLM is unavailable or parsing/normalization fails (caller falls back to single planner).
    """
    t = (user_text or "").strip()
    if not t or not is_llm_configured():
        return None
    try:
        hist = _recent_window(recent_messages)
        human = json.dumps(
            {"user_message": t, "recent_messages": hist},
            ensure_ascii=False,
            default=str,
        )[:14000]
        raw, _ = invoke_system_human_resilient(COMPOUND_PLAN_SYSTEM, human)
        o = _parse_json_obj(raw) or {}
        steps_in = o.get("steps")
        if not isinstance(steps_in, list) or not steps_in:
            return None
        out: list[dict[str, Any]] = []
        allowed = frozenset({"create_task", "delete_task", "update_task_status", "rename_task"})
        for step in steps_in[:8]:
            if not isinstance(step, dict):
                continue
            tool = str(step.get("tool") or step.get("name") or "").strip()
            if tool not in allowed:
                continue
            args = step.get("args") if isinstance(step.get("args"), dict) else {}
            out.append({"name": tool, "args": args})
        return out if out else None
    except Exception:
        logger.exception("plan_compound_task_steps failed")
        return None


def plan_task_tool(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Detect and plan a tool call from a user message.

    Current tools:
    - create_task: create a Task for the current user
    - delete_task: delete a Task for the current user (by id or title match)
    """
    t = (user_text or "").strip()
    if not t:
        return None
    low = t.lower()

    # LLM-only planner.
    if not is_llm_configured():
        return None
    try:
        hist = _recent_window(recent_messages)
        human = json.dumps(
            {
                "user_message": t,
                "recent_messages": hist,
            },
            ensure_ascii=False,
            default=str,
        )[:12000]
        raw, _ = invoke_system_human_resilient(_TOOL_ROUTER_SYSTEM, human)
        o = _parse_json_obj(raw) or {}
        tool = str(o.get("tool") or o.get("name") or "").strip()
        conf = o.get("confidence")
        try:
            conf_f = float(conf) if conf is not None else 0.0
        except Exception:
            conf_f = 0.0
        if tool not in ("create_task", "delete_task", "update_task_status", "rename_task", "none"):
            tool = "none"
        if tool == "none" or conf_f < 0.6:
            return None
        args = o.get("args") or {}
        if not isinstance(args, dict):
            args = {}
        return {
            "name": tool,
            "args": args,
            "confidence": conf_f,
            "reason": str(o.get("reason") or "")[:200],
        }
    except Exception:
        logger.exception("plan_task_tool LLM router failed")
        return None


def _parse_create_task_json(content: str) -> dict[str, Any] | None:
    s = (content or "").strip()
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
        title = str(o.get("title", "")).strip()
        status = str(o.get("status", "todo")).strip()
        if not title:
            return None
        if status not in ("todo", "inProgress", "done"):
            status = "todo"
        return {"title": title[:100], "status": status}
    except Exception:
        return None


def _parse_update_task_json(content: str) -> dict[str, Any] | None:
    o = _parse_json_obj(content) or {}
    if not isinstance(o, dict):
        return None
    status = str(o.get("status") or "").strip()
    if status in ("inprogress", "in_progress", "in progress"):
        status = "inProgress"
    if status not in ("todo", "inProgress", "done"):
        return None
    if "id" in o and o.get("id") is not None:
        try:
            tid = int(o["id"])
            return {"id": tid, "status": status} if tid > 0 else None
        except Exception:
            return None
    title = str(o.get("title") or "").strip()
    if title:
        return {"title": title[:200], "status": status}
    # Pronoun follow-ups ("make it in progress"): status only; task resolved from chat session.
    return {"status": status}


def extract_create_task_args(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    Extract {title, status} for create_task.
    Uses LLM if configured; session history helps resolve "add it / that" to a concrete title.
    """
    t = (user_text or "").strip()
    if not t:
        return None

    if not is_llm_configured():
        return None
    try:
        hist = _recent_window(recent_messages)
        human = json.dumps(
            {"user_message": t, "recent_messages": hist},
            ensure_ascii=False,
            default=str,
        )[:12000]
        system = (
            "Extract task creation arguments. Reply with JSON only (no markdown). Schema: "
            '{"title":"...", "status":"todo|inProgress|done"}. '
            "If the message contains a time like '6 PM', keep it in the title. "
            "If status is not explicitly mentioned, use todo. "
            "If the user refers to 'it', 'that', or a prior topic, set title from the **most recent** "
            "relevant subject in recent_messages (bottom of transcript before this message)."
        )
        raw, _ = invoke_system_human_resilient(system, human)
        j = _parse_create_task_json(raw)
        return j
    except Exception:
        logger.exception("extract_create_task_args LLM failed")
        return None


def _infer_task_status_from_text(text: str) -> str | None:
    """Lightweight fallback when router/LLM omits structured status."""
    low = (text or "").lower()
    if re.search(r"\b(in\s*progress|inprogress)\b", low):
        return "inProgress"
    if re.search(r"\b(done|complete|completed|finish|finished)\b", low):
        return "done"
    if re.search(r"\b(todo|to\s*do|pending)\b", low):
        return "todo"
    return None


def extract_update_task_status_args(
    user_text: str,
    *,
    recent_messages: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """
    LLM: extract {id/status}, {title/status}, or {status} for pronoun follow-ups in the same chat.
    """
    t = (user_text or "").strip()
    if not t or not is_llm_configured():
        return None
    try:
        hist = _recent_window(recent_messages)
        human = json.dumps(
            {"user_message": t, "recent_messages": hist},
            ensure_ascii=False,
            default=str,
        )[:12000]
        system = (
            "Extract update_task_status arguments from the user message. Reply with JSON only. "
            "Schema: {\"id\": 12, \"status\": \"todo|inProgress|done\"} OR "
            "{\"title\":\"...\",\"status\":\"todo|inProgress|done\"} OR "
            "{\"status\":\"todo|inProgress|done\"} when the user means the task they just created or "
            "last mentioned (it / this task / that one) without naming it. "
            "If the user uses 'in progress', output status as inProgress. "
            "Do NOT treat arbitrary numbers as ids (e.g. '6 PM' is not an id) unless the message explicitly says 'id 12' or 'task 12'. "
            "If the user provides a quoted title, use it as title."
        )
        raw, _ = invoke_system_human_resilient(system, human)
        return _parse_update_task_json(raw)
    except Exception:
        logger.exception("extract_update_task_status_args LLM failed")
        return None


def extract_rename_task_args(user_text: str) -> dict[str, Any] | None:
    """
    LLM-only: extract args for rename_task.
    """
    t = (user_text or "").strip()
    if not t or not is_llm_configured():
        return None
    try:
        system = (
            "Extract rename_task arguments from the user message. Reply with JSON only. "
            "Schema: either {\"id\": 12, \"title\": \"<new title>\"} OR "
            "{\"from_title\":\"<old title>\",\"to_title\":\"<new title>\"}. "
            "If the user provides quoted strings, use them. "
            "Do NOT treat arbitrary numbers as ids unless the message explicitly says 'id 12' or 'task 12'."
        )
        raw, _ = invoke_system_human_resilient(system, f"User message:\n{t}")
        o = _parse_json_obj(raw) or {}
        if "id" in o and o.get("id") is not None and "title" in o:
            try:
                tid = int(o["id"])
            except Exception:
                return None
            new_title = str(o.get("title") or "").strip()
            if tid > 0 and new_title:
                return {"id": tid, "title": new_title[:200]}
            return None
        frm = str(o.get("from_title") or "").strip()
        to = str(o.get("to_title") or "").strip()
        if frm and to:
            return {"from_title": frm[:200], "to_title": to[:200]}
        return None
    except Exception:
        logger.exception("extract_rename_task_args LLM failed")
        return None


def run_create_task_tool(user, *, title: str, status: str = "todo") -> dict[str, Any]:
    from tasks.models import Task

    now = timezone.now()
    t = Task.objects.create(
        title=title[:100],
        status=status if status in ("todo", "inProgress", "done") else "todo",
        user_id=user.pk,
        created_by_id=user.pk,
        created_at=now,
    )
    return {
        "id": t.pk,
        "title": t.title,
        "status": t.status,
        "project_id": t.project_id,
        "project_name": t.project.name if t.project_id else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


def _extract_task_id(text: str) -> int | None:
    """
    Extract a task id only when the user clearly indicates an id.

    We intentionally do NOT treat arbitrary numbers as ids (e.g. "6 PM").
    Supported patterns:
    - "id 12" / "ID:12"
    - "task 12"
    - "task #12"
    """
    s = text or ""
    m = re.search(r"\b(?:task\s*#?\s*|id\s*:?\s*)(\d{1,9})\b", s, re.IGNORECASE)
    if not m:
        return None
    try:
        v = int(m.group(1))
        return v if v > 0 else None
    except Exception:
        return None


def extract_delete_task_args(user_text: str) -> dict[str, Any] | None:
    """
    Extract args for delete_task.
    Returns:
      - {"id": int} or {"title": str}
    """
    t = (user_text or "").strip()
    if not t:
        return None

    if not is_llm_configured():
        return None
    try:
        system = (
            "Extract delete_task arguments. Reply with JSON only. "
            "Schema: either {\"id\": 12} or {\"title\": \"...\"} or {} when user says 'delete this'. "
            "Important: DO NOT treat arbitrary numbers as ids (e.g. '6 PM' is not an id). "
            "Only treat id when the message explicitly says 'id 12' or 'task 12'. "
            "If the user provides a quoted title, use it."
        )
        raw, _ = invoke_system_human_resilient(system, f"User message:\n{t}")
        o = _parse_json_obj(raw) or {}
        if "id" in o:
            try:
                return {"id": int(o["id"])}
            except Exception:
                return None
        if "title" in o:
            title = str(o.get("title") or "").strip()
            return {"title": title[:200]} if title else None
        # allow {}
        return {}
    except Exception:
        logger.exception("extract_delete_task_args LLM failed")
        return None


def fallback_last_referenced_task_id(user, session_id: int | None) -> int | None:
    """
    Resolve 'this task' / follow-ups from the same chat: walk recent assistant turns and use
    the latest tool result that still references a concrete task (created/updated/renamed).
    """
    del user  # scoped by session + ownership checks at call site
    if not session_id:
        return None
    try:
        from ..models import AssistantChatMessage

        msgs = (
            AssistantChatMessage.objects.filter(
                session_id=int(session_id),
                role=AssistantChatMessage.Role.ASSISTANT,
            )
            .exclude(result_json=None)
            .order_by("-created_at", "-id")[:30]
        )
        for m in msgs:
            rj = m.result_json
            if not isinstance(rj, dict):
                continue
            k = rj.get("kind")
            if k == "compound":
                task = rj.get("last_task")
                if isinstance(task, dict):
                    tid = task.get("id")
                    if tid is not None:
                        try:
                            return int(tid)
                        except Exception:
                            continue
                continue
            if k not in ("task_created", "task_updated", "task_renamed"):
                continue
            task = rj.get("task")
            if isinstance(task, dict):
                tid = task.get("id")
                if tid is not None:
                    try:
                        return int(tid)
                    except Exception:
                        continue
        return None
    except Exception:
        logger.exception("fallback_last_referenced_task_id failed")
        return None


def _fallback_last_created_task_from_session(user, session_id: int | None) -> int | None:
    """Backward-compatible name: last task referenced in session (not only created)."""
    return fallback_last_referenced_task_id(user, session_id)


def run_delete_task_tool(
    user,
    *,
    task_id: int | None = None,
    title: str | None = None,
    session_id: int | None = None,
    implicit_task_id: int | None = None,
) -> dict[str, Any]:
    """
    Delete a task owned by user.
    - If task_id is provided: delete that task if it belongs to user.
    - Else if title provided: delete if exactly one task matches (case-insensitive exact, then icontains).
    - implicit_task_id: same-request chain — “delete it” after a prior step touched that task.
    """
    from tasks.models import Task

    if not task_id and not title:
        task_id = implicit_task_id or fallback_last_referenced_task_id(user, session_id)

    if task_id:
        q = Task.objects.filter(pk=int(task_id), user_id=user.pk)
        t = q.select_related("project").first()
        if not t:
            return {"deleted": False, "reason": "not_found", "id": int(task_id)}
        payload = {
            "id": t.pk,
            "title": t.title,
            "status": t.status,
            "project_id": t.project_id,
            "project_name": t.project.name if t.project_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        q.delete()
        return {"deleted": True, "task": payload}

    title = (title or "").strip()
    if not title:
        return {"deleted": False, "reason": "missing_identifier"}

    base = Task.objects.filter(user_id=user.pk)
    exact = base.filter(title__iexact=title).order_by("-created_at", "-id")
    qs = exact if exact.exists() else base.filter(title__icontains=title).order_by("-created_at", "-id")
    matches = list(qs.select_related("project")[:5])
    if not matches:
        # Helpful diagnostics: task may exist but belong to a different user (common when
        # pairing/sessions switch accounts).
        other_count = Task.objects.filter(title__iexact=title).exclude(user_id=user.pk).count()
        recent = list(
            base.order_by("-created_at", "-id").values("id", "title", "status")[:8]
        )
        return {
            "deleted": False,
            "reason": "not_found",
            "title": title,
            "other_user_exact_match_count": int(other_count),
            "your_recent_tasks": recent,
            "your_user_id": int(user.pk),
        }
    if len(matches) > 1:
        # UX choice: user asked to delete by title and does not want IDs.
        # We delete the most recent match and report what happened.
        chosen = matches[0]
        payload_multi = {
            "id": chosen.pk,
            "title": chosen.title,
            "status": chosen.status,
            "project_id": chosen.project_id,
            "project_name": chosen.project.name if chosen.project_id else None,
            "created_at": chosen.created_at.isoformat() if chosen.created_at else None,
        }
        Task.objects.filter(pk=chosen.pk, user_id=user.pk).delete()
        return {
            "deleted": True,
            "task": payload_multi,
            "note": "multiple_matches_deleted_most_recent",
            "match_count_considered": len(matches),
            "candidates": [{"id": x.pk, "title": x.title, "status": x.status} for x in matches],
        }

    t = matches[0]
    payload2 = {
        "id": t.pk,
        "title": t.title,
        "status": t.status,
        "project_id": t.project_id,
        "project_name": t.project.name if t.project_id else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
    Task.objects.filter(pk=t.pk, user_id=user.pk).delete()
    return {"deleted": True, "task": payload2}


def run_update_task_status_tool(
    user,
    *,
    task_id: int | None = None,
    title: str | None = None,
    status: str,
    session_id: int | None = None,
    implicit_task_id: int | None = None,
) -> dict[str, Any]:
    from tasks.models import Task

    status = status if status in ("todo", "inProgress", "done") else "todo"
    base = Task.objects.filter(user_id=user.pk)

    t = None
    tid_use = int(task_id) if task_id is not None else None
    name = (title or "").strip()

    if tid_use is not None:
        t = base.select_related("project").filter(pk=int(tid_use)).first()
        if not t:
            return {"updated": False, "reason": "not_found", "id": int(tid_use)}
    elif name:
        exact = base.filter(title__iexact=name).order_by("-created_at", "-id")
        qs = exact if exact.exists() else base.filter(title__icontains=name).order_by("-created_at", "-id")
        matches = list(qs.select_related("project")[:5])
        if not matches:
            return {"updated": False, "reason": "not_found", "title": name}
        t = matches[0]
    else:
        tid_fb = implicit_task_id or fallback_last_referenced_task_id(user, session_id)
        if tid_fb:
            t = base.select_related("project").filter(pk=int(tid_fb)).first()
            if not t:
                return {"updated": False, "reason": "not_found", "id": int(tid_fb)}
        else:
            return {"updated": False, "reason": "missing_identifier"}

    t.status = status
    t.save(update_fields=["status"])
    return {
        "updated": True,
        "task": {
            "id": t.pk,
            "title": t.title,
            "status": t.status,
            "project_id": t.project_id,
            "project_name": t.project.name if t.project_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "created_by_id": getattr(t, "created_by_id", None),
        },
    }


def run_rename_task_tool(
    user,
    *,
    task_id: int | None = None,
    from_title: str | None = None,
    to_title: str | None = None,
    title: str | None = None,
    session_id: int | None = None,
    implicit_task_id: int | None = None,
) -> dict[str, Any]:
    """
    Rename a task (update title) scoped to current user.
    Accepts:
      - task_id + title(new)
      - from_title(old) + to_title(new)
      - title(new) only → same-chat follow-up (“rename it to …”) uses session context
      - implicit_task_id: resolve “it” inside a multi-step compound request
    """
    from tasks.models import Task

    new_title = (title or to_title or "").strip()
    if not new_title:
        return {"updated": False, "reason": "missing_new_title"}
    new_title = new_title[:100]

    base = Task.objects.filter(user_id=user.pk)
    t = None
    tid_use = int(task_id) if task_id is not None else None

    if tid_use is not None:
        t = base.select_related("project").filter(pk=int(tid_use)).first()
        if not t:
            return {"updated": False, "reason": "not_found", "id": int(tid_use)}
    else:
        old = (from_title or "").strip()
        if old:
            exact = base.filter(title__iexact=old).order_by("-created_at", "-id")
            qs = exact if exact.exists() else base.filter(title__icontains=old).order_by("-created_at", "-id")
            matches = list(qs.select_related("project")[:5])
            if not matches:
                return {"updated": False, "reason": "not_found", "title": old}
            t = matches[0]
        else:
            tid_fb = implicit_task_id or fallback_last_referenced_task_id(user, session_id)
            if tid_fb:
                t = base.select_related("project").filter(pk=int(tid_fb)).first()
                if not t:
                    return {"updated": False, "reason": "not_found", "id": int(tid_fb)}
            else:
                return {"updated": False, "reason": "missing_identifier"}

    t.title = new_title
    t.save(update_fields=["title"])
    return {
        "updated": True,
        "task": {
            "id": t.pk,
            "title": t.title,
            "status": t.status,
            "project_id": t.project_id,
            "project_name": t.project.name if t.project_id else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "created_by_id": getattr(t, "created_by_id", None),
        },
    }

