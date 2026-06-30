"""Full (re)index of agile content into KnowledgeChunk for doc-RAG (Tier 2B).

Usage:
    python manage.py reindex_knowledge

Safe to run repeatedly; rows whose text is unchanged are skipped (no re-embedding).
"""

from __future__ import annotations

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-index all work items, comments, and sprint goals into KnowledgeChunk."

    def handle(self, *args, **options):
        from assistant.knowledge import reindex_all

        counts = reindex_all()
        self.stdout.write(
            self.style.SUCCESS(
                "Knowledge index refreshed: "
                f"{counts['tasks']} tasks, {counts['comments']} comments, "
                f"{counts['sprints']} sprints "
                f"({counts['embedded']} (re)embedded)."
            )
        )
