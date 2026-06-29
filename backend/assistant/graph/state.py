"""Graph state: plain dict / TypedDict for LangGraph (no ORM objects)."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph state (merged per node return)."""

    user_text: str
    session_id: int | None
    intent: str
    route: dict[str, Any]
    productivity_ctx: dict[str, Any]
    task_insights_ctx: dict[str, Any]
    tasks_items: list[dict[str, Any]]
    tool_action: dict[str, Any]
    recent_messages: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    assistant_text: str
    result_json: dict[str, Any]
    error: str
