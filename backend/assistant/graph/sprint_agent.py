"""
Sprint skill for the in-app assistant.

A self-contained agent that turns natural-language sprint requests into actions on
the ``sprints`` app, reusing its services (permissions + audited status changes) and
metrics (burndown / summary). Kept isolated from the existing tasks/productivity flows:
the graph routes here only when the message is sprint-related.

Capabilities
------------
- create a sprint
- start / complete a sprint
- add a work item (to a sprint or the backlog)
- move a work item between a sprint and the backlog
- change a work item's status (audited, so burndown stays correct)
- answer status / burndown / list-sprints questions

All planning actions are permission-checked via ``sprints.services.can_manage_project``.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .llm_factory import invoke_system_human_resilient, is_llm_configured

logger = logging.getLogger(__name__)

ACTIONS = frozenset(
    {
        "create_sprint",
        "start_sprint",
        "complete_sprint",
        "add_item",
        "move_item",
        "set_status",
        "status",
        "burndown",
        "list_items",
        "list_sprints",
        "team",
        "projects",
        "help",
    }
)

_SPRINT_WORD = re.compile(r"\bsprints?\b", re.IGNORECASE)
_BURNDOWN_WORD = re.compile(r"\bburn\s?down\b", re.IGNORECASE)
_CREATE_RE = re.compile(r"\b(create|new|add|make|set\s?up|start)\b", re.IGNORECASE)
_START_RE = re.compile(r"\b(start|begin|activate|kick\s?off|launch)\b", re.IGNORECASE)
_COMPLETE_RE = re.compile(r"\b(complete|finish|close|end|wrap\s?up)\b", re.IGNORECASE)
_LIST_RE = re.compile(r"\b(list|show|what|which|see|view)\b", re.IGNORECASE)
_STATUS_RE = re.compile(
    r"\b(status|progress|how\s+(?:is|are|much|many)|summary|going|on\s+track|left|remaining)\b",
    re.IGNORECASE,
)
_MOVE_RE = re.compile(r"\bmove\b", re.IGNORECASE)
# Team / roster queries: "who is in my team", "what is my team doing", "my teammates",
# "list the employees", "show the members/people/staff", etc.
_TEAM_RE = re.compile(
    r"\bteammates?\b|\bcolleagues?\b|\bco-?workers?\b|\bemployees?\b|\bstaff\b"
    r"|\b(?:my|the|our)\s+team\b"
    r"|\bteam(?:'s)?\s+(?:doing|working|tasks?|work|progress|members?|workload|roster)\b"
    r"|\b(?:list|show|see|view|who(?:'s| is| are)?)\s+(?:the\s+|all\s+|my\s+|our\s+)?"
    r"(?:employees?|members?|people|teammates?|developers?|devs|staff)\b"
    r"|\bwho(?:'s| is| are)\s+(?:in|on|working|doing)\b"
    r"|\bwho\s+else\b|\beveryone\b|\beach\s+(?:member|person)\b",
    re.IGNORECASE,
)


def wants_team(user_text: str) -> bool:
    return bool(_TEAM_RE.search(user_text or ""))


# Project questions: "what is the current project", "which project am I working on",
# "my projects", "what projects are we working on". Used to route to the sprint skill and
# answer with a real project listing (not personal tasks / doc-RAG).
_PROJECT_WORD = re.compile(r"\bprojects?\b", re.IGNORECASE)
_PROJECT_QUERY_RE = re.compile(
    r"\b(which|what|current|list|show|see|view|my|our|am\s+i|are\s+we|working\s+on|working|on\s+now)\b",
    re.IGNORECASE,
)
# Mutations the sprint skill can't do (projects are created/deleted elsewhere) — don't
# treat these as a project listing.
_PROJECT_MUTATE_RE = re.compile(r"\b(create|new|add|make|delete|remove|rename|set\s?up)\b", re.IGNORECASE)


def wants_project_query(user_text: str) -> bool:
    t = user_text or ""
    if not _PROJECT_WORD.search(t) or _PROJECT_MUTATE_RE.search(t):
        return False
    return bool(_PROJECT_QUERY_RE.search(t))

_ITEM_WORD = re.compile(r"\b(task|tasks|item|items|story|stories|bug|bugs|chore|spike|work\s?item|ticket|tickets)\b", re.IGNORECASE)
_BACKLOG_RE = re.compile(r"\bbacklog\b", re.IGNORECASE)
# Words that, together with a work-item noun, signal a "list items" query (any order):
# "list/show/what/which tasks", "pending/open/remaining tasks", "my tasks",
# "tasks assigned to me", "completed items", etc.
_ITEM_QUERY_KW = re.compile(
    r"\b(list|show|see|view|what|which|any|pending|open|remaining|incomplete|unfinished|"
    r"left|assigned|my|mine|i\s+have|todo|to\s?do|done|completed|finished|in\s?progress)\b",
    re.IGNORECASE,
)


def _is_item_list_query(text: str) -> bool:
    t = text or ""
    return bool(_ITEM_WORD.search(t) and _ITEM_QUERY_KW.search(t))
_ASSIGNED_ME_RE = re.compile(
    r"\b(assigned\s+to\s+me|my\s+(?:task|tasks|item|items|work)|for\s+me|i\s+have|mine)\b",
    re.IGNORECASE,
)
_PENDING_RE = re.compile(r"\b(pending|open|remaining|incomplete|unfinished|not\s+done|left|todo|to\s?do)\b", re.IGNORECASE)
_DONE_RE = re.compile(r"\b(done|completed|finished|complete)\b", re.IGNORECASE)
_INPROGRESS_RE = re.compile(r"\bin\s?progress|ongoing|doing|wip\b", re.IGNORECASE)


def _status_filter_from_text(text: str) -> str | None:
    t = text or ""
    if _INPROGRESS_RE.search(t):
        return "inProgress"
    if _PENDING_RE.search(t):
        return "pending"
    if _DONE_RE.search(t):
        return "done"
    return None


def wants_sprint(user_text: str) -> bool:
    """
    True when the message is about sprints specifically (so the assistant should use
    the sprint skill rather than the generic task agent).
    """
    t = user_text or ""
    if _BURNDOWN_WORD.search(t):
        return True
    if wants_team(t):
        return True
    if wants_project_query(t):
        return True
    if not _SPRINT_WORD.search(t):
        return False
    # The bare word "sprint" anywhere is a strong enough signal for this skill, which
    # also gracefully answers status/help; the generic task agent stays for plain tasks.
    return True


# --------------------------------------------------------------------------- #
# planning
# --------------------------------------------------------------------------- #
_PLANNER_SYSTEM = """You are SmartAgile's SPRINT planner. Convert the user's message into a single JSON object describing one sprint action. Reply with JSON ONLY, no markdown.

Schema:
{
  "action": one of ["create_sprint","start_sprint","complete_sprint","add_item","move_item","set_status","status","burndown","list_items","list_sprints","team","projects","help"],
  "project": string|null,        // project / team name if mentioned
  "sprint": string|null,         // sprint name if mentioned
  "title": string|null,          // work-item title (for add_item/move_item/set_status)
  "item_type": one of ["task","story","bug","chore","spike"]|null,
  "story_points": number|null,
  "status": one of ["todo","inProgress","done"]|null,         // target status for set_status
  "status_filter": one of ["pending","todo","inProgress","done","all"]|null,  // filter for list_items
  "assignee": one of ["me","all"]|null,                       // who, for list_items
  "goal": string|null,           // sprint goal (create_sprint)
  "start_date": "YYYY-MM-DD"|null,
  "end_date": "YYYY-MM-DD"|null,
  "move_to": "backlog"|string|null  // target sprint name or "backlog" (move_item / complete_sprint unfinished)
}

Functions (choose exactly one "action"):
- create_sprint   — make a new sprint.
- start_sprint    — activate a sprint.
- complete_sprint — close a sprint; set move_to="backlog" or a sprint name to move unfinished items.
- add_item        — add a work item (task/story/bug/chore/spike) to a sprint or the backlog.
- move_item       — move ONE work item between a sprint and the backlog (or another sprint).
- set_status      — change ONE work item's status (todo/inProgress/done).
- status          — a sprint's progress: completion %, items/points done, focus time.
- burndown        — a sprint's burndown trend / chart.
- list_items      — list work items in a sprint (optionally filtered by status and/or assignee).
- list_sprints    — list sprints (optionally for one project).
- team            — who is on the team and what each person is working on (roster / workload).
- projects        — which project(s) the user is on and each one's active sprint.
- help            — sprint-related but unclear.

Perspective:
- The message may start with "Perspective: me|team|project". With "me", prefer assignee="me" for list_items. With "team"/"project", listings cover the whole team (assignee="all") unless the user explicitly says my/mine/assigned to me.
- Anyone (employee, lead, manager, admin, stakeholder) may ask anything. Do NOT refuse based on role — the server enforces permissions afterwards. Your only job is to classify the intent and extract fields.

Disambiguation:
- "complete/finish/close the sprint AND move unfinished to the backlog" is ONE complete_sprint (move_to="backlog") — NOT move_item.
- Quoted text is a work-item or sprint title; prefer it.
- list_items status_filter: open/remaining/incomplete/not done/pending -> "pending"; completed/finished/done -> "done"; in progress/ongoing/wip -> "inProgress"; otherwise "all".
- "current/which/my/our project(s)" -> projects. "who/team/teammates/employees/staff/members/everyone" -> team.
- Only include fields you are confident about; use null otherwise.

Examples (message -> JSON):
- "create a sprint called Sprint 7 in Apollo with goal stabilize auth" -> {"action":"create_sprint","sprint":"Sprint 7","project":"Apollo","goal":"stabilize auth"}
- "start the sprint" -> {"action":"start_sprint"}
- "finish the sprint and push leftovers to the backlog" -> {"action":"complete_sprint","move_to":"backlog"}
- "add a story 'Payment gateway' worth 5 points to Sprint 7" -> {"action":"add_item","title":"Payment gateway","item_type":"story","story_points":5,"sprint":"Sprint 7"}
- "log a bug 'Login 500' in the backlog" -> {"action":"add_item","title":"Login 500","item_type":"bug","move_to":"backlog"}
- "move 'Payment gateway' to the backlog" -> {"action":"move_item","title":"Payment gateway","move_to":"backlog"}
- "mark 'Login page' as done" -> {"action":"set_status","title":"Login page","status":"done"}
- "I finished the onboarding screen" -> {"action":"set_status","title":"onboarding screen","status":"done"}
- "how is the sprint going" -> {"action":"status"}
- "how far along is Sprint 7" -> {"action":"status","sprint":"Sprint 7"}
- "what's the progress on the Website project" -> {"action":"status","project":"Website"}
- "show the burndown" -> {"action":"burndown"}
- "what are my open tasks this sprint" -> {"action":"list_items","assignee":"me","status_filter":"pending"}
- "what's been completed this sprint" -> {"action":"list_items","status_filter":"done"}
- "what is everyone working on" -> {"action":"team"}
- "who has open work on the team" -> {"action":"team"}
- "list the employees" -> {"action":"team"}
- "list all sprints" -> {"action":"list_sprints"}
- "show sprints in Apollo" -> {"action":"list_sprints","project":"Apollo"}
- "what project am I working on" -> {"action":"projects"}
- "what projects do we have" -> {"action":"projects"}"""


def _parse_plan_json(content: str) -> dict[str, Any] | None:
    s = (content or "").strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if not m:
        return None
    try:
        o = json.loads(m.group(0))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(o, dict):
        return None
    action = str(o.get("action") or "").strip()
    if action not in ACTIONS:
        return None
    return o


def _llm_plan(user_text: str, recent_text: str, scope: str | None = None) -> dict[str, Any] | None:
    try:
        parts = []
        if scope in ("me", "team", "project"):
            parts.append(f"Perspective: {scope}")
        if recent_text:
            parts.append(f"Recent conversation:\n{recent_text}")
        parts.append(f"Latest message:\n{user_text or ''}")
        human = "\n\n".join(parts)
        raw, _ = invoke_system_human_resilient(_PLANNER_SYSTEM, human)
        return _parse_plan_json(raw)
    except Exception:  # pragma: no cover
        logger.exception("sprint planner LLM failed")
        return None


def _normalize_status(value: str | None) -> str | None:
    s = (value or "").strip().lower().replace("_", " ").replace("-", " ")
    s = re.sub(r"\s+", " ", s)
    if not s:
        return None
    if s in ("done", "complete", "completed", "finished", "finish"):
        return "done"
    if s in ("in progress", "inprogress", "doing", "started", "wip", "ongoing"):
        return "inProgress"
    if s in ("todo", "to do", "backlog", "open", "new", "not started"):
        return "todo"
    return None


# "mark/set/change <item> as/to <status>" — pulls the status token out of the command so
# we can plan a set_status action deterministically (without relying on the LLM planner).
_SET_STATUS_CMD_RE = re.compile(
    r"\b(?:mark|set|change)\b.*?\b(?:as|to)\b\s+([a-z][a-z ]*?)(?:[.!?]|$)",
    re.IGNORECASE,
)


def _status_from_command(text: str | None) -> str | None:
    m = _SET_STATUS_CMD_RE.search(text or "")
    return _normalize_status(m.group(1)) if m else None


_QUOTED_RE = re.compile(r"[\"'\u201c\u201d\u2018\u2019]([^\"'\u201c\u201d\u2018\u2019]+)[\"'\u201c\u201d\u2018\u2019]")
_CALLED_RE = re.compile(r"\b(?:called|named|titled|name(?:d)?\s+it)\s+(.+?)(?:\s+(?:in|for|to|with|goal|from|starting)\b|[.!?]|$)", re.IGNORECASE)


def _extract_quoted(text: str) -> str | None:
    m = _QUOTED_RE.search(text or "")
    return m.group(1).strip() if m else None


def _rule_plan(user_text: str) -> dict[str, Any]:
    t = user_text or ""
    plan: dict[str, Any] = {"action": "help"}
    quoted = _extract_quoted(t)
    has_sprint = bool(_SPRINT_WORD.search(t))

    if _BURNDOWN_WORD.search(t):
        plan = {"action": "burndown"}
    elif _MOVE_RE.search(t) and not (_COMPLETE_RE.search(t) and has_sprint):
        # "move 'X' to backlog/sprint Y" — but NOT "complete the sprint and move
        # unfinished items to backlog", which is a complete_sprint action (handled below).
        plan = {"action": "move_item", "title": quoted}
        if _BACKLOG_RE.search(t):
            plan["move_to"] = "backlog"
        else:
            m = re.search(r"\bto\s+sprint\s+(.+?)(?:[.!?]|$)", t, re.IGNORECASE)
            if m:
                plan["move_to"] = m.group(1).strip()
    elif _status_from_command(t):
        plan = {"action": "set_status", "title": quoted, "status": _status_from_command(t)}
    elif _COMPLETE_RE.search(t) and has_sprint:
        plan = {"action": "complete_sprint"}
        if _BACKLOG_RE.search(t):
            plan["move_to"] = "backlog"
    elif _START_RE.search(t) and has_sprint and not _ITEM_WORD.search(t):
        plan = {"action": "start_sprint"}
    elif _CREATE_RE.search(t) and has_sprint and not _ITEM_WORD.search(t):
        name = quoted
        if not name:
            cm = _CALLED_RE.search(t)
            name = cm.group(1).strip() if cm else None
        plan = {"action": "create_sprint", "sprint": name}
    elif re.search(r"\b(add|create|new)\b", t, re.IGNORECASE) and _ITEM_WORD.search(t):
        title = quoted
        if not title:
            tm = re.search(r"\b(?:add|create)\b\s+(?:a\s+)?(?:task|item|story|bug|chore|spike|ticket)?\s*(.+?)(?:\s+to\b|[.!?]|$)", t, re.IGNORECASE)
            title = tm.group(1).strip() if tm else None
        plan = {"action": "add_item", "title": title}
        if _BACKLOG_RE.search(t):
            plan["move_to"] = "backlog"
        sm = re.search(r"\bto\s+sprint\s+(.+?)(?:[.!?]|$)", t, re.IGNORECASE)
        if sm:
            plan["sprint"] = sm.group(1).strip()
        tym = _ITEM_WORD.search(t)
        if tym:
            tv = tym.group(1).lower().replace("work item", "task").replace("ticket", "task")
            if tv in ("task", "story", "bug", "chore", "spike"):
                plan["item_type"] = tv
    elif _TEAM_RE.search(t):
        plan = {"action": "team"}
    elif wants_project_query(t):
        plan = {"action": "projects"}
    elif _LIST_RE.search(t) and re.search(r"\bsprints\b", t, re.IGNORECASE):
        plan = {"action": "list_sprints"}
    elif _is_item_list_query(t):
        plan = {"action": "list_items", "status_filter": _status_filter_from_text(t)}
        if _ASSIGNED_ME_RE.search(t):
            plan["assignee"] = "me"
    elif _STATUS_RE.search(t) and has_sprint:
        plan = {"action": "status"}
    elif has_sprint:
        plan = {"action": "status"}
    return plan


def plan_sprint_action(
    user_text: str, recent_text: str = "", scope: str | None = None
) -> dict[str, Any]:
    """LLM planner (when configured) merged with the deterministic rule planner."""
    rule = _rule_plan(user_text)
    if is_llm_configured():
        llm = _llm_plan(user_text, recent_text, scope=scope)
        if llm:
            # Prefer the LLM's action/args, but backfill from rules where the LLM left blanks.
            merged = {**rule, **{k: v for k, v in llm.items() if v not in (None, "")}}
            # For item listings the deterministic filters are more reliable than the
            # LLM's (e.g. "pending" must stay "pending", not collapse to "todo").
            if merged.get("action") == "list_items" and rule.get("action") == "list_items":
                if rule.get("status_filter") is not None:
                    merged["status_filter"] = rule["status_filter"]
                if rule.get("assignee"):
                    merged["assignee"] = rule["assignee"]
            # Team/roster questions are detected reliably by rule; don't let the LLM
            # reinterpret "what is my team doing" as a personal item listing.
            if rule.get("action") == "team":
                merged["action"] = "team"
            return merged
    return rule


# Conjunctions that separate two independent requests in one message
# ("summarize the sprint AND list the employees", "status, burndown").
_CLAUSE_SPLIT_RE = re.compile(
    r"\s*(?:,|;|&|\band\s+also\b|\band\b|\bthen\b|\balso\b|\bplus\b|\bas\s+well\s+as\b)\s*",
    re.IGNORECASE,
)
# Only READ-ONLY query actions are run as a compound. Mutations (create/start/complete/
# add/move/set_status) are never split — clause-splitting is heuristic and could reorder
# or misattribute a destructive change, so those always go through the single planner.
_COMPOUND_SAFE = frozenset(
    {"status", "burndown", "list_items", "list_sprints", "team", "projects"}
)


def _split_clauses(text: str) -> list[str]:
    return [c for c in (p.strip(" ?.!\t") for p in _CLAUSE_SPLIT_RE.split(text or "")) if c]


def plan_sprint_actions(
    user_text: str, recent_text: str = "", scope: str | None = None
) -> list[dict[str, Any]]:
    """
    Plan one OR MORE sprint actions for a single message.

    Most messages are one action (returns ``[plan]`` from :func:`plan_sprint_action`).
    When the user clearly asks for several read-only things at once
    ("summarize the sprint and list the employees"), we split on conjunctions and return
    a plan per distinct, compound-safe action so the caller can answer every part.
    """
    primary = plan_sprint_action(user_text, recent_text, scope=scope)
    clauses = _split_clauses(user_text)
    if len(clauses) < 2:
        return [primary]

    sub: list[dict[str, Any]] = []
    seen: set[str] = set()
    for clause in clauses:
        p = _rule_plan(clause)
        action = p.get("action")
        if not action or action == "help" or action in seen:
            continue
        seen.add(action)
        sub.append(p)

    # Need ≥2 distinct actions, and every one must be safe to run as a compound.
    if len(sub) < 2 or not all(p["action"] in _COMPOUND_SAFE for p in sub):
        return [primary]
    return sub


# --------------------------------------------------------------------------- #
# resolution helpers
# --------------------------------------------------------------------------- #
def _visible_projects(user):
    from sprints import services
    from tasks.models import Project

    return list(Project.objects.filter(pk__in=services.visible_project_ids(user)))


def _resolve_project(user, name: str | None):
    """Return (project, error_text). Falls back to the sole visible project."""
    projects = _visible_projects(user)
    if not projects:
        return None, "You're not part of any project yet. Ask an admin to add you to one."
    if name:
        nl = name.strip().lower()
        exact = [p for p in projects if p.name.lower() == nl]
        if exact:
            return exact[0], None
        partial = [p for p in projects if nl in p.name.lower()]
        if len(partial) == 1:
            return partial[0], None
        if len(partial) > 1:
            names = ", ".join(p.name for p in partial)
            return None, f"Which project did you mean: {names}?"
        return None, f"I couldn't find a project named “{name}”."
    if len(projects) == 1:
        return projects[0], None
    names = ", ".join(p.name for p in projects[:8])
    return None, f"Which project? You have: {names}."


def _resolve_sprint(user, name: str | None, project=None):
    """Return (sprint, error_text). Defaults to the active sprint when unnamed."""
    from sprints import services
    from sprints.models import Sprint

    qs = Sprint.objects.filter(project_id__in=services.visible_project_ids(user))
    if project is not None:
        qs = qs.filter(project=project)
    if name:
        nl = name.strip().lower()
        exact = list(qs.filter(name__iexact=nl)[:2])
        if len(exact) == 1:
            return exact[0], None
        partial = list(qs.filter(name__icontains=nl)[:5])
        if len(partial) == 1:
            return partial[0], None
        if len(partial) > 1:
            return None, "Several sprints match that name; please be more specific."
        return None, f"I couldn't find a sprint named “{name}”."
    active = list(qs.filter(status=Sprint.Status.ACTIVE).order_by("-started_at", "-id")[:2])
    if len(active) == 1:
        return active[0], None
    if len(active) > 1:
        names = ", ".join(s.name for s in active)
        return None, f"You have multiple active sprints ({names}). Which one?"
    recent = list(qs.order_by("-start_date", "-id")[:1])
    if recent:
        return recent[0], None
    return None, "There are no sprints yet. Try: *“create a sprint called Sprint 1”*."


def _resolve_task(user, title: str | None, project=None):
    from sprints import services
    from tasks.models import Task

    if not title:
        return None, "Which work item? Mention its title, e.g. *“mark 'Login page' as done”*."
    qs = Task.objects.filter(project_id__in=services.visible_project_ids(user))
    if project is not None:
        qs = qs.filter(project=project)
    tl = title.strip().lower()
    exact = list(qs.filter(title__iexact=tl)[:2])
    if len(exact) == 1:
        return exact[0], None
    partial = list(qs.filter(title__icontains=tl)[:5])
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        return None, f"Several items match “{title}”; please be more specific."
    return None, f"I couldn't find a work item titled “{title}”."


def _sprint_brief(sprint) -> dict[str, Any]:
    return {
        "id": sprint.id,
        "name": sprint.name,
        "status": sprint.status,
        "project": sprint.project.name if sprint.project_id else None,
        "project_id": sprint.project_id,
    }


# --------------------------------------------------------------------------- #
# executors  (each returns (text, result_json_base))
# --------------------------------------------------------------------------- #
def _err(text: str) -> tuple[str, dict[str, Any]]:
    return text, {"kind": "sprint_error", "message": text}


def _exec_create_sprint(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services
    from sprints.models import Sprint

    project, err = _resolve_project(user, plan.get("project"))
    if err:
        return _err(err)
    if not services.can_manage_project(user, project):
        return _err(f"Only the lead, manager, or an admin can create sprints in **{project.name}**.")
    name = (plan.get("sprint") or "").strip() or "New sprint"
    sprint = Sprint.objects.create(
        project=project,
        name=name,
        goal=(plan.get("goal") or "").strip(),
        start_date=plan.get("start_date") or None,
        end_date=plan.get("end_date") or None,
        created_by=user,
    )
    text = f"Created sprint **{sprint.name}** in **{project.name}**. Add work items, then say *“start the sprint”* when you're ready."
    return text, {"kind": "sprint_created", "sprint": _sprint_brief(sprint), "last_sprint": sprint.id}


def _exec_start_sprint(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services

    project, _ = _resolve_project(user, plan.get("project")) if plan.get("project") else (None, None)
    sprint, err = _resolve_sprint(user, plan.get("sprint"), project)
    if err:
        return _err(err)
    if not services.can_manage_project(user, sprint.project_id):
        return _err(f"Only the lead, manager, or an admin can start **{sprint.name}**.")
    services.start_sprint(sprint, by=user)
    text = f"**{sprint.name}** is now active with **{round(float(sprint.committed_points or 0), 1)}** committed points. Good luck!"
    return text, {"kind": "sprint_started", "sprint": _sprint_brief(sprint), "last_sprint": sprint.id}


def _exec_complete_sprint(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services

    project, _ = _resolve_project(user, plan.get("project")) if plan.get("project") else (None, None)
    sprint, err = _resolve_sprint(user, plan.get("sprint"), project)
    if err:
        return _err(err)
    if not services.can_manage_project(user, sprint.project_id):
        return _err(f"Only the lead, manager, or an admin can complete **{sprint.name}**.")
    move = plan.get("move_to")
    target = None
    if move == "backlog":
        target = "backlog"
    elif move:
        target, terr = _resolve_sprint(user, move)
        if terr:
            target = None
    services.complete_sprint(sprint, move_incomplete_to=target, by=user)
    suffix = ""
    if target == "backlog":
        suffix = " Unfinished items were moved to the backlog."
    elif target is not None:
        suffix = f" Unfinished items were moved to **{target.name}**."
    text = f"Completed **{sprint.name}**.{suffix}"
    return text, {"kind": "sprint_completed", "sprint": _sprint_brief(sprint), "last_sprint": sprint.id}


def _exec_add_item(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services
    from tasks.models import Task

    title = (plan.get("title") or "").strip()
    if not title:
        return _err("What should I call the work item? e.g. *“add a task 'Set up CI' to the sprint”*.")

    to_backlog = plan.get("move_to") == "backlog"
    project = None
    sprint = None
    if not to_backlog:
        project_hint = plan.get("project")
        proj_for_sprint = None
        if project_hint:
            proj_for_sprint, perr = _resolve_project(user, project_hint)
            if perr:
                return _err(perr)
        sprint, serr = _resolve_sprint(user, plan.get("sprint"), proj_for_sprint)
        if serr:
            return _err(serr)
        project = sprint.project
    else:
        project, perr = _resolve_project(user, plan.get("project"))
        if perr:
            return _err(perr)

    if not services.can_manage_project(user, project):
        return _err(f"Only the lead, manager, or an admin can add work items in **{project.name}**.")

    item_type = plan.get("item_type") if plan.get("item_type") in ("task", "story", "bug", "chore", "spike") else "task"
    pts = plan.get("story_points")
    task = Task.objects.create(
        title=title,
        project=project,
        sprint=sprint,
        item_type=item_type,
        story_points=float(pts) if isinstance(pts, (int, float)) else None,
        created_by=user,
        status="todo",
    )
    where = "the backlog" if to_backlog else f"**{sprint.name}**"
    text = f"Added {item_type} **{task.title}** to {where} in **{project.name}**."
    return text, {
        "kind": "work_item_added",
        "item": {"id": task.id, "title": task.title, "item_type": item_type},
        "sprint": _sprint_brief(sprint) if sprint else None,
        "last_task": task.id,
        "last_sprint": sprint.id if sprint else None,
    }


def _exec_move_item(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services

    task, err = _resolve_task(user, plan.get("title"))
    if err:
        return _err(err)
    if not services.can_manage_project(user, task.project_id):
        return _err("Only the lead, manager, or an admin can move work items between the sprint and backlog.")
    move = plan.get("move_to")
    if move == "backlog":
        task.sprint = None
        task.save(update_fields=["sprint"])
        text = f"Moved **{task.title}** to the backlog."
        return text, {"kind": "work_item_moved", "item": {"id": task.id, "title": task.title}, "last_task": task.id}
    target, terr = _resolve_sprint(user, move if isinstance(move, str) else None, task.project)
    if terr:
        return _err(terr)
    task.sprint = target
    task.save(update_fields=["sprint"])
    text = f"Moved **{task.title}** into **{target.name}**."
    return text, {
        "kind": "work_item_moved",
        "item": {"id": task.id, "title": task.title},
        "sprint": _sprint_brief(target),
        "last_task": task.id,
        "last_sprint": target.id,
    }


def _exec_set_status(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services

    task, err = _resolve_task(user, plan.get("title"))
    if err:
        return _err(err)
    status = _normalize_status(plan.get("status"))
    if not status:
        return _err("What status should it be — **To Do**, **In Progress**, or **Done**?")
    is_manager = bool(task.project_id and services.can_manage_project(user, task.project_id))
    if not (is_manager or task.user_id == user.pk):
        return _err(f"You can only change the status of items assigned to you. **{task.title}** isn't yours.")
    services.apply_status_change(task, status, changed_by=user)
    label = {"todo": "To Do", "inProgress": "In Progress", "done": "Done"}[status]
    text = f"Moved **{task.title}** to **{label}**."
    return text, {
        "kind": "work_item_status",
        "item": {"id": task.id, "title": task.title, "status": status},
        "last_task": task.id,
        "last_sprint": task.sprint_id,
    }


def _exec_status(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import metrics

    project, _ = _resolve_project(user, plan.get("project")) if plan.get("project") else (None, None)
    sprint, err = _resolve_sprint(user, plan.get("sprint"), project)
    if err:
        return _err(err)
    summary = metrics.sprint_summary(sprint)
    effort = None
    try:
        effort = metrics.sprint_effort(sprint)
    except Exception:  # pragma: no cover
        logger.exception("sprint_effort failed in assistant status")
    lines = [
        f"**{sprint.name}** ({sprint.status}) — {summary['done_count']}/{summary['item_count']} items done ({summary['completion_pct']}%).",
        f"Points: {summary['done_points']}/{summary['total_points']} completed.",
    ]
    if effort and effort.get("focus_hours"):
        lines.append(f"Team focus time logged: **{effort['focus_hours']}h** (of {effort['office_hours']}h tracked).")
    text = "\n".join(lines)
    return text, {
        "kind": "sprint_status",
        "sprint": _sprint_brief(sprint),
        "summary": summary,
        "effort": effort,
        "last_sprint": sprint.id,
    }


def _exec_burndown(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import metrics

    project, _ = _resolve_project(user, plan.get("project")) if plan.get("project") else (None, None)
    sprint, err = _resolve_sprint(user, plan.get("sprint"), project)
    if err:
        return _err(err)
    bd = metrics.burndown(sprint)
    actual = [a for a in bd.get("actual", []) if a is not None]
    remaining = actual[-1] if actual else bd.get("committed_points", 0)
    text = (
        f"**{sprint.name}** burndown — committed **{bd.get('committed_points', 0)}** points, "
        f"**{remaining}** remaining over {len(bd.get('days', []))} days. See the chart for the full trend."
    )
    return text, {"kind": "sprint_burndown", "sprint": _sprint_brief(sprint), "burndown": bd, "last_sprint": sprint.id}


_STATUS_LABEL = {"todo": "To Do", "inProgress": "In Progress", "done": "Done"}


def _exec_list_items(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services
    from tasks.models import Task

    project, _ = _resolve_project(user, plan.get("project")) if plan.get("project") else (None, None)
    sprint, err = _resolve_sprint(user, plan.get("sprint"), project)
    if err:
        return _err(err)
    if not services.can_view_project(user, sprint.project_id):
        return _err(f"You don't have access to **{sprint.name}**.")

    items = Task.objects.filter(sprint=sprint).select_related("user")

    sf = (plan.get("status_filter") or "").strip()
    if sf == "pending":
        items = items.filter(status__in=["todo", "inProgress"])
    elif sf in ("todo", "inProgress", "done"):
        items = items.filter(status=sf)

    # Scope: "me" (UI scope or "assigned to me") restricts to the current user.
    scope = plan.get("_scope")
    mine = plan.get("assignee") == "me" or scope == "me"
    if mine:
        items = items.filter(user_id=user.pk)

    items = list(items.order_by("status", "rank", "-id")[:50])

    who = "assigned to you " if mine else ""
    filt = {
        "pending": "pending ",
        "todo": "to-do ",
        "inProgress": "in-progress ",
        "done": "completed ",
    }.get(sf, "")
    if not items:
        text = f"There are no {filt}items {who}in **{sprint.name}**."
        return text, {"kind": "sprint_items", "sprint": _sprint_brief(sprint), "items": [], "last_sprint": sprint.id}

    rows = [
        {
            "id": i.id,
            "title": i.title,
            "status": i.status,
            "item_type": i.item_type,
            "story_points": i.story_points,
            "assignee": i.user.username if i.user_id else None,
        }
        for i in items
    ]
    label = f"{filt}items".strip()
    label = label[0].upper() + label[1:]
    header = f"{label} {who}in **{sprint.name}** ({len(rows)}):".replace("  ", " ")
    lines = [
        f"- {r['title']} — *{_STATUS_LABEL.get(r['status'], r['status'])}*"
        + (f" · @{r['assignee']}" if r["assignee"] and not mine else "")
        for r in rows
    ]
    text = header + "\n" + "\n".join(lines)
    return text, {
        "kind": "sprint_items",
        "sprint": _sprint_brief(sprint),
        "items": rows,
        "filter": sf or "all",
        "mine": mine,
        "last_sprint": sprint.id,
    }


def _team_projects(user, plan, role):
    """Resolve which project(s) a team question is about. Returns (projects, error)."""
    from sprints import services
    from tasks.models import Project

    if plan.get("project"):
        project, err = _resolve_project(user, plan.get("project"))
        return ([project] if project else []), err
    ids = services.manageable_project_ids(user) if role in ("manager", "admin") else services.visible_project_ids(user)
    projects = list(Project.objects.filter(pk__in=ids).order_by("name"))
    return projects, None


def _project_roster(project):
    """Ordered, de-duplicated roster for a project: lead, manager, then members."""
    from tasks.models import ProjectMember

    roster = []
    seen = set()

    def add(u, role_label):
        if u and u.pk not in seen:
            seen.add(u.pk)
            roster.append((u, role_label))

    add(getattr(project, "lead", None), "Lead")
    add(getattr(project, "manager", None), "Manager")
    for pm in ProjectMember.objects.filter(project=project).select_related("user"):
        add(pm.user, "Member")
    return roster


def _exec_team(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services
    from sprints.models import Sprint
    from tasks.models import Task

    role = services.assistant_role(user)
    projects, err = _team_projects(user, plan, role)
    if err:
        return _err(err)
    if not projects:
        return _err("You're not part of any project team yet. Ask an admin to add you to one.")
    if len(projects) > 1 and not plan.get("project"):
        names = ", ".join(p.name for p in projects[:8])
        return _err(f"Which team/project did you mean? You have: {names}.")

    project = projects[0]
    roster = _project_roster(project)
    active = Sprint.objects.filter(project=project, status=Sprint.Status.ACTIVE).order_by("-started_at", "-id").first()

    # Employees see who's on the team but not everyone's task breakdown (manager view).
    if role == "employee":
        people = ", ".join(f"{u.username} ({lbl})" for u, lbl in roster) or "just you"
        text = (
            f"Your team on **{project.name}**: {people}.\n\n"
            "Detailed team task tracking is available to your lead or manager. "
            "Ask me about *your* tasks (e.g. *“what are my pending tasks?”*) and I'll help."
        )
        return text, {
            "kind": "team_roster",
            "project": project.name,
            "project_id": project.pk,
            "members": [{"username": u.username, "role": lbl} for u, lbl in roster],
        }

    # Manager / admin: roster + what each member is currently working on.
    item_qs = Task.objects.filter(project=project).exclude(status="done")
    if active:
        item_qs = item_qs.filter(sprint=active)
    items = list(item_qs.select_related("user"))
    by_user: dict[int, list] = {}
    for it in items:
        by_user.setdefault(it.user_id, []).append(it)

    members_out = []
    lines = []
    for u, lbl in roster:
        mine = by_user.get(u.pk, [])
        in_prog = [t for t in mine if t.status == "inProgress"]
        todo = [t for t in mine if t.status == "todo"]
        doing = in_prog[0].title if in_prog else None
        members_out.append(
            {
                "username": u.username,
                "role": lbl,
                "doing": doing,
                "in_progress": [t.title for t in in_prog],
                "todo_count": len(todo),
                "open_count": len(mine),
            }
        )
        if doing:
            tail = f"working on **{doing}**" + (f" · {len(todo)} to-do" if todo else "")
        elif mine:
            tail = f"{len(todo)} to-do" + (" item" if len(todo) == 1 else " items")
        else:
            tail = "no open items"
        lines.append(f"- {u.username} ({lbl}) — {tail}")

    where = f" (active sprint **{active.name}**)" if active else ""
    header = f"**{project.name}** team — {len(roster)} {'person' if len(roster) == 1 else 'people'}{where}:"
    text = header + "\n" + "\n".join(lines)
    return text, {
        "kind": "team_overview",
        "project": project.name,
        "project_id": project.pk,
        "sprint": _sprint_brief(active) if active else None,
        "members": members_out,
    }


def _exec_projects(user, plan) -> tuple[str, dict[str, Any]]:
    """Answer "what/which project(s) am I working on" with the user's projects + active sprint."""
    from sprints import services
    from sprints.models import Sprint
    from tasks.models import Project

    # A specific project was named (or pinned from the UI) — answer about just that one.
    if plan.get("project"):
        project, err = _resolve_project(user, plan.get("project"))
        if err:
            return _err(err)
        projects = [project]
    else:
        role = services.assistant_role(user)
        scope = plan.get("_scope")
        if scope in ("team", "project") and role in ("manager", "admin"):
            ids = services.manageable_project_ids(user)
        else:
            ids = services.visible_project_ids(user)
        projects = list(Project.objects.filter(pk__in=ids).order_by("name"))

    if not projects:
        return _err("You're not part of any project yet. Ask an admin to add you to one.")

    actives: dict[int, Any] = {}
    for s in (
        Sprint.objects.filter(
            project_id__in=[p.pk for p in projects], status=Sprint.Status.ACTIVE
        ).order_by("-started_at", "-id")
    ):
        actives.setdefault(s.project_id, s)

    rows = []
    for p in projects:
        s = actives.get(p.pk)
        rows.append(
            {
                "id": p.pk,
                "name": p.name,
                "active_sprint": s.name if s else None,
                "sprint_id": s.id if s else None,
            }
        )

    if len(rows) == 1:
        r = rows[0]
        tail = (
            f" The active sprint is **{r['active_sprint']}**."
            if r["active_sprint"]
            else " There's no active sprint right now."
        )
        text = f"You're working on **{r['name']}**.{tail}"
    else:
        lines = [
            f"- **{r['name']}**"
            + (f" — active sprint *{r['active_sprint']}*" if r["active_sprint"] else " — no active sprint")
            for r in rows
        ]
        text = f"You're working on **{len(rows)}** projects:\n" + "\n".join(lines)

    return text, {"kind": "project_list", "projects": rows, "last_sprint": rows[0].get("sprint_id")}


def _exec_list_sprints(user, plan) -> tuple[str, dict[str, Any]]:
    from sprints import services
    from sprints.models import Sprint

    project, err = (None, None)
    if plan.get("project"):
        project, err = _resolve_project(user, plan.get("project"))
        if err:
            return _err(err)
    qs = Sprint.objects.filter(project_id__in=services.visible_project_ids(user))
    if project is not None:
        qs = qs.filter(project=project)
    sprints = list(qs.select_related("project").order_by("-start_date", "-id")[:15])
    if not sprints:
        return "There are no sprints yet. Try *“create a sprint called Sprint 1”*.", {
            "kind": "sprint_list",
            "sprints": [],
        }
    rows = [
        {
            "id": s.id,
            "name": s.name,
            "status": s.status,
            "project": s.project.name if s.project_id else None,
            "project_id": s.project_id,
        }
        for s in sprints
    ]
    lines = [f"- **{r['name']}** ({r['status']}) — {r['project']}" for r in rows]
    text = "Sprints:\n" + "\n".join(lines)
    return text, {"kind": "sprint_list", "sprints": rows}


def _exec_help(user, plan) -> tuple[str, dict[str, Any]]:  # noqa: ARG001
    text = (
        "I can manage your sprints. Try:\n"
        "- *“Create a sprint called Sprint 5 in Website”*\n"
        "- *“Add a task 'Fix login bug' to the sprint”*\n"
        "- *“Start the sprint”* / *“Complete the sprint”*\n"
        "- *“Move 'Fix login bug' to the backlog”*\n"
        "- *“Mark 'Fix login bug' as done”*\n"
        "- *“What's the sprint status?”* or *“show the burndown”*"
    )
    return text, {"kind": "sprint_help"}


_DISPATCH = {
    "create_sprint": _exec_create_sprint,
    "start_sprint": _exec_start_sprint,
    "complete_sprint": _exec_complete_sprint,
    "add_item": _exec_add_item,
    "move_item": _exec_move_item,
    "set_status": _exec_set_status,
    "status": _exec_status,
    "burndown": _exec_burndown,
    "list_items": _exec_list_items,
    "list_sprints": _exec_list_sprints,
    "team": _exec_team,
    "projects": _exec_projects,
    "help": _exec_help,
}


def handle_sprint(
    user,
    user_text: str,
    recent_text: str = "",
    scope: str | None = None,
    project_id: int | None = None,
) -> tuple[str, dict[str, Any]]:
    """
    Plan and execute one sprint action. Returns (assistant_text, result_json_base).

    ``scope`` ("me" / "team" / "project") comes from the assistant UI and biases
    work-item queries (e.g. "me" restricts listings to the current user).
    ``project_id`` is the project the user chose to chat about; when set (and the
    user may use it) it scopes resolution to that project. Neither relaxes
    permissions — those are always enforced via ``sprints.services``.
    Never raises: on any unexpected error it returns a friendly help message.
    """
    try:
        plans = plan_sprint_actions(user_text, recent_text, scope=scope)

        chosen_name: str | None = None
        if project_id:
            chosen_name = _chosen_project_name(user, project_id, scope)

        def _prepare(plan: dict[str, Any]) -> dict[str, Any]:
            if scope:
                plan["_scope"] = scope
            # Pin the chosen project (unless the message itself named one) so the
            # executors resolve sprints/items within that project.
            if chosen_name and not plan.get("project"):
                plan["project"] = chosen_name
            return plan

        # Single action — the common path (unchanged behavior).
        if len(plans) == 1:
            plan = _prepare(plans[0])
            action = plan.get("action") if plan.get("action") in ACTIONS else "help"
            text, base = _DISPATCH[action](user, plan)
            base.setdefault("action", action)
            if scope:
                base.setdefault("scope", scope)
            return text, base

        # Compound: run each read-only part and combine into one multi result.
        parts: list[dict[str, Any]] = []
        texts: list[str] = []
        for plan in plans:
            _prepare(plan)
            action = plan.get("action") if plan.get("action") in ACTIONS else "help"
            text_i, base_i = _DISPATCH[action](user, plan)
            base_i.setdefault("action", action)
            base_i["text"] = text_i
            parts.append(base_i)
            if text_i:
                texts.append(text_i)

        combined: dict[str, Any] = {
            "kind": "sprint_multi",
            "parts": parts,
            "actions": [b.get("action") for b in parts],
        }
        if scope:
            combined["scope"] = scope
        for b in parts:
            if b.get("last_sprint"):
                combined["last_sprint"] = b["last_sprint"]
            if b.get("last_task"):
                combined["last_task"] = b["last_task"]
        return "\n\n".join(texts), combined
    except Exception:  # pragma: no cover
        logger.exception("handle_sprint failed")
        return _exec_help(user, {})


def _chosen_project_name(user, project_id: int, scope: str | None) -> str | None:
    """
    Resolve a UI-selected project id to its name, enforcing access:
    team/project perspectives require the user to manage it; otherwise it must at
    least be visible. Returns None when the selection isn't allowed.
    """
    from sprints import services
    from tasks.models import Project

    if scope in ("team", "project"):
        allowed = services.manageable_project_ids(user)
    else:
        allowed = services.visible_project_ids(user)
    if project_id not in allowed:
        return None
    return Project.objects.filter(pk=project_id).values_list("name", flat=True).first()

