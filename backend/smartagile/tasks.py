import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from .models import UsageEvent

logger = logging.getLogger(__name__)

CHUNK = 500


def _parse_occurred_at(value):
    if value is None:
        return timezone.now()
    if hasattr(value, "isoformat"):
        return value if timezone.is_aware(value) else timezone.make_aware(value, timezone.get_current_timezone())
    s = str(value)
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    occurred_at = parse_datetime(s)
    if occurred_at is None:
        return timezone.now()
    if timezone.is_naive(occurred_at):
        occurred_at = timezone.make_aware(occurred_at, timezone.get_current_timezone())
    return occurred_at


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def persist_usage_events_batch(self, user_id: int, events: list):
    """
    Persist validated events. Each event dict uses string occurred_at (ISO) or datetime.
    """
    if not events:
        return 0

    to_create = []
    for e in events:
        dur = float(e["duration_seconds"])
        raw_idle = float(e.get("idle_seconds", 0) or 0)
        to_create.append(
            UsageEvent(
                user_id=int(user_id),
                source_type=e["source_type"],
                name=e["name"],
                context=e.get("context", "") or "",
                category=e.get("category", "") or "",
                duration_seconds=dur,
                idle_seconds=min(dur, max(0.0, raw_idle)),
                keystrokes=float(e.get("keystrokes", 0) or 0),
                clicks=float(e.get("clicks", 0) or 0),
                scrolls=float(e.get("scrolls", 0) or 0),
                occurred_at=_parse_occurred_at(e.get("occurred_at")),
            )
        )

    total = 0
    try:
        for i in range(0, len(to_create), CHUNK):
            chunk = to_create[i : i + CHUNK]
            UsageEvent.objects.bulk_create(chunk, batch_size=CHUNK)
            total += len(chunk)
    except Exception as exc:
        logger.exception("persist_usage_events_batch failed user_id=%s", user_id)
        raise self.retry(exc=exc) from exc

    return total


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_password_reset_otp_email(self, to_email: str, otp: int):
    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        settings.EMAIL_HOST_USER or "noreply@localhost",
    )
    if not (getattr(settings, "EMAIL_HOST_PASSWORD", None) or ""):
        logger.error("send_password_reset_otp_email: missing EMAIL_HOST_PASSWORD; aborting send to %r", to_email)
        raise RuntimeError("EMAIL_HOST_PASSWORD is not set; configure backend/.env")
    try:
        logger.info(
            "send_password_reset_otp_email: sending from=%r to=%r (OTP not logged)",
            from_email,
            to_email,
        )
        send_mail(
            subject="Password Reset OTP",
            message=f"Your OTP for password reset is {otp}.",
            from_email=from_email,
            recipient_list=[to_email],
            fail_silently=False,
        )
        logger.info("send_password_reset_otp_email: SMTP send_mail finished OK to=%r", to_email)
    except Exception as exc:
        logger.exception("send_password_reset_otp_email: SMTP failed for to=%r", to_email)
        raise self.retry(exc=exc) from exc


@shared_task
def run_usage_daily_rollup(target_date_iso=None):
    """
    ETL: aggregate UsageEvent into UsageDailyRollup (with intelligence features) for one day.
    Default: yesterday in the current timezone.
    """
    from .insights import sync_rollup_for_day

    if target_date_iso:
        d = parse_date(target_date_iso)
        if d is None:
            logger.warning("run_usage_daily_rollup: bad date %s", target_date_iso)
            return 0
    else:
        d = timezone.localdate() - timedelta(days=1)

    user_ids = (
        UsageEvent.objects.filter(occurred_at__date=d)
        .values_list("user_id", flat=True)
        .distinct()
    )
    n = 0
    for uid in user_ids:
        try:
            sync_rollup_for_day(int(uid), d)
            n += 1
        except Exception:
            logger.exception("sync_rollup_for_day failed user_id=%s day=%s", uid, d)
    return n


@shared_task
def run_placeholder_ai_job(job_type, payload=None):
    """Reserved hook for future ML / AI workloads (run via Celery worker)."""
    payload = payload or {}
    logger.info(
        "run_placeholder_ai_job type=%s keys=%s",
        job_type,
        list(payload.keys()),
    )
    return {"status": "noop", "job_type": job_type}
