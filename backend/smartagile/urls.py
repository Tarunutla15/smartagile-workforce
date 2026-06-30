from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import *

urlpatterns = [
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('signup/', SignupDataCreateView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('check_data/', CheckDataView.as_view(), name='check_data'),
    path(
        'admin/employee/<int:employee_id>/usage/',
        AdminEmployeeUsageView.as_view(),
        name='admin_employee_usage',
    ),
    path('forgetpassword/', ForgotPasswordView.as_view(), name='forgetpassword'),
    path('resetpassword/', ResetPasswordView.as_view(), name='resetpassword'),
    path('appdata/', AppDataView.as_view(), name='appdata'),
    path("insights/summary/", InsightsSummaryView.as_view(), name="insights_summary"),
    path("logout/", LogoutAPIView.as_view(), name="logout"),
    path("attendence/", AttendanceListView.as_view(), name="attendence"),
    path('auth_events/', AuthSessionEventsView.as_view(), name='auth_events'),
    path(
        'usage-events/batch/',
        UsageEventBatchIngestView.as_view(),
        name='usage_events_batch',
    ),
    path("health/", HealthView.as_view(), name="health"),
    path("agent/status/", AgentStatusView.as_view(), name="agent_status"),
    path("notifications/", NotificationListView.as_view(), name="notifications"),
    path(
        "notifications/read-all/",
        NotificationReadView.as_view(),
        name="notifications_read_all",
    ),
    path(
        "notifications/<int:pk>/read/",
        NotificationReadView.as_view(),
        name="notification_read",
    ),
    path("assistant/", include("assistant.service.urls")),
]
