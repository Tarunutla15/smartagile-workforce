"""Graph nodes: classify, load data, synthesize. User is passed via partial(...)."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

from ..brain import (
    build_productivity_context,
    build_productivity_snapshot_for_llm,
    format_productivity_markdown,
    productivity_result_json,
)

from .router import route_message
from .llm_factory import (
    invoke_system_human_resilient,
    is_llm_configured,
    llm_label,
)
from .state import AgentState
from .tools import (
    _infer_task_status_from_text,
    extract_create_task_args,
    extract_delete_task_args,
    extract_rename_task_args,
    extract_update_task_status_args,
    plan_compound_task_steps,
    plan_task_tool,
    run_create_task_tool,
    run_delete_task_tool,
    run_rename_task_tool,
    run_update_task_status_tool,
)

logger = logging.getLogger(__name__)
GRAPH_VERSION = 1


def _format_recent_messages(msgs: list[dict[str, Any]]) -> str:
    if not msgs:
        return ""
    n = int(getattr(settings, "ASSISTANT_SESSION_MESSAGE_LIMIT", 24))
    window = msgs[-n:] if len(msgs) > n else msgs
    lines = []
    for m in window:
        role = (m.get("role") or "").strip() or "user"
        content = (m.get("content") or "").strip()
        if not content:
            continue
        lines.append(f"{role}: {content}")
    return "\n".join(lines)[:10000]


def _format_memories(memories: list[dict[str, Any]]) -> str:
    if not memories:
        return ""
    lines = []
    for m in memories[:10]:
        typ = m.get("type") or "other"
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"- ({typ}) {content}")
    return "\n".join(lines)[:4000]


def _wrap(
    base: dict[str, Any],
    *,
    intent: str,
    llm_used: Any,
) -> dict[str, Any]:
    return {
        "graph_version": GRAPH_VERSION,
        "intent": intent,
        "llm": llm_label(llm_used) if llm_used is not None else None,
        **base,
    }


def classify_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    from .intent import wants_email_report

    user_text = (state or {}).get("user_text") or ""
    recent = (state or {}).get("recent_messages") or []
    route = route_message(user_text, recent_messages=recent)
    intent = (route or {}).get("intent") or "general"
    # Deterministic override: an explicit "email/send me ... report" request always
    # routes to the email-report flow, even if the LLM router labeled it productivity.
    if wants_email_report(user_text):
        intent = "report"
        route = {**(route or {}), "intent": "report"}
    return {"intent": intent, "route": route}


def load_memory_node(user: Any, state: AgentState) -> dict[str, Any]:
    """
    Retrieval layer: inject short-term session messages + long-term user memories.
    """
    from ..memory import recent_session_messages, retrieve_memories

    sid = (state or {}).get("session_id")
    user_text = (state or {}).get("user_text") or ""
    recent = recent_session_messages(user, int(sid)) if sid else []
    mem = retrieve_memories(user, user_text, limit=6)
    return {"recent_messages": recent, "memories": mem}


def load_productivity_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    """
    Productivity data loader (analytics agent).

    1. "right now / currently" -> rolling live window (existing behavior).
    2. Otherwise plan an analytics query (top_apps / time_on_app / focus_summary over a
       time window) and run it.
    3. If no specific analytics query is detected, fall back to today's full snapshot
       (keeps websites / most-opened / insight-card behavior unchanged).
    """
    from ..brain import build_current_productivity_context
    from .analytics import plan_analytics_query, run_analytics_query

    user_text = (state or {}).get("user_text") or ""
    recent = (state or {}).get("recent_messages") or []
    t = user_text.lower()

    if any(k in t for k in ("currently", "right now", "at the moment")):
        return {"productivity_ctx": build_current_productivity_context(user, minutes=15)}

    query = plan_analytics_query(user_text, recent_messages=recent)
    if query:
        ctx = run_analytics_query(user, query)
        if ctx is not None:
            return {"productivity_ctx": ctx}

    return {"productivity_ctx": build_productivity_context(user)}


def load_tasks_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    from tasks.models import Task

    items: list[dict[str, Any]] = []
    for t in (
        Task.objects.filter(user_id=user.pk)
        .select_related("project")
        .order_by("-created_at", "-id")[:30]
    ):
        items.append(
            {
                "id": t.pk,
                "title": t.title,
                "status": t.status,
                "project_id": t.project_id,
                "project_name": t.project.name if t.project_id else None,
                "created_at": t.created_at.isoformat() if getattr(t, "created_at", None) else None,
                "created_by_id": getattr(t, "created_by_id", None),
            }
        )
    return {"tasks_items": items}


def _run_compound_task_steps(
    user: Any,
    state: AgentState,
    steps: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Execute multiple task tools in order (one user message). Tracks last touched task id between steps.
    """
    user_text = (state or {}).get("user_text") or ""
    sid = (state or {}).get("session_id")
    sid_int = int(sid) if sid else None

    implicit: int | None = None
    lines: list[str] = []
    step_records: list[dict[str, Any]] = []
    last_task: dict[str, Any] | None = None

    for step in steps:
        name = step.get("name") or ""
        args = dict(step.get("args") or {})

        if name == "create_task":
            title = (args.get("title") or "").strip()
            status = (args.get("status") or "todo").strip()
            if status not in ("todo", "inProgress", "done"):
                status = "todo"
            if not title:
                lines.append("Couldn’t create a task — missing title in that step.")
                step_records.append({"tool": name, "error": "missing_title"})
                continue
            created = run_create_task_tool(user, title=title, status=status)
            implicit = int(created.get("id") or 0) or None
            last_task = dict(created)
            lines.append(
                f"Created task **{created.get('title')}** (ID **{created.get('id')}**, status **{created.get('status')}**)."
            )
            step_records.append({"kind": "task_created", "task": created})

        elif name == "update_task_status":
            tid = args.get("id")
            try:
                tid = int(tid) if tid is not None and tid != "" else None
            except Exception:
                tid = None
            title_u = args.get("title")
            status = (args.get("status") or "").strip()
            if status not in ("todo", "inProgress", "done"):
                inferred = _infer_task_status_from_text(user_text)
                if inferred:
                    status = inferred
            if status not in ("todo", "inProgress", "done"):
                lines.append("Skipped a status update — tell me todo, inProgress, or done.")
                step_records.append({"tool": name, "error": "missing_status"})
                continue
            use_implicit = implicit if tid is None and not (str(title_u or "").strip()) else None
            resu = run_update_task_status_tool(
                user,
                task_id=tid,
                title=title_u,
                status=status,
                session_id=sid_int,
                implicit_task_id=use_implicit,
            )
            if not resu.get("updated"):
                lines.append(f"Couldn’t update status ({resu.get('reason') or 'unknown'}).")
                step_records.append({"tool": name, "error": resu.get("reason"), "result": resu})
                continue
            task = resu.get("task") or {}
            implicit = int(task.get("id") or 0) or None
            last_task = dict(task)
            lines.append(
                f"Updated task **{task.get('title')}** (ID **{task.get('id')}**) to status **{task.get('status')}**."
            )
            step_records.append({"kind": "task_updated", "task": task})

        elif name == "rename_task":
            tid = args.get("id")
            try:
                tid = int(tid) if tid is not None and tid != "" else None
            except Exception:
                tid = None
            new_title = args.get("title")
            from_title = args.get("from_title")
            to_title = args.get("to_title")
            use_implicit = implicit if tid is None and not (str(from_title or "").strip()) else None
            resr = run_rename_task_tool(
                user,
                task_id=tid,
                from_title=from_title,
                to_title=to_title,
                title=new_title,
                session_id=sid_int,
                implicit_task_id=use_implicit,
            )
            if not resr.get("updated"):
                lines.append(f"Couldn’t rename ({resr.get('reason') or 'unknown'}).")
                step_records.append({"tool": name, "error": resr.get("reason"), "result": resr})
                continue
            task = resr.get("task") or {}
            implicit = int(task.get("id") or 0) or None
            last_task = dict(task)
            lines.append(f"Renamed task to **{task.get('title')}** (ID **{task.get('id')}**).")
            step_records.append({"kind": "task_renamed", "task": task})

        elif name == "delete_task":
            tid = args.get("id")
            try:
                tid = int(tid) if tid is not None and tid != "" else None
            except Exception:
                tid = None
            title_d = args.get("title")
            use_implicit = implicit if tid is None and not (str(title_d or "").strip()) else None
            res = run_delete_task_tool(
                user,
                task_id=tid,
                title=title_d,
                session_id=sid_int,
                implicit_task_id=use_implicit,
            )
            if not res.get("deleted"):
                lines.append(f"Couldn’t delete ({res.get('reason') or 'unknown'}).")
                step_records.append({"tool": name, "error": res.get("reason"), "result": res})
                continue
            deleted_task = res.get("task") or {}
            implicit = None
            note = res.get("note") or ""
            extra = (
                " (Several matched; removed the most recent.)"
                if note == "multiple_matches_deleted_most_recent"
                else ""
            )
            lines.append(f"Deleted task **{deleted_task.get('title')}** (ID **{deleted_task.get('id')}**).{extra}")
            step_records.append({"kind": "task_deleted", "task": deleted_task})
        else:
            step_records.append({"tool": name, "error": "unknown_tool"})

    assistant_text = "\n\n".join(lines) if lines else "No actions completed."
    payload: dict[str, Any] = {
        "kind": "compound",
        "steps": step_records,
        "step_count": len(step_records),
    }
    if last_task:
        payload["last_task"] = last_task
    return {
        "tool_action": {"name": "compound", "steps": steps, "results": step_records},
        "assistant_text": assistant_text,
        "result_json": _wrap(payload, intent="tasks", llm_used=None),
    }


def tool_tasks_node(user: Any, state: AgentState) -> dict[str, Any]:
    """
    Tool execution for tasks intent (agent behavior).
    Currently supports: create_task.
    """
    user_text = (state or {}).get("user_text") or ""
    recent = (state or {}).get("recent_messages") or []

    compound = plan_compound_task_steps(user_text, recent_messages=recent)
    planned: dict[str, Any] | None = None
    if compound is not None:
        if len(compound) > 1:
            return _run_compound_task_steps(user, state, compound)
        if len(compound) == 1:
            planned = compound[0]

    # Prefer the router plan if present (saves a second router call).
    route = (state or {}).get("route") or {}
    if planned is None:
        if isinstance(route, dict) and route.get("tool") in ("create_task", "delete_task", "update_task_status", "rename_task"):
            planned = {"name": route.get("tool"), "args": route.get("args") or {}}
        else:
            planned = plan_task_tool(user_text, recent_messages=recent)
    if not planned:
        return {"tool_action": None}
    tool_name = planned.get("name")
    if tool_name not in ("create_task", "delete_task", "update_task_status", "rename_task"):
        return {"tool_action": planned}

    if tool_name == "create_task":
        exc = extract_create_task_args(user_text, recent_messages=recent) or {}
        args = {**exc, **(planned.get("args") or {})}
        title = (args.get("title") or "").strip()
        status = (args.get("status") or "todo").strip()
        if not title:
            return {
                "assistant_text": "Tell me the task title you want me to create.",
                "result_json": _wrap(
                    {"kind": "tool_error", "tool": "create_task", "error": "missing_title"},
                    intent="tasks",
                    llm_used=None,
                ),
            }

        created = run_create_task_tool(user, title=title, status=status)
        text = (
            f"Created task **{created.get('title')}** (ID **{created.get('id')}**, status **{created.get('status')}**)."
            + (f"\n\n- **Project:** {created.get('project_name')}" if created.get("project_name") else "")
        )
        return {
            "tool_action": {"name": "create_task", "args": args, "result": created},
            "assistant_text": text,
            "result_json": _wrap(
                {"kind": "task_created", "task": created},
                intent="tasks",
                llm_used=None,
            ),
        }

    if tool_name == "update_task_status":
        exu = extract_update_task_status_args(user_text, recent_messages=recent) or {}
        argsu = {**exu, **(planned.get("args") or {})}
        tid = argsu.get("id")
        try:
            tid = int(tid) if tid is not None and tid != "" else None
        except Exception:
            tid = None
        title = argsu.get("title")
        status = (argsu.get("status") or "").strip()
        if status not in ("todo", "inProgress", "done"):
            inferred = _infer_task_status_from_text(user_text)
            if inferred:
                status = inferred
        if status not in ("todo", "inProgress", "done"):
            return {
                "assistant_text": "Tell me what status to set (todo, inProgress, or done).",
                "result_json": _wrap(
                    {"kind": "tool_error", "tool": "update_task_status", "error": "missing_status"},
                    intent="tasks",
                    llm_used=None,
                ),
            }
        sid = (state or {}).get("session_id")
        resu = run_update_task_status_tool(
            user,
            task_id=tid,
            title=title,
            status=status,
            session_id=int(sid) if sid else None,
        )
        if not resu.get("updated"):
            reason = resu.get("reason") or ""
            if reason == "missing_identifier":
                hint = (
                    "I don’t know which task you mean yet. Try something like "
                    "**make it in progress** right after creating a task in this chat, "
                    "or say **mark \"your title\" done**."
                )
            else:
                hint = (
                    "I couldn’t find that task on your current account to update. "
                    "Try quoting the exact title or the task **ID**."
                )
            return {
                "assistant_text": hint,
                "result_json": _wrap(
                    {"kind": "tool_error", "tool": "update_task_status", "error": reason, "result": resu},
                    intent="tasks",
                    llm_used=None,
                ),
            }
        task = resu.get("task") or {}
        textu = f"Updated task **{task.get('title')}** (ID **{task.get('id')}**) to status **{task.get('status')}**."
        return {
            "tool_action": {"name": "update_task_status", "args": argsu, "result": resu},
            "assistant_text": textu,
            "result_json": _wrap(
                {"kind": "task_updated", "task": task},
                intent="tasks",
                llm_used=None,
            ),
        }

    if tool_name == "rename_task":
        exr = extract_rename_task_args(user_text) or {}
        argsr = {**exr, **(planned.get("args") or {})}
        tid = argsr.get("id")
        try:
            tid = int(tid) if tid is not None and tid != "" else None
        except Exception:
            tid = None
        new_title = argsr.get("title")
        from_title = argsr.get("from_title")
        to_title = argsr.get("to_title")
        sid = (state or {}).get("session_id")
        resr = run_rename_task_tool(
            user,
            task_id=tid,
            from_title=from_title,
            to_title=to_title,
            title=new_title,
            session_id=int(sid) if sid else None,
        )
        if not resr.get("updated"):
            return {
                "assistant_text": "I couldn’t rename that task. Try: `rename \"old title\" to \"new title\"`.",
                "result_json": _wrap(
                    {"kind": "tool_error", "tool": "rename_task", "error": resr.get("reason"), "result": resr},
                    intent="tasks",
                    llm_used=None,
                ),
            }
        task = resr.get("task") or {}
        textr = f"Renamed task to **{task.get('title')}** (ID **{task.get('id')}**)."
        return {
            "tool_action": {"name": "rename_task", "args": argsr, "result": resr},
            "assistant_text": textr,
            "result_json": _wrap(
                {"kind": "task_renamed", "task": task},
                intent="tasks",
                llm_used=None,
            ),
        }

    # delete_task
    exd = extract_delete_task_args(user_text) or {}
    args2 = {**exd, **(planned.get("args") or {})}
    tid_d = args2.get("id")
    try:
        tid_d = int(tid_d) if tid_d is not None and tid_d != "" else None
    except Exception:
        tid_d = None
    sid = (state or {}).get("session_id")
    res = run_delete_task_tool(
        user,
        task_id=tid_d,
        title=args2.get("title"),
        session_id=int(sid) if sid else None,
    )
    if not res.get("deleted"):
        reason = res.get("reason") or "unknown"
        if reason == "multiple_matches":
            cands = res.get("candidates") or []
            lines = [f"- ID **{c.get('id')}**: {c.get('title')} ({c.get('status')})" for c in cands[:5]]
            msg = (
                "I found multiple tasks that match. Reply with the **task ID** you want me to delete:\n\n"
                + "\n".join(lines)
            )
        elif reason == "not_found":
            other = int(res.get("other_user_exact_match_count") or 0)
            recent = res.get("your_recent_tasks") or []
            hint = (
                "It looks like that exact title exists under a **different account**. "
                "Make sure you're logged into the same account that created/owns that task, then try again."
                if other > 0
                else ""
            )
            lines = []
            for x in recent[:6]:
                lines.append(f"- ID **{x.get('id')}**: {x.get('title')} ({x.get('status')})")
            recent_block = ("\n\nHere are your most recent tasks on this account:\n" + "\n".join(lines)) if lines else ""
            msg = (
                "I couldn’t find a matching task to delete for your current account. "
                "If you share the task **ID** (e.g. `delete task 12`), I can delete it.\n\n"
                + hint
                + recent_block
            )
        else:
            msg = "Tell me which task to delete (task **ID** is best)."
        return {
            "tool_action": {"name": "delete_task", "args": args2, "result": res},
            "assistant_text": msg,
            "result_json": _wrap(
                {"kind": "tool_error", "tool": "delete_task", "error": reason, "result": res},
                intent="tasks",
                llm_used=None,
            ),
        }

    deleted_task = res.get("task") or {}
    note = res.get("note") or ""
    extra = ""
    if note == "multiple_matches_deleted_most_recent":
        extra = " (Matched multiple tasks by that title; deleted the most recent one.)"
    text2 = f"Deleted task **{deleted_task.get('title')}** (ID **{deleted_task.get('id')}**).{extra}"
    return {
        "tool_action": {"name": "delete_task", "args": args2, "result": res},
        "assistant_text": text2,
        "result_json": _wrap(
            {"kind": "task_deleted", "task": deleted_task},
            intent="tasks",
            llm_used=None,
        ),
    }


def email_report_node(user: Any, state: AgentState) -> dict[str, Any]:
    """
    Build a usage report for the requested period and return a DRAFT (no email sent here).
    The user confirms via the chat card -> the confirm endpoint actually sends it.
    """
    from ..report import (
        build_usage_report,
        extract_recipient,
        render_report_email,
        resolve_report_period,
        summary_preview,
    )

    user_text = (state or {}).get("user_text") or ""
    period = resolve_report_period(user_text)
    default_email = (getattr(user, "email", "") or "").strip()
    recipient, explicit = extract_recipient(user_text, default_email)

    report = build_usage_report(user, period)
    subject, _html, _text = render_report_email(report, user=user)
    preview = summary_preview(report)

    draft = {
        "period": period,
        "period_label": report.get("period_label"),
        "recipient": recipient,
        "recipient_explicit": explicit,
        "subject": subject,
        "preview": preview,
        "has_data": report.get("has_data"),
        "summary": report.get("summary"),
        "top_apps": (report.get("top_apps") or [])[:5],
        "top_sites": (report.get("top_sites") or [])[:5],
        "categories": (report.get("categories") or [])[:5],
    }

    label = report.get("period_label") or "your activity"
    if recipient:
        text = (
            f"Here is a draft of your **{label}** usage report for **{recipient}**.\n\n"
            f"{preview}\n\n"
            "Review it below and hit **Send** to email it (you can change the address first)."
        )
    else:
        text = (
            f"I prepared your **{label}** usage report.\n\n"
            f"{preview}\n\n"
            "Tell me which email address to send it to (or type it in the box below), then hit **Send**."
        )

    return {
        "assistant_text": text,
        "result_json": _wrap(
            {"kind": "email_report_draft", "draft": draft},
            intent="report",
            llm_used=None,
        ),
    }


def synthesize_productivity_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    ctx = (state or {}).get("productivity_ctx") or build_productivity_context(user)
    user_text = (state or {}).get("user_text") or ""
    recent = (state or {}).get("recent_messages") or []
    memories = (state or {}).get("memories") or []
    use_llm = bool(getattr(settings, "ASSISTANT_LLM_SYNTHESIZE", True))
    base = productivity_result_json(ctx)
    llm: Any = None
    if use_llm and is_llm_configured():
        try:
            system = (
                "You are SmartAgile's in-app assistant. Answer using ONLY the JSON context below. "
                "Do not invent or guess metrics. Answer the user's question directly and only include "
                "extra sections (top apps / websites) if the user explicitly asked for them. "
                "The context covers the period named in the `date` field (e.g. 'today', 'this week', "
                "'the last 7 days'); phrase your answer around THAT period, not 'today' unless that is it. "
                "If has_data is false, say there is no tracked activity for that period yet (desktop agent "
                "must be running). "
                "If an `app_focus` object is present, the user asked about ONE specific app: report its "
                "**duration_human** and **open_count** for the period; if app_focus.matched is false, say "
                "that app had no tracked usage in that period. Do not list other apps in that case. "
                "If a `site_focus` object is present, the user asked about ONE specific website: report its "
                "**duration_human** and **open_count** for the period (these come from page TITLES, not URLs); "
                "if site_focus.matched is false, say that site had no tracked usage in that period. "
                "If a `category_breakdown` object is present, the user asked about categories or work vs "
                "distraction: lead with **work_duration_human** vs **distracted_duration_human** (and focus_score "
                "if useful), then list the top categories from its `categories` array with duration_human. "
                "If a `comparison` object is present, the user compared two periods: state both sides "
                "(comparison.current.value_human for current.label, comparison.previous.value_human for "
                "previous.label), then the change using comparison.direction (up/down/same), comparison.delta_human "
                "and comparison.pct_change. Frame it as the metric in comparison.metric (e.g. focus, time on an app/site). "
                "If a `trend` object is present, describe how the metric moved over time: lead with "
                "trend.summary.direction (up/down/flat), then start->end (summary.first_human -> summary.last_human), "
                "the peak (summary.max_bucket at summary.max_human) and low point (summary.min_bucket at "
                "summary.min_human), and the average (summary.avg_human). Summarize the shape — do NOT list every "
                "point. For focus the values are percentages. "
                "If an `explanation` object is present, the user asked WHY (a diagnosis): give a brief, supportive "
                "productivity-coach answer. State the focus_score and work vs distraction "
                "(work_duration_human / distracted_duration_human), compare to the prior period using "
                "explanation.vs_previous (direction + previous_focus), then call out the biggest drivers from "
                "explanation.top_distraction_categories and explanation.top_distraction_apps (with duration_human). "
                "Finish with 1–2 specific, actionable suggestions. Be concise and encouraging, never preachy. "
                "If browser_pages is present (with a `browser` or `chrome` object), and the user asked about "
                "websites/pages, list the top entries from most_time_in_pages with duration_human (page TITLES, not URLs). "
                "If the user asks which app/application they spent most time on, use "
                "app_activity.most_time_in_apps and list the top 3–5 with durations. "
                "If the user asks which app was opened most times / most frequently / most opened, use "
                "app_activity.most_opened_apps and rank by open_count (not duration). "
                "If the user asks about focus / distraction / deep work / context switching, use the "
                "`features` object (focus_score, work_duration_seconds, distracted_duration_seconds, "
                "app_switch_count, deep_work_segment_count). "
                "If the user asks which websites they visited in Chrome, use "
                "browser_pages.chrome.most_time_in_pages (may be null for windowed queries). Important: "
                "these are tab/page TITLES, not guaranteed URLs; say that clearly and list the top 5. "
                "If the context contains a window object with mode='fallback_to_today', tell the user "
                "there was no recent (last N minutes) activity so you used today's totals instead. "
                "When presenting durations, prefer **duration_human** (e.g. '1h 12m') if present; "
                "otherwise convert duration_seconds into hours/minutes (avoid raw seconds). "
                "Be concise, friendly, use **bold** for key numbers that appear in the data."
            )
            human = (
                f"User message:\n{user_text}\n\n"
                f"Recent chat context (may include preferences):\n{_format_recent_messages(recent)}\n\n"
                f"User memory (may include habits/preferences; do not invent):\n{_format_memories(memories)}\n\n"
                f"Authoritative productivity JSON:\n{build_productivity_snapshot_for_llm(ctx)}"
            )
            text, llm = invoke_system_human_resilient(system, human)
        except Exception:  # pragma: no cover
            logger.exception("synthesize productivity LLM failed; using template")
            text = format_productivity_markdown(ctx)
            llm = None
    else:
        text = format_productivity_markdown(ctx)

    rj = _wrap(
        {
            **base,
            "retrieval": {
                "recent_messages_count": len(recent),
                "memories": memories[:6],
            },
        },
        intent="productivity",
        llm_used=llm,
    )
    return {"assistant_text": text, "result_json": rj}


def synthesize_tasks_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    user_text = (state or {}).get("user_text") or ""
    items = (state or {}).get("tasks_items") or []
    recent = (state or {}).get("recent_messages") or []
    memories = (state or {}).get("memories") or []
    use_llm = bool(getattr(settings, "ASSISTANT_LLM_SYNTHESIZE", True))
    llm: Any = None

    # Derive "pending" locally so the LLM can answer follow-ups precisely.
    pending = [x for x in items if str(x.get("status") or "").lower() not in ("done",)]

    base: dict[str, Any] = {
        "kind": "tasks_snapshot",
        "count": len(items),
        "pending_count": len(pending),
        "tasks": items,
    }

    if use_llm and is_llm_configured():
        try:
            system = (
                "You are SmartAgile's in-app assistant. Summarize the user's task list. "
                "Use ONLY the JSON task list. Do not invent tasks. If the list is empty, say so clearly. "
                "If the user asks about pending tasks, treat status != 'done' as pending. "
                "If the user asks 'what is that pending task' and there is exactly one pending task, "
                "describe that task clearly (title, status, project_name if present, created_at). "
                "Be concise; bullets are fine."
            )
            human = (
                f"User message:\n{user_text}\n\n"
                f"Recent chat context:\n{_format_recent_messages(recent)}\n\n"
                f"User memory:\n{_format_memories(memories)}\n\n"
                f"Tasks (authoritative):\n{json.dumps(items, default=str)[:20000]}\n\n"
                f"Pending (derived):\n{json.dumps(pending, default=str)[:10000]}"
            )
            text, llm = invoke_system_human_resilient(system, human)
        except Exception:  # pragma: no cover
            logger.exception("synthesize tasks LLM failed; using template")
            if pending:
                lines = []
                for x in pending[:20]:
                    proj = x.get("project_name")
                    meta = []
                    if proj:
                        meta.append(str(proj))
                    if x.get("created_at"):
                        meta.append(f"created {x.get('created_at')}")
                    meta_s = f" — {' · '.join(meta)}" if meta else ""
                    lines.append(f"- **{x.get('title')}** (ID {x.get('id')}, {x.get('status')}){meta_s}")
                text = "Your pending tasks:\n\n" + "\n".join(lines)
            else:
                text = "You have no pending tasks in SmartAgile right now."
            llm = None
    elif items:
        # Non-LLM: answer pending-focused questions more directly.
        t = user_text.lower()
        if ("pending" in t or "todo" in t or "to do" in t) and pending:
            lines = []
            for x in pending[:20]:
                proj = x.get("project_name")
                meta = []
                if proj:
                    meta.append(str(proj))
                if x.get("created_at"):
                    meta.append(f"created {x.get('created_at')}")
                meta_s = f" — {' · '.join(meta)}" if meta else ""
                lines.append(f"- **{x.get('title')}** (ID {x.get('id')}, {x.get('status')}){meta_s}")
            text = "Your pending tasks:\n\n" + "\n".join(lines)
        elif ("what is" in t and "that" in t and "pending" in t) and len(pending) == 1:
            x = pending[0]
            proj = x.get("project_name") or "No project"
            ca = x.get("created_at") or "unknown time"
            text = (
                f"Your pending task is **{x.get('title')}** (ID **{x.get('id')}**, status **{x.get('status')}**).\n\n"
                f"- **Project:** {proj}\n"
                f"- **Created:** {ca}"
            )
        elif pending:
            lines = [f"- **{x.get('title')}** (ID {x.get('id')}, {x.get('status')})" for x in pending[:20]]
            text = "Here are your pending tasks:\n\n" + "\n".join(lines)
        else:
            text = "You have no pending tasks in SmartAgile right now."
    else:
        text = (
            "I don't see any tasks assigned to you in SmartAgile yet. "
            "You can add them from the Tasks section of your dashboard."
        )

    rj = _wrap(
        {
            **base,
            "retrieval": {
                "recent_messages_count": len(recent),
                "memories": memories[:6],
            },
        },
        intent="tasks",
        llm_used=llm,
    )
    return {"assistant_text": text, "result_json": rj}


def synthesize_general_node(user: Any, state: AgentState) -> dict[str, Any]:  # noqa: ARG001
    user_text = (state or {}).get("user_text") or ""
    recent = (state or {}).get("recent_messages") or []
    memories = (state or {}).get("memories") or []
    use_llm = bool(getattr(settings, "ASSISTANT_LLM_SYNTHESIZE", True))
    llm: Any = None
    base: dict[str, Any] = {"kind": "general"}

    if use_llm and is_llm_configured():
        try:
            system = (
                "You are SmartAgile's friendly in-app assistant. "
                "The app is about work productivity and tasks. "
                "Keep answers short. If the user is only greeting, greet back. "
                "Do not claim to have their personal metrics. "
                "Suggest they ask about productivity/usage or tasks in SmartAgile if relevant."
            )
            human = (
                f"User message:\n{user_text or 'Hello'}\n\n"
                f"Recent chat context:\n{_format_recent_messages(recent)}\n\n"
                f"User memory:\n{_format_memories(memories)}"
            )
            text, llm = invoke_system_human_resilient(system, human)
        except Exception:  # pragma: no cover
            logger.exception("synthesize general LLM failed; using template")
            text = _static_general()
            llm = None
    else:
        text = _static_general()
        llm = None

    rj = _wrap(
        {
            **base,
            "retrieval": {
                "recent_messages_count": len(recent),
                "memories": memories[:6],
            },
        },
        intent="general",
        llm_used=llm,
    )
    return {"assistant_text": text, "result_json": rj}


def _static_general() -> str:
    return (
        "I am your SmartAgile assistant. I can help with your **productivity and usage** "
        "(focus, distraction, app switching) and your **tasks** in the app. "
        "What would you like to know?"
    )


def route_after_classify(state: AgentState) -> str:
    return (state or {}).get("intent") or "general"
