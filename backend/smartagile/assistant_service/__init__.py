"""
Assistant service package.

Goal: keep all assistant/chat-related backend logic in one place:
- HTTP API views + urls
- memory extraction/retrieval
- assistant reply orchestration (LangGraph entrypoint lives in smartagile.assistant_brain)
"""

