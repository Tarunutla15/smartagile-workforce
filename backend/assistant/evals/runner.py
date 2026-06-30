"""Deterministic eval runner.

Three suites, none of which need an LLM or network (so they're free and CI-safe):

1. routing  — `classify_intent_rules` maps a message to the right intent.
2. sprint    — `_rule_plan` maps a sprint message to the right action.
3. grounding — the deterministic synthesis template prints only numbers that exist in its
               input context (the anti-hallucination contract every synth node promises).

Each `run_*` returns a list of result dicts: {suite, name, ok, detail}.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_DIR = Path(__file__).resolve().parent


def _load_jsonl(name: str) -> list[dict[str, Any]]:
    path = _DIR / name
    out: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run_routing() -> list[dict[str, Any]]:
    from assistant.graph.intent import classify_intent_rules

    results = []
    for case in _load_jsonl("routing_cases.jsonl"):
        msg = case["message"]
        expected = case["expect_intent"]
        actual = classify_intent_rules(msg)
        results.append(
            {
                "suite": "routing",
                "name": msg,
                "ok": actual == expected,
                "detail": f"expected {expected!r}, got {actual!r}",
            }
        )
    return results


def run_sprint_actions() -> list[dict[str, Any]]:
    from assistant.graph.sprint_agent import _rule_plan

    results = []
    for case in _load_jsonl("sprint_action_cases.jsonl"):
        msg = case["message"]
        expected = case["expect_action"]
        actual = (_rule_plan(msg) or {}).get("action")
        results.append(
            {
                "suite": "sprint",
                "name": msg,
                "ok": actual == expected,
                "detail": f"expected {expected!r}, got {actual!r}",
            }
        )
    return results


def _numbers_in(value: Any) -> set[str]:
    """All integer-looking tokens reachable in a nested structure (as strings)."""
    found: set[str] = set()

    def walk(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            found.add(str(int(v)))
        elif isinstance(v, str):
            found.update(re.findall(r"\d+", v))
        elif isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                walk(x)

    walk(value)
    return found


def run_grounding() -> list[dict[str, Any]]:
    """The template must surface the real totals and invent NO numbers not in the context."""
    from assistant.graph.task_insights import format_task_insights_markdown

    ctx = {
        "has_tasks": True,
        "totals": {"total": 5, "todo": 3, "in_progress": 1, "done": 1, "completion_pct": 20},
        "next_up": {
            "reason": "in_progress",
            "tasks": [{"title": "Login bug", "id": 7, "status": "inProgress", "age_days": 4}],
        },
        "aging_pending": [],
        "by_project": [],
    }
    text = format_task_insights_markdown(ctx)

    results = []
    # (a) the key totals must actually appear.
    must_have = ["5", "3", "1", "20"]
    missing = [n for n in must_have if n not in text]
    results.append(
        {
            "suite": "grounding",
            "name": "totals surfaced",
            "ok": not missing,
            "detail": f"missing numbers {missing}" if missing else "all totals present",
        }
    )
    # (b) no invented numbers: every integer printed must come from the context.
    allowed = _numbers_in(ctx)
    printed = set(re.findall(r"\d+", text))
    invented = sorted(printed - allowed)
    results.append(
        {
            "suite": "grounding",
            "name": "no invented numbers",
            "ok": not invented,
            "detail": f"invented {invented}" if invented else "no hallucinated numbers",
        }
    )
    return results


def run_all() -> list[dict[str, Any]]:
    return run_routing() + run_sprint_actions() + run_grounding()


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    failed = [r for r in results if not r["ok"]]
    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "failures": failed,
    }
