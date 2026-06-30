"""Compile the LangGraph workflow for one Django user (nodes bound with functools.partial)."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from .nodes import (
    classify_node,
    digest_node,
    email_report_node,
    load_knowledge_node,
    load_memory_node,
    load_productivity_node,
    load_task_insights_node,
    load_tasks_node,
    route_after_classify,
    sprint_node,
    tool_tasks_node,
    synthesize_general_node,
    synthesize_knowledge_node,
    synthesize_productivity_node,
    synthesize_task_insights_node,
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
    graph.add_node("load_task_insights", lambda s: load_task_insights_node(user, s))
    graph.add_node("load_knowledge", lambda s: load_knowledge_node(user, s))
    graph.add_node("synthesize_knowledge", lambda s: synthesize_knowledge_node(user, s))
    graph.add_node("synthesize_productivity", lambda s: synthesize_productivity_node(user, s))
    graph.add_node("synthesize_tasks", lambda s: synthesize_tasks_node(user, s))
    graph.add_node("synthesize_task_insights", lambda s: synthesize_task_insights_node(user, s))
    graph.add_node("synthesize_general", lambda s: synthesize_general_node(user, s))
    graph.add_node("email_report", lambda s: email_report_node(user, s))
    graph.add_node("digest", lambda s: digest_node(user, s))
    graph.add_node("sprint", lambda s: sprint_node(user, s))

    graph.set_entry_point("classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {
            "report": "email_report",
            "digest": "digest",
            "productivity": "load_memory",
            "tasks": "load_memory",
            "task_insights": "load_memory",
            "knowledge": "load_memory",
            "sprint": "load_memory",
            "general": "load_memory",
        },
    )
    graph.add_conditional_edges(
        "load_memory",
        route_after_classify,
        {
            "productivity": "load_productivity",
            "tasks": "tool_tasks",
            "task_insights": "load_task_insights",
            "knowledge": "load_knowledge",
            "sprint": "sprint",
            "general": "synthesize_general",
        },
    )
    graph.add_edge("email_report", END)
    graph.add_edge("digest", END)
    graph.add_edge("sprint", END)
    graph.add_edge("load_productivity", "synthesize_productivity")
    graph.add_edge("synthesize_productivity", END)
    graph.add_edge("load_task_insights", "synthesize_task_insights")
    graph.add_edge("synthesize_task_insights", END)
    graph.add_edge("load_knowledge", "synthesize_knowledge")
    graph.add_edge("synthesize_knowledge", END)
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
