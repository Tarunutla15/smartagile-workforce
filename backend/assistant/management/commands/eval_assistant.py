"""Run the assistant eval harness and print a report.

    python manage.py eval_assistant

Exits non-zero if any case fails, so it can gate CI. Deterministic — no LLM/network.
"""

from django.core.management.base import BaseCommand

from assistant.evals.runner import run_all, summarize


class Command(BaseCommand):
    help = "Run deterministic assistant evals (routing, sprint actions, grounding)."

    def handle(self, *args, **options):
        results = run_all()
        summary = summarize(results)

        # Group pass/fail counts per suite for a compact report.
        suites: dict[str, list] = {}
        for r in results:
            suites.setdefault(r["suite"], []).append(r)
        for suite, rows in suites.items():
            passed = sum(1 for r in rows if r["ok"])
            self.stdout.write(f"{suite:10s} {passed}/{len(rows)} passed")

        if summary["failed"]:
            self.stdout.write(self.style.ERROR(f"\n{summary['failed']} failure(s):"))
            for r in summary["failures"]:
                self.stdout.write(
                    self.style.ERROR(f"  [{r['suite']}] {r['name']!r}: {r['detail']}")
                )
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(f"\nAll {summary['passed']} assistant eval cases passed.")
        )
