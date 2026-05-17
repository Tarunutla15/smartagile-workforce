"""Persist web login / logout for per-user counts and history."""

import logging

from .models import AuthSessionEvent

logger = logging.getLogger(__name__)


def record_auth_event(user_id: int, event: str) -> None:
    """event: AuthSessionEvent.EventType.LOGIN or .LOGOUT"""
    try:
        AuthSessionEvent.objects.create(user_id=int(user_id), event=event)
    except Exception:
        logger.exception("record_auth_event failed user_id=%s event=%s", user_id, event)
