"""CI gate for the assistant eval harness (Tier 2D).

Runs the deterministic golden suites and fails if any case regresses. These need no LLM
or network, so they're safe and fast in CI. Use ``python manage.py eval_assistant`` for a
human-readable report.
"""

from django.test import SimpleTestCase

from assistant.evals.runner import (
    run_grounding,
    run_routing,
    run_sprint_actions,
    summarize,
)


class AssistantEvalTests(SimpleTestCase):
    def _assert_all(self, results):
        s = summarize(results)
        if s["failed"]:
            lines = [f"[{r['suite']}] {r['name']!r}: {r['detail']}" for r in s["failures"]]
            self.fail(f"{s['failed']} eval case(s) failed:\n" + "\n".join(lines))

    def test_routing_cases(self):
        self._assert_all(run_routing())

    def test_sprint_action_cases(self):
        self._assert_all(run_sprint_actions())

    def test_grounding_no_hallucinated_numbers(self):
        self._assert_all(run_grounding())


class SprintCompoundPlanTests(SimpleTestCase):
    """Compound (multi-part) sprint questions must plan every read-only part, while
    mutation requests are never split (clause-splitting is heuristic)."""

    def test_two_readonly_parts_are_planned(self):
        from assistant.graph.sprint_agent import plan_sprint_actions

        actions = [p["action"] for p in plan_sprint_actions(
            "summarize the sprint and list the employees?"
        )]
        self.assertEqual(actions, ["status", "team"])

    def test_single_request_stays_single(self):
        from assistant.graph.sprint_agent import plan_sprint_actions

        self.assertEqual(
            [p["action"] for p in plan_sprint_actions("summarize the sprint")],
            ["status"],
        )

    def test_complete_and_move_is_not_split(self):
        from assistant.graph.sprint_agent import plan_sprint_actions

        # "complete the sprint and move unfinished to backlog" is one complete_sprint.
        self.assertEqual(
            [p["action"] for p in plan_sprint_actions(
                "complete the sprint and move unfinished to backlog"
            )],
            ["complete_sprint"],
        )

    def test_mutation_compound_falls_back_to_single(self):
        from assistant.graph.sprint_agent import plan_sprint_actions

        # A create+add compound is not split (mutations are never auto-sequenced).
        plans = plan_sprint_actions("start sprint Alpha and add task X")
        self.assertEqual(len(plans), 1)
