"""
LangGraph assistant: classify → route → load context → synthesize (template or LLM).

Default `LLM_PROVIDER=auto`: use Groq when `GROQ_API_KEY` is set; if the request fails
(or no Groq key), use `OPENAI_API_KEY`. Set `LLM_PROVIDER=groq` or `openai` to lock one provider.
"""

from .runner import run_assistant_graph

__all__ = ["run_assistant_graph"]
