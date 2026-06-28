"""
Semantic memory: extraction + embedding + retrieval.

Design goals:
- Works with OpenAI-compatible embeddings (OpenAI by default).
- Degrades gracefully when embeddings are unavailable (stores text only).
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from smartagile.models import AssistantChatMessage, AssistantChatSession, UserMemory

logger = logging.getLogger(__name__)

MAX_MEMORY_CHARS = 800
MAX_QUERY_CHARS = 2000


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += float(x) * float(y)
        na += float(x) * float(x)
        nb += float(y) * float(y)
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _make_embedder() -> Any | None:
    """
    Return an embeddings client or None when not configured.

    We intentionally default to OpenAI embeddings even when chat uses Groq, because
    Groq's OpenAI-compatible endpoint is primarily for chat and may not support embeddings.
    """
    try:
        from langchain_openai import OpenAIEmbeddings
    except Exception:  # pragma: no cover
        return None

    mode = (getattr(settings, "EMBEDDINGS_PROVIDER", "auto") or "auto").strip().lower()

    # Explicit OpenAI
    if mode == "openai":
        key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
        if not key:
            return None
        kwargs: dict[str, Any] = {
            "model": getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            "api_key": key,
        }
        base = getattr(settings, "OPENAI_BASE_URL", None) or None
        if base:
            kwargs["base_url"] = base
        return OpenAIEmbeddings(**kwargs)

    # Explicit Groq (best-effort; may fail at runtime).
    if mode == "groq":
        key = (getattr(settings, "GROQ_API_KEY", "") or "").strip()
        if not key:
            return None
        m = getattr(settings, "GROQ_EMBEDDING_MODEL", "") or ""
        if not m:
            # If the user insists on Groq embeddings, they must provide a supported model name.
            return None
        return OpenAIEmbeddings(
            model=m,
            api_key=key,
            base_url=getattr(settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        )

    # auto: prefer OpenAI if key exists; else none (text-only memory).
    key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
    if not key:
        return None
    kwargs2: dict[str, Any] = {
        "model": getattr(settings, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        "api_key": key,
    }
    base2 = getattr(settings, "OPENAI_BASE_URL", None) or None
    if base2:
        kwargs2["base_url"] = base2
    return OpenAIEmbeddings(**kwargs2)


def embed_text(text: str) -> list[float] | None:
    t = (text or "").strip()
    if not t:
        return None
    t = t[:MAX_QUERY_CHARS]
    emb = _make_embedder()
    if not emb:
        return None
    try:
        v = emb.embed_query(t)
        return [float(x) for x in v] if v else None
    except Exception:
        logger.exception("embed_text failed; continuing without embeddings")
        return None


def recent_session_messages(user, session_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    """
    Return last N messages (role + content) from this session, oldest-first, for prompt injection.
    Default and cap come from settings (roughly the last 2–6+ back-and-forth turns).
    """
    from django.conf import settings

    if limit is None:
        limit = int(getattr(settings, "ASSISTANT_SESSION_MESSAGE_LIMIT", 24))
    cap = int(getattr(settings, "ASSISTANT_SESSION_MESSAGE_MAX", 48))
    limit = max(1, min(int(limit), cap))
    try:
        s = AssistantChatSession.objects.filter(pk=session_id, user=user).only("id").first()
        if not s:
            return []
        qs = (
            AssistantChatMessage.objects.filter(session_id=s.pk)
            .order_by("-created_at", "-id")
            .only("role", "content", "created_at")[:limit]
        )
        out = []
        for m in reversed(list(qs)):
            out.append({"role": m.role, "content": (m.content or "")[:2500]})
        return out
    except Exception:
        logger.exception("recent_session_messages failed")
        return []


_HABIT_RE = re.compile(r"\b(i\s+usually|i\s+often|most\s+of\s+the\s+time|i\s+always)\b", re.I)
_PREF_RE = re.compile(r"\b(i\s+prefer|i\s+like|please\s+always|in\s+future)\b", re.I)
_CONSTRAINT_RE = re.compile(r"\b(i\s+can'?t|i\s+cannot|i\s+won'?t|only\s+can|blocked\s+by)\b", re.I)


def extract_memory_items(text: str) -> list[tuple[str, str]]:
    """
    Super lightweight extraction to avoid extra LLM calls.
    Returns list of (type, content).
    """
    t = (text or "").strip()
    if not t:
        return []

    t_norm = " ".join(t.split())
    items: list[tuple[str, str]] = []

    if _HABIT_RE.search(t_norm):
        items.append((UserMemory.MemoryType.HABIT, t_norm))
    if _PREF_RE.search(t_norm):
        items.append((UserMemory.MemoryType.PREFERENCE, t_norm))
    if _CONSTRAINT_RE.search(t_norm):
        items.append((UserMemory.MemoryType.CONSTRAINT, t_norm))

    # If nothing matched but message is short and declarative, store as OTHER (low score).
    if not items and len(t_norm) <= 140 and ("I " in t_norm or t_norm.lower().startswith("my ")):
        items.append((UserMemory.MemoryType.OTHER, t_norm))

    # Deduplicate within the message.
    seen = set()
    uniq = []
    for typ, c in items:
        key = (typ, c.lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append((typ, c[:MAX_MEMORY_CHARS]))
    return uniq[:3]


@transaction.atomic
def extract_and_store_memories(user, user_text: str) -> list[int]:
    """
    Store memory candidates from the user message.
    Returns created memory ids.
    """
    created_ids: list[int] = []
    items = extract_memory_items(user_text)
    if not items:
        return created_ids

    for typ, content in items:
        v = embed_text(content)
        m = UserMemory.objects.create(
            user=user,
            type=typ,
            content=content,
            embedding=v,
            score=0.1 if v is None else 0.3,
        )
        created_ids.append(m.pk)
    return created_ids


def retrieve_memories(user, query: str, limit: int = 6) -> list[dict[str, Any]]:
    """
    Retrieve top memories by embedding similarity; falls back to keyword match.
    """
    limit = max(1, min(int(limit), 12))
    q = (query or "").strip()[:MAX_QUERY_CHARS]
    if not q:
        return []

    qv = embed_text(q)
    qs = UserMemory.objects.filter(user=user).only("id", "type", "content", "embedding", "last_used_at", "created_at")[:200]

    scored: list[tuple[float, UserMemory]] = []
    if qv is not None:
        for m in qs:
            v = m.embedding
            if isinstance(v, list) and v and all(isinstance(x, (int, float)) for x in v):
                sim = _cosine(qv, [float(x) for x in v])
                if sim > 0:
                    scored.append((sim, m))
        scored.sort(key=lambda t: t[0], reverse=True)
        picked = scored[:limit]
        out = []
        now = timezone.now()
        for sim, m in picked:
            UserMemory.objects.filter(pk=m.pk).update(last_used_at=now, score=float(sim))
            out.append({"id": m.pk, "type": m.type, "content": m.content, "score": float(sim)})
        return out

    # Fallback: keyword overlap
    q_words = {w for w in re.findall(r"[a-z0-9]{3,}", q.lower())}
    if not q_words:
        return []
    tmp = []
    for m in qs:
        mw = {w for w in re.findall(r"[a-z0-9]{3,}", (m.content or "").lower())}
        if not mw:
            continue
        overlap = len(q_words & mw)
        if overlap:
            tmp.append((overlap, m))
    tmp.sort(key=lambda t: t[0], reverse=True)
    out2 = []
    now2 = timezone.now()
    for overlap, m in tmp[:limit]:
        UserMemory.objects.filter(pk=m.pk).update(last_used_at=now2, score=float(overlap))
        out2.append({"id": m.pk, "type": m.type, "content": m.content, "score": float(overlap)})
    return out2

