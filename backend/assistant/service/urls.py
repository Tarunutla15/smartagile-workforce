from django.urls import path

from .api import (
    AssistantReportConfirmView,
    AssistantSessionDetailView,
    AssistantSessionListCreateView,
    AssistantSessionMessageView,
)

urlpatterns = [
    path("sessions/", AssistantSessionListCreateView.as_view(), name="assistant_sessions"),
    path(
        "sessions/<int:session_id>/",
        AssistantSessionDetailView.as_view(),
        name="assistant_session_detail",
    ),
    path(
        "sessions/<int:session_id>/messages/",
        AssistantSessionMessageView.as_view(),
        name="assistant_session_messages",
    ),
    path(
        "sessions/<int:session_id>/report/confirm/",
        AssistantReportConfirmView.as_view(),
        name="assistant_report_confirm",
    ),
]

