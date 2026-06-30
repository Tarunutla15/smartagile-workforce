"""
Incremental knowledge indexing (Tier 2B doc-RAG).

When a work item, comment, or sprint changes, enqueue a (debounced) Celery job to refresh
its KnowledgeChunk. We enqueue rather than embed inline so saves stay fast and embedding
cost/latency stays off the request path. ``register()`` is idempotent — connected from
``AssistantConfig.ready()``.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save

logger = logging.getLogger(__name__)

_CONNECTED = False


def _enqueue(kind: str, obj_id: int) -> None:
    if not getattr(settings, "ASSISTANT_DOC_RAG", True):
        return
    if not obj_id:
        return
    try:
        from smartagile.tasks import index_knowledge_task

        index_knowledge_task.delay(kind, obj_id)
    except Exception:
        # Broker down / eager misconfig — never break the originating save.
        logger.exception("knowledge index enqueue failed kind=%s id=%s", kind, obj_id)


def _on_task_save(sender, instance, **kwargs):
    _enqueue("task", instance.pk)


def _on_task_delete(sender, instance, **kwargs):
    _enqueue("task", instance.pk)


def _on_comment_save(sender, instance, **kwargs):
    _enqueue("comment", instance.pk)


def _on_comment_delete(sender, instance, **kwargs):
    _enqueue("comment", instance.pk)


def _on_sprint_save(sender, instance, **kwargs):
    _enqueue("sprint", instance.pk)


def _on_sprint_delete(sender, instance, **kwargs):
    _enqueue("sprint", instance.pk)


def register() -> None:
    global _CONNECTED
    if _CONNECTED:
        return

    from sprints.models import Sprint, WorkItemComment
    from tasks.models import Task

    post_save.connect(_on_task_save, sender=Task, dispatch_uid="kb_task_save")
    post_delete.connect(_on_task_delete, sender=Task, dispatch_uid="kb_task_delete")
    post_save.connect(_on_comment_save, sender=WorkItemComment, dispatch_uid="kb_comment_save")
    post_delete.connect(
        _on_comment_delete, sender=WorkItemComment, dispatch_uid="kb_comment_delete"
    )
    post_save.connect(_on_sprint_save, sender=Sprint, dispatch_uid="kb_sprint_save")
    post_delete.connect(_on_sprint_delete, sender=Sprint, dispatch_uid="kb_sprint_delete")

    _CONNECTED = True
