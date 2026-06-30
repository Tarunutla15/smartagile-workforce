import logging
import random
import traceback
from email.mime.text import MIMEText

from django.contrib.auth import get_user_model
from django.core import validators
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from backend import settings
from .attendance_db import finalize_logout_attendance, record_login_attendance
from .auth_events import record_auth_event
from .models import AgentStatus, AuthSessionEvent, Notification
from .permissions import IsAdminRole
from .tasks import persist_usage_events_batch, send_password_reset_otp_email
from .usage_ingest import normalize_usage_events
from .usage_query import usage_rows_for_signup_user_id
from .insights import (
    build_insights,
    compute_app_activity_detail,
    compute_features_from_events,
    load_baseline_rollups,
)
from .password_utils import verify_and_upgrade_password
from .serializers import (
    AuthSessionEventSerializer,
    NotificationSerializer,
    SessionUserSerializer,
    UserRegistrationSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentUserView(APIView):
    """GET: JWT identifies user; sets CSRF cookie for cookie-based flows."""

    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return Response(
                {
                    "authenticated": True,
                    "user": SessionUserSerializer(request.user).data,
                }
            )
        return Response({"authenticated": False, "user": None})


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        password = request.data.get("password")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_and_upgrade_password(user, password):
            return Response(
                {"error": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            record_login_attendance(user.id)
        except Exception:
            logger.exception("record_login_attendance failed")

        record_auth_event(user.id, AuthSessionEvent.EventType.LOGIN)

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Login successful.",
                "user": SessionUserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )


class SignupDataCreateView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            record_auth_event(user.id, AuthSessionEvent.EventType.LOGIN)
            if getattr(user, "role", "employee") != "admin":
                try:
                    record_login_attendance(user.id)
                except Exception:
                    logger.exception("record_login_attendance after signup failed")
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "user": SessionUserSerializer(user).data,
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckDataView(APIView):
    """Admin-only: list users (no passwords)."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, *args, **kwargs):
        try:
            data_exists = User.objects.exists()
            if data_exists:
                data = SessionUserSerializer(
                    User.objects.all().order_by("id"), many=True
                ).data
            else:
                data = None
            return Response({"data_exists": data_exists, "data": data})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AuthSessionEventsView(APIView):
    """GET: current user's login/logout history and monthly counts."""

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        uid = request.user.pk
        try:
            limit = int(request.query_params.get("limit", 100))
        except ValueError:
            limit = 100
        limit = max(1, min(limit, 500))

        qs = AuthSessionEvent.objects.filter(user_id=uid).order_by("-created_at")[:limit]
        events = AuthSessionEventSerializer(qs, many=True).data

        local_now = timezone.localtime(timezone.now())
        month_start = local_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        today = timezone.localdate()

        month_qs = AuthSessionEvent.objects.filter(
            user_id=uid,
            created_at__gte=month_start,
        )
        today_qs = AuthSessionEvent.objects.filter(
            user_id=uid,
            created_at__date=today,
        )

        summary = {
            "logins_this_month": month_qs.filter(event=AuthSessionEvent.EventType.LOGIN).count(),
            "logouts_this_month": month_qs.filter(event=AuthSessionEvent.EventType.LOGOUT).count(),
            "logins_today": today_qs.filter(event=AuthSessionEvent.EventType.LOGIN).count(),
            "logouts_today": today_qs.filter(event=AuthSessionEvent.EventType.LOGOUT).count(),
        }

        return Response({"summary": summary, "events": events})


class ForgotPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    GENERIC_MESSAGE = (
        "If an account exists for this email, we sent a reset code. "
        "Check your inbox."
    )

    def post(self, request):
        try:
            email = (request.data.get("email") or "").strip()
            if not email:
                return Response({"error": "Email is required"}, status=400)

            validators.validate_email(email)

            request.session.pop("otp", None)
            request.session.pop("reset_email", None)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                logger.warning(
                    "forgot_password: no account for email=%r — not sending any email (same user-facing message as success)",
                    email,
                )
                request.session.save()
                return Response({"message": self.GENERIC_MESSAGE}, status=200)

            otp = random.randint(100000, 999999)
            request.session["otp"] = otp
            request.session["reset_email"] = email
            request.session.save()

            if not (settings.EMAIL_HOST_PASSWORD or ""):
                logger.error(
                    "forgot_password: EMAIL_HOST_PASSWORD is empty — email cannot be sent; check backend/.env"
                )

            logger.info(
                "forgot_password: user id=%s, dispatching OTP email task to=%r",
                user.pk,
                email,
            )
            send_password_reset_otp_email.delay(email, otp)

            return Response({"message": self.GENERIC_MESSAGE}, status=200)

        except validators.ValidationError as e:
            return Response({"error": str(e)}, status=400)

        except Exception:
            logger.exception("forgot_password: unhandled error")
            return Response({"error": "Internal Server Error"}, status=500)


class ResetPasswordView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            new_password = request.data.get("password")
            otp_user = request.data.get("otp")

            session_otp = request.session.get("otp")
            session_email = request.session.get("reset_email")

            if session_otp is None or not session_email:
                return Response(
                    {
                        "error": "Reset session expired. Request a new code from the forgot-password page."
                    },
                    status=400,
                )

            if otp_user is None or str(session_otp).strip() != str(otp_user).strip():
                return Response({"error": "Invalid or expired code."}, status=400)

            if not new_password:
                return Response({"error": "Password is required"}, status=400)

            user = User.objects.filter(email__iexact=(session_email or "").strip()).first()
            if not user:
                request.session.pop("otp", None)
                request.session.pop("reset_email", None)
                request.session.save()
                return Response(
                    {"error": "User with this email does not exist."}, status=400
                )

            user.set_password(new_password)
            user.save(update_fields=["password"])

            del request.session["otp"]
            del request.session["reset_email"]
            request.session.save()

            return Response({"message": "Password updated successfully"}, status=200)

        except ObjectDoesNotExist:
            return Response(
                {"error": "User with the given email does not exist"}, status=400
            )
        except Exception as e:
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class UsageEventBatchIngestView(APIView):
    """
    Desktop agent: POST JSON {"events": [...]} with Bearer JWT access token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        uid = request.user.pk

        body = request.data
        if isinstance(body, list):
            raw = body
        else:
            raw = body.get("events") or []
        events, errors = normalize_usage_events(raw)
        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        serializable = []
        last_event_at = None
        for e in events:
            row = dict(e)
            occurred = row["occurred_at"]
            if last_event_at is None or occurred > last_event_at:
                last_event_at = occurred
            row["occurred_at"] = occurred.isoformat()
            serializable.append(row)

        # Enqueue (or, with CELERY_TASK_ALWAYS_EAGER, persist in-process). If the broker is
        # down or the persist raises, surface a retryable 503 instead of an unhandled 500 so
        # the desktop agent keeps the batch buffered and retries — no silent data loss.
        try:
            persist_usage_events_batch.delay(uid, serializable)
        except Exception:
            logger.exception("usage ingest enqueue/persist failed user_id=%s", uid)
            return Response(
                {"detail": "usage ingest temporarily unavailable; retry later", "queued": False},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Heartbeat: record that this user's agent is alive and delivering data. Best-effort
        # — a failure here must never fail an otherwise-accepted batch.
        try:
            self._touch_agent_status(uid, last_event_at, request)
        except Exception:
            logger.exception("agent status update failed user_id=%s (continuing)", uid)

        return Response(
            {"accepted": len(serializable), "queued": True},
            status=status.HTTP_202_ACCEPTED,
        )

    @staticmethod
    def _touch_agent_status(uid, last_event_at, request):
        now = timezone.now()
        version = (request.META.get("HTTP_X_SMARTAGILE_AGENT_VERSION") or "")[:64]
        defaults = {"last_seen_at": now}
        if last_event_at is not None:
            defaults["last_event_at"] = last_event_at
        if version:
            defaults["agent_version"] = version
        AgentStatus.objects.update_or_create(user_id=uid, defaults=defaults)


class NotificationListView(APIView):
    """GET: current user's notifications + unread count.

    Query params: ``?unread=1`` to return only unread, ``?limit=N`` (default 30, max 100).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        qs = Notification.objects.filter(user_id=request.user.pk)
        if str(request.query_params.get("unread", "")).strip() in ("1", "true", "yes"):
            qs = qs.filter(read_at__isnull=True)
        try:
            limit = int(request.query_params.get("limit", 30))
        except ValueError:
            limit = 30
        limit = max(1, min(limit, 100))

        unread = Notification.objects.filter(
            user_id=request.user.pk, read_at__isnull=True
        ).count()
        items = NotificationSerializer(qs[:limit], many=True).data
        return Response({"unread": unread, "results": items})


class NotificationReadView(APIView):
    """POST: mark one notification (``/<id>/read/``) or all (``/read-all/``) as read."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk=None, *args, **kwargs):
        now = timezone.now()
        qs = Notification.objects.filter(user_id=request.user.pk, read_at__isnull=True)
        if pk is not None:
            qs = qs.filter(pk=pk)
        updated = qs.update(read_at=now)
        unread = Notification.objects.filter(
            user_id=request.user.pk, read_at__isnull=True
        ).count()
        return Response({"updated": updated, "unread": unread})


class HealthView(APIView):
    """Unauthenticated readiness probe.

    The desktop agent and ops tooling hit this to distinguish a real outage (DB down,
    server starting) from a transient blip. Returns 200 only when the database is
    reachable; 503 otherwise so callers back off and retry instead of treating a cold
    start as a hard failure.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        db_ok = True
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        except Exception:
            db_ok = False
            logger.exception("health check: database unreachable")

        payload = {
            "ok": db_ok,
            "database": "ok" if db_ok else "down",
            "time": timezone.now().isoformat(),
            "timezone": str(getattr(settings, "TIME_ZONE", "UTC")),
        }
        code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=code)


class AgentStatusView(APIView):
    """GET: is the current user's desktop agent alive and uploading?

    ``connected`` is true when the last successful upload (heartbeat) is within the
    freshness window, so the UI can show "tracking active" vs "reconnect / start the agent"
    without the agent having to push a separate heartbeat.
    """

    permission_classes = [IsAuthenticated]

    FRESH_SECONDS = 180

    def get(self, request, *args, **kwargs):
        st = AgentStatus.objects.filter(user_id=request.user.pk).first()
        if st is None or st.last_seen_at is None:
            return Response(
                {
                    "connected": False,
                    "last_seen_at": None,
                    "last_event_at": None,
                    "agent_version": "",
                    "seconds_since_seen": None,
                }
            )
        age = (timezone.now() - st.last_seen_at).total_seconds()
        return Response(
            {
                "connected": age <= self.FRESH_SECONDS,
                "last_seen_at": st.last_seen_at.isoformat(),
                "last_event_at": st.last_event_at.isoformat() if st.last_event_at else None,
                "agent_version": st.agent_version or "",
                "seconds_since_seen": int(age),
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class AppDataView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            combined_list = usage_rows_for_signup_user_id(request.user.id)
            return Response(combined_list, status=status.HTTP_200_OK)
        except validators.ValidationError as e:
            logger.error("Validation error: %s", e)
            return Response({"error": "Invalid email format"}, status=400)
        except Exception as e:
            logger.error("Unexpected error: %s", e)
            return Response(
                {"error": "An unexpected error occurred"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class InsightsSummaryView(APIView):
    """
    Intelligence layer: feature snapshot for a day + rule / baseline insights.
    GET ?date=YYYY-MM-DD (default: today, local time).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        date_str = request.query_params.get("date")
        if date_str:
            d = parse_date(str(date_str).strip())
            if d is None:
                return Response(
                    {"error": "Invalid date. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            d = timezone.localdate()

        uid = request.user.pk
        features = compute_features_from_events(uid, d)
        app_activity = compute_app_activity_detail(uid, d)
        baseline = load_baseline_rollups(uid, d, days=7)
        insight_cards = build_insights(features, baseline)
        return Response(
            {
                "date": d.isoformat(),
                "features": features.to_dict(),
                "app_activity": app_activity,
                "baseline_sample_days": len(baseline),
                "insights": insight_cards,
            },
            status=status.HTTP_200_OK,
        )


class AdminEmployeeUsageView(APIView):
    """Admin-only: GET aggregated usage for another user."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request, employee_id, *args, **kwargs):
        if not User.objects.filter(pk=employee_id).exists():
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        rows = usage_rows_for_signup_user_id(int(employee_id))
        return Response(rows, status=status.HTTP_200_OK)


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        uid = request.user.pk
        record_auth_event(uid, AuthSessionEvent.EventType.LOGOUT)
        try:
            finalize_logout_attendance(uid)
        except Exception:
            logger.exception("finalize_logout_attendance failed")
        request.session.pop("signup_user_id", None)
        request.session.save()
        return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)


class AttendanceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        suffix = f"_{request.user.id}"
        attendance = []

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT login, date, logout, duration
                    FROM attendence{suffix}
                    ORDER BY date DESC
                    LIMIT 120
                    """
                )
                rows = cursor.fetchall()
        except Exception as e:
            logger.warning("attendance table read failed: %s", e)
            return Response([], status=status.HTTP_200_OK)

        for row in rows:
            login_ts, work_date, logout_ts, dur = row
            attendance.append(
                {
                    "login_iso": login_ts.isoformat() if login_ts else None,
                    "login": login_ts.strftime("%H:%M:%S") if login_ts else None,
                    "date": work_date.isoformat() if work_date else None,
                    "logout_iso": logout_ts.isoformat() if logout_ts else None,
                    "logout": logout_ts.strftime("%H:%M:%S") if logout_ts else None,
                    "duration_seconds": float(dur) if dur is not None else None,
                }
            )

        return Response(attendance, status=status.HTTP_200_OK)
