from django.apps import AppConfig


class AssistantConfig(AppConfig):
    """
    AI assistant layer: LangGraph workflow, analytics agent, semantic memory, and the
    chat HTTP API. Pure logic only — persistent models still live in the `smartagile` app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "assistant"
    verbose_name = "SmartAgile Assistant"
