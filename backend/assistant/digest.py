"""
Scheduling / digest agent helpers.

Parses a chat request into a digest action, persists the user's cadence preference,
and produces the confirmation text. The actual recurring send is done by the Celery
beat task `smartagile.tasks.send_scheduled_usage_digests`.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_OFF_RE = re.compile(
    r"\b(stop|turn\s+off|disable|cancel|unsubscribe|no\s+more|off)\b", re.IGNORECASE
)
_DAILY_RE = re.compile(r"\b(daily|every\s+day|each\s+day|per\s+day)\b", re.IGNORECASE)
_WEEKLY_RE = re.compile(
    r"\b(weekly|every\s+week|each\s+week|once\s+a\s+week|per\s+week)\b", re.IGNORECASE
)
_STATUS_RE = re.compile(
    r"\b(what('?s| is)|current|my)\b.*\b(digest|schedule|subscription)\b", re.IGNORECASE
)
# "send it now / immediately / right away" -> also fire the digest email this instant.
_NOW_RE = re.compile(
    r"\b(now|immediately|right\s+now|right\s+away|asap|instantly|straight\s+away)\b",
    re.IGNORECASE,
)

VALID_FREQUENCIES = ("off", "daily", "weekly")


def wants_immediate_send(user_text: str) -> bool:
    """True when the user wants the digest emailed right now (not just scheduled)."""
    return bool(_NOW_RE.search(user_text or ""))


def parse_digest_request(user_text: str) -> str:
    """
    Map a message to an action:
      - "daily" / "weekly" / "off": set that cadence
      - "status": user is asking about the current setting
      - "ambiguous": wants a digest but didn't say how often
    Order matters: an explicit cadence wins over a bare "off" word, and "off"
    wins over a generic enable request.
    """
    t = user_text or ""
    if _DAILY_RE.search(t):
        return "daily"
    if _WEEKLY_RE.search(t):
        return "weekly"
    if _OFF_RE.search(t):
        return "off"
    if _STATUS_RE.search(t):
        return "status"
    return "ambiguous"


def set_digest_frequency(user, frequency: str) -> str:
    """Persist the cadence on the user (no-op safe). Returns the stored value."""
    freq = frequency if frequency in VALID_FREQUENCIES else "off"
    if getattr(user, "digest_frequency", None) != freq:
        user.digest_frequency = freq
        try:
            user.save(update_fields=["digest_frequency"])
        except Exception:
            user.save()
    return freq


def describe_digest(frequency: str, *, user_email: str = "", just_changed: bool = False) -> str:
    """Human-friendly confirmation / status text."""
    email = user_email or "your account email"
    if frequency == "daily":
        when = "every morning (a recap of the previous day)"
    elif frequency == "weekly":
        when = "every Monday morning (a recap of last week)"
    else:
        if just_changed:
            return "Done — I've turned **off** your recurring usage digest. You won't get scheduled emails anymore."
        return (
            "Your recurring usage digest is currently **off**. "
            "Say *“email me a daily digest”* or *“send a weekly summary”* to turn it on."
        )

    lead = "Done — I'll" if just_changed else "You're set to receive a digest. I'll"
    return (
        f"{lead} email your SmartAgile usage digest to **{email}** {when}.\n\n"
        "You can change it anytime (*“make it weekly”*) or stop it (*“turn off my digest”*)."
    )


def send_digest_now(user, frequency: str) -> dict:
    """
    Build and email the digest for `frequency` to the user immediately (synchronous).

    daily -> previous day's report; weekly -> last week's. Returns a result dict:
    {"sent": bool, "recipient": str, "has_data": bool, "period_label": str, "reason": str}.
    Sends even when there's no tracked data (explicit user request), unlike the scheduled job.
    """
    from .report import build_usage_report, render_report_email
    from smartagile.tasks import send_usage_report_email

    freq = frequency if frequency in ("daily", "weekly") else "daily"
    period = {"kind": "yesterday"} if freq == "daily" else {"kind": "last_week"}
    email = (getattr(user, "email", "") or "").strip()
    if not email:
        return {"sent": False, "reason": "no_email"}

    try:
        report = build_usage_report(user, period)
        subject, html_body, text_body = render_report_email(report, user=user)
    except Exception:
        logger.exception("send_digest_now: failed to build report for user_id=%s", getattr(user, "pk", None))
        return {"sent": False, "reason": "build_failed", "recipient": email}

    try:
        send_usage_report_email(email, subject, html_body, text_body)
    except RuntimeError as exc:
        logger.warning("send_digest_now: SMTP not configured: %s", exc)
        return {"sent": False, "reason": "smtp_not_configured", "recipient": email}
    except Exception:
        logger.exception("send_digest_now: send failed for %r", email)
        return {"sent": False, "reason": "send_failed", "recipient": email}

    return {
        "sent": True,
        "recipient": email,
        "has_data": bool(report.get("has_data")),
        "period_label": report.get("period_label") or ("yesterday" if freq == "daily" else "last week"),
    }


def describe_immediate_send(res: dict, frequency: str, *, scheduled: str | None = None) -> str:
    """Confirmation text for an immediate send, optionally noting the recurring cadence set."""
    email = res.get("recipient") or "your account email"
    when = res.get("period_label") or ("yesterday" if frequency == "daily" else "last week")

    cadence_note = ""
    if scheduled in ("daily", "weekly"):
        every = "every morning" if scheduled == "daily" else "every Monday morning"
        cadence_note = f"\n\nI'll also keep emailing your **{scheduled}** digest {every}."

    if res.get("sent"):
        nodata = "" if res.get("has_data") else " (there was no tracked activity for that period, so the email says so)"
        return f"Sent your usage digest to **{email}** now — a recap of **{when}**{nodata}.{cadence_note}"

    reason = res.get("reason")
    if reason == "smtp_not_configured":
        base = (
            "I couldn't send it right now — email isn't configured on the server yet "
            "(missing SMTP credentials in `backend/.env`)."
        )
    elif reason == "no_email":
        base = "I couldn't send it — your account doesn't have an email address on file."
    else:
        base = "I couldn't send it right now — the email failed to go out. Please try again in a moment."
    return base + cadence_note
