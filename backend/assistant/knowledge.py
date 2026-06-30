"""
Document-RAG over agile content (Tier 2B).

We embed the text the team actually writes — work-item titles/descriptions, work-item
comments, and sprint goals — into ``smartagile.KnowledgeChunk`` rows. The assistant then
retrieves the most relevant chunks (cosine over the stored embedding, with a keyword
fallback when embeddings aren't configured) to ground answers in real project context.

Design notes
------------
* One chunk per source row, keyed by (``source_type``, ``source_id``); ``content_hash``
  lets re-indexing skip rows whose text is unchanged (and avoids re-embedding cost).
* Indexing is idempotent and safe to run repeatedly (full reindex or per-row).
* Retrieval is ALWAYS scoped to projects the asking user can see
  (``sprints.services.visible_project_ids``) — never leak another team's content.
* Scale: Python cosine over a per-project candidate set is fine to ~10k chunks. The
  upgrade path is pgvector (swap ``VectorField`` + ANN index into the model and replace
  the candidate scan below); the retrieval contract here stays the same.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from django.conf import settings

from .memory import _cosine, embed_text

logger = logging.getLogger(__name__)

MAX_TEXT_CHARS = 5000
MAX_EMBED_CHARS = 2000
CANDIDATE_LIMIT = 800
_WORD_RE = re.compile(r"[a-z0-9]{3,}")


def doc_rag_enabled() -> bool:
    return bool(getattr(settings, "ASSISTANT_DOC_RAG", True))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _delete_chunk(source_type: str, source_id: int) -> None:
    from smartagile.models import KnowledgeChunk

    KnowledgeChunk.objects.filter(source_type=source_type, source_id=source_id).delete()


def _upsert_chunk(
    *,
    project_id: int | None,
    source_type: str,
    source_id: int,
    task_id: int | None,
    sprint_id: int | None,
    title: str,
    text: str,
) -> bool:
    """Create/update the chunk for one source row. Returns True if it was (re)embedded."""
    from smartagile.models import KnowledgeChunk

    text = (text or "").strip()
    if not project_id or not text:
        # Nothing useful to index (e.g. a task with no project / empty body) — make sure
        # we don't leave a stale chunk behind.
        _delete_chunk(source_type, source_id)
        return False

    title = (title or "").strip()
    payload = f"{title}\n{text}".strip()
    content_hash = _hash(payload)

    existing = KnowledgeChunk.objects.filter(
        source_type=source_type, source_id=source_id
    ).first()
    if (
        existing is not None
        and existing.content_hash == content_hash
        and existing.project_id == project_id
    ):
        return False  # text unchanged — no rewrite / re-embed needed

    embedding = embed_text(payload[:MAX_EMBED_CHARS])
    KnowledgeChunk.objects.update_or_create(
        source_type=source_type,
        source_id=source_id,
        defaults={
            "project_id": project_id,
            "task_id": task_id,
            "sprint_id": sprint_id,
            "title": title[:300],
            "text": text[:MAX_TEXT_CHARS],
            "embedding": embedding,
            "content_hash": content_hash,
        },
    )
    return True


# --------------------------------------------------------------------------- #
# Per-source indexers (called from signals / Celery / management command).
# --------------------------------------------------------------------------- #
def index_task(task_id: int) -> bool:
    from tasks.models import Task

    t = (
        Task.objects.filter(pk=task_id)
        .only("id", "title", "description", "project_id", "sprint_id")
        .first()
    )
    if t is None:
        _delete_chunk("work_item", task_id)
        return False
    title = t.title or ""
    return _upsert_chunk(
        project_id=t.project_id,
        source_type="work_item",
        source_id=t.pk,
        task_id=t.pk,
        sprint_id=t.sprint_id,
        title=title,
        text=f"{title}\n{t.description or ''}",
    )


def index_comment(comment_id: int) -> bool:
    from sprints.models import WorkItemComment

    c = (
        WorkItemComment.objects.filter(pk=comment_id)
        .select_related("task")
        .first()
    )
    if c is None or c.task is None:
        _delete_chunk("comment", comment_id)
        return False
    task = c.task
    return _upsert_chunk(
        project_id=task.project_id,
        source_type="comment",
        source_id=c.pk,
        task_id=task.pk,
        sprint_id=task.sprint_id,
        title=f"Comment on {task.title}",
        text=c.body,
    )


def index_sprint(sprint_id: int) -> bool:
    from sprints.models import Sprint

    s = Sprint.objects.filter(pk=sprint_id).only("id", "name", "goal", "project_id").first()
    if s is None:
        _delete_chunk("sprint_goal", sprint_id)
        return False
    return _upsert_chunk(
        project_id=s.project_id,
        source_type="sprint_goal",
        source_id=s.pk,
        task_id=None,
        sprint_id=s.pk,
        title=f"Sprint goal: {s.name}",
        text=s.goal,
    )


def reindex_all() -> dict[str, int]:
    """Full (re)index of every source row. Safe to run repeatedly."""
    from sprints.models import Sprint, WorkItemComment
    from tasks.models import Task

    counts = {"tasks": 0, "comments": 0, "sprints": 0, "embedded": 0}
    for tid in Task.objects.values_list("id", flat=True).iterator():
        counts["tasks"] += 1
        if index_task(tid):
            counts["embedded"] += 1
    for cid in WorkItemComment.objects.values_list("id", flat=True).iterator():
        counts["comments"] += 1
        if index_comment(cid):
            counts["embedded"] += 1
    for sid in Sprint.objects.values_list("id", flat=True).iterator():
        counts["sprints"] += 1
        if index_sprint(sid):
            counts["embedded"] += 1
    return counts


# --------------------------------------------------------------------------- #
# Retrieval (used by the knowledge node).
# --------------------------------------------------------------------------- #
def _snippet(text: str, limit: int = 320) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _row(chunk, score: float) -> dict[str, Any]:
    return {
        "source_type": chunk.source_type,
        "title": chunk.title,
        "snippet": _snippet(chunk.text),
        "task_id": chunk.task_id,
        "sprint_id": chunk.sprint_id,
        "project_id": chunk.project_id,
        "score": round(float(score), 4),
    }


def retrieve_knowledge(user, query: str, limit: int = 6) -> list[dict[str, Any]]:
    """
    Top-``limit`` knowledge chunks relevant to ``query``, scoped to projects ``user`` can
    see. Cosine over embeddings when available; otherwise keyword overlap. Never raises.
    """
    if not doc_rag_enabled():
        return []
    q = (query or "").strip()
    if not q:
        return []

    from smartagile.models import KnowledgeChunk
    from sprints.services import visible_project_ids

    try:
        pids = visible_project_ids(user)
    except Exception:
        logger.exception("knowledge retrieve: project scoping failed")
        return []
    if not pids:
        return []

    limit = max(1, min(int(limit), 12))
    candidates = list(
        KnowledgeChunk.objects.filter(project_id__in=pids).only(
            "id",
            "source_type",
            "title",
            "text",
            "task_id",
            "sprint_id",
            "project_id",
            "embedding",
        )[:CANDIDATE_LIMIT]
    )
    if not candidates:
        return []

    qv = embed_text(q)
    scored: list[tuple[float, Any]] = []
    if qv is not None:
        for c in candidates:
            v = c.embedding
            if isinstance(v, list) and v:
                try:
                    sim = _cosine(qv, [float(x) for x in v])
                except (TypeError, ValueError):
                    continue
                if sim > 0:
                    scored.append((sim, c))
        if scored:
            scored.sort(key=lambda t: t[0], reverse=True)
            return [_row(c, s) for s, c in scored[:limit]]

    # Keyword fallback (no embeddings, or none of the chunks were embedded).
    qwords = set(_WORD_RE.findall(q.lower()))
    if not qwords:
        return []
    for c in candidates:
        words = set(_WORD_RE.findall(f"{c.title} {c.text}".lower()))
        overlap = len(qwords & words)
        if overlap:
            scored.append((float(overlap), c))
    scored.sort(key=lambda t: t[0], reverse=True)
    return [_row(c, s) for s, c in scored[:limit]]
