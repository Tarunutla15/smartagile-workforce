"""
Chat models: Groq first (default), then OpenAI when `LLM_PROVIDER=auto` or on Groq errors.

- `LLM_PROVIDER=auto` (default): use Groq if GROQ_API_KEY is set; on invoke failure, retry
  with OpenAI if OPENAI_API_KEY is set. If no Groq key, use OpenAI.
- `LLM_PROVIDER=groq`: only Groq (no OpenAI fallback).
- `LLM_PROVIDER=openai`: only OpenAI.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore

try:
    from langchain_core.messages import BaseMessage
except ImportError:  # pragma: no cover
    BaseMessage = Any  # type: ignore


def _set_label(llm: Any, label: dict[str, Any]) -> None:
    llm._sa_label = label  # type: ignore[attr-defined]


def _make_groq_llm() -> Any | None:
    if not ChatOpenAI:
        return None
    key = (getattr(settings, "GROQ_API_KEY", None) or "").strip()
    if not key:
        return None
    m = ChatOpenAI(
        model=getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
        openai_api_key=key,
        openai_api_base=getattr(
            settings, "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
        ),
        temperature=0.15,
        max_tokens=1024,
    )
    _set_label(
        m,
        {
            "provider": "groq",
            "model": getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile"),
        },
    )
    return m


def _make_openai_llm() -> Any | None:
    if not ChatOpenAI:
        return None
    key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not key:
        return None
    kwargs: dict[str, Any] = {
        "model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
        "openai_api_key": key,
        "temperature": 0.15,
        "max_tokens": 1024,
    }
    base = getattr(settings, "OPENAI_BASE_URL", None) or None
    if base:
        kwargs["openai_api_base"] = base
    m = ChatOpenAI(**kwargs)
    _set_label(
        m,
        {
            "provider": "openai",
            "model": getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
        },
    )
    return m


def _provider_mode() -> str:
    return (getattr(settings, "LLM_PROVIDER", "auto") or "auto").strip().lower()


def is_llm_configured() -> bool:
    """True if any provider can be used in the current mode (keys set)."""
    p = _provider_mode()
    if p == "openai":
        return _make_openai_llm() is not None
    if p == "groq":
        return _make_groq_llm() is not None
    return _make_groq_llm() is not None or _make_openai_llm() is not None


def get_chat_model() -> Any | None:
    """
    Single "primary" model handle for code that only checks availability / calls once.

    - `auto`: Groq if key exists, else OpenAI (use `invoke_system_human_resilient` for
      runtime Groq-fail -> OpenAI fallback).
    - `groq` / `openai`: that provider only.
    """
    p = _provider_mode()
    if p == "openai":
        return _make_openai_llm()
    if p == "groq":
        return _make_groq_llm()
    return _make_groq_llm() or _make_openai_llm()


def _invoke_with_llm(
    llm: Any, messages: list[BaseMessage]
) -> tuple[str, Any]:
    r = llm.invoke(messages)
    text = (getattr(r, "content", None) or str(r)).strip()
    return text, llm


def invoke_messages_resilient(messages: list[BaseMessage]) -> tuple[str, Any]:
    """
    Run a chat. In `auto` mode: try Groq, then on failure try OpenAI.
    In `groq` / `openai` mode: a single provider only.
    """
    p = _provider_mode()

    if p == "openai":
        o = _make_openai_llm()
        if not o:
            raise RuntimeError("No OPENAI_API_KEY for LLM_PROVIDER=openai")
        return _invoke_with_llm(o, messages)

    if p == "groq":
        g = _make_groq_llm()
        if not g:
            raise RuntimeError("No GROQ_API_KEY for LLM_PROVIDER=groq")
        return _invoke_with_llm(g, messages)

    # auto: base = Groq, fall back to OpenAI (missing key or API error)
    g = _make_groq_llm()
    o = _make_openai_llm()
    if g:
        try:
            return _invoke_with_llm(g, messages)
        except Exception as e:
            logger.warning("Groq request failed; falling back to OpenAI: %s", e)
            if o:
                return _invoke_with_llm(o, messages)
            raise
    if o:
        return _invoke_with_llm(o, messages)
    raise RuntimeError("No GROQ_API_KEY or OPENAI_API_KEY set")


def invoke_system_human_resilient(
    system: str, human: str
) -> tuple[str, Any]:
    from langchain_core.messages import HumanMessage, SystemMessage

    return invoke_messages_resilient(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )


def llm_label(llm: Any) -> dict[str, Any] | None:
    if llm is None:
        return None
    if getattr(llm, "_sa_label", None):
        return llm._sa_label  # type: ignore[union-attr]
    p = _provider_mode()
    if p == "groq":
        return {
            "provider": "groq",
            "model": getattr(settings, "GROQ_MODEL", "groq"),
        }
    return {
        "provider": "openai",
        "model": getattr(settings, "OPENAI_MODEL", "openai"),
    }
