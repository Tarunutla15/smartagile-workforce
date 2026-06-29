"""Compile the LangGraph workflow for one Django user (nodes bound with functools.partial)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .nodes import (
    classify_node,
    email_report_node,
    load_memory_node,
    load_productivity_node,
    load_tasks_node,
    route_after_classify,
    tool_tasks_node,
    synthesize_general_node,
    synthesize_productivity_node,
    synthesize_tasks_node,
)
from .state import AgentState


def build_compiled_assistant_graph(user: Any):
    """
    Per-request compiled graph (user bound in partials so state stays JSON-serializable).
    """
    graph = StateGraph(AgentState)

    graph.add_node("classify", lambda s: classify_node(user, s))
    graph.add_node("load_memory", lambda s: load_memory_node(user, s))
    graph.add_node("load_productivity", lambda s: load_productivity_node(user, s))
    graph.add_node("tool_tasks", lambda s: tool_tasks_node(user, s))
    graph.add_node("load_tasks", lambda s: load_tasks_node(user, s))
    graph.add_node("synthesize_productivity", lambda s: synthesize_productivity_node(user, s))
    graph.add_node("synthesize_tasks", lambda s: synthesize_tasks_node(user, s))
    graph.add_node("synthesize_general", lambda s: synthesize_general_node(user, s))
    graph.add_node("email_report", lambda s: email_report_node(user, s))

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "report": "email_report",
            "productivity": "load_memory",
            "tasks": "load_memory",
            "general": "load_memory",
        },
    )
    graph.add_conditional_edges(
        "load_memory",
        route_after_classify,
        {
            "productivity": "load_productivity",
            "tasks": "tool_tasks",
            "general": "synthesize_general",
        },
    )
    graph.add_edge("email_report", END)
    graph.add_edge("load_productivity", "synthesize_productivity")
    graph.add_edge("synthesize_productivity", END)
    # tool_tasks either returns an assistant_text (tool executed) or continues to load_tasks.
    graph.add_conditional_edges(
        "tool_tasks",
        lambda s: "end" if (s or {}).get("assistant_text") else "continue",
        {
            "end": END,
            "continue": "load_tasks",
        },
    )
    graph.add_edge("load_tasks", "synthesize_tasks")
    graph.add_edge("synthesize_tasks", END)
    graph.add_edge("synthesize_general", END)

    return graph.compile()
