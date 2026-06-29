import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
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


def send_usage_report_email(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    """
    Send a usage-report email (HTML + plaintext) synchronously.

    Called from the assistant confirm endpoint so we can report real success/failure to
    the user. Raises RuntimeError if SMTP is not configured, or the underlying SMTP error.
    """
    from_email = getattr(
        settings,
        "DEFAULT_FROM_EMAIL",
        settings.EMAIL_HOST_USER or "noreply@localhost",
    )
    if not (getattr(settings, "EMAIL_HOST_PASSWORD", None) or ""):
        logger.error("send_usage_report_email: missing EMAIL_HOST_PASSWORD; aborting send to %r", to_email)
        raise RuntimeError("EMAIL_HOST_PASSWORD is not set; configure backend/.env")

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body or "",
        from_email=from_email,
        to=[to_email],
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    logger.info("send_usage_report_email: sending from=%r to=%r subject=%r", from_email, to_email, subject)
    msg.send(fail_silently=False)
    logger.info("send_usage_report_email: SMTP send finished OK to=%r", to_email)


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
def send_scheduled_usage_digests(frequency: str):
    """
    Scheduling agent: email a recurring usage digest to every user opted into `frequency`.

    daily  -> previous day's report; weekly -> last week's report. Users with no tracked
    activity for the period are skipped (no point emailing an empty digest).
    Returns the number of digests actually sent.
    """
    from django.contrib.auth import get_user_model

    from assistant.report import build_usage_report, render_report_email

    if frequency not in ("daily", "weekly"):
        logger.warning("send_scheduled_usage_digests: bad frequency %r", frequency)
        return 0

    period = {"kind": "yesterday"} if frequency == "daily" else {"kind": "last_week"}
    User = get_user_model()
    recipients = User.objects.filter(digest_frequency=frequency).exclude(email="")

    sent = 0
    for user in recipients.iterator():
        try:
            report = build_usage_report(user, period)
            if not report.get("has_data"):
                continue
            subject, html_body, text_body = render_report_email(report, user=user)
            send_usage_report_email(user.email, subject, html_body, text_body)
            sent += 1
        except RuntimeError as exc:
            # SMTP not configured — stop early; the rest will fail the same way.
            logger.warning("send_scheduled_usage_digests aborted (%s): %s", frequency, exc)
            break
        except Exception:
            logger.exception(
                "send_scheduled_usage_digests: failed for user_id=%s", getattr(user, "pk", None)
            )
    logger.info("send_scheduled_usage_digests(%s): sent %d digest(s)", frequency, sent)
    return sent


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
