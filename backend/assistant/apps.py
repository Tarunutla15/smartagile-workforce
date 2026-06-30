from django.apps import AppConfig


class AssistantConfig(AppConfig):
    """
    AI assistant layer: LangGraph workflow, analytics agent, semantic memory, and the
    chat HTTP API. Pure logic only — persistent models still live in the `smartagile` app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"
    verbose_name = "SmartAgile Assistant"

    def ready(self):
        # Connect incremental knowledge-indexing signals (doc-RAG, Tier 2B).
        try:
            from . import signals

            signals.register()
        except Exception:  # pragma: no cover - never block app startup
            import logging

            logging.getLogger(__name__).exception(
                "assistant: failed to register knowledge signals"
            )
