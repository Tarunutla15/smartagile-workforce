"""POST batched usage events to the Django ingestion API (no direct DB from the agent).

Resilience notes
----------------
This loop runs on a background thread and must **never** die: if it raised, the
engine would keep queueing events with no consumer, so usage would silently stop
uploading until the whole agent restarts (re-pairing alone would not fix it).

To guarantee that:
- every network call is wrapped so ``requests`` exceptions (connection refused,
  timeouts, DNS, sleep/wake, server restarts) are caught and treated as transient;
- transient failures keep the events buffered and retry on the next interval
  (bounded by ``MAX_PENDING_EVENTS`` so memory cannot grow without limit);
- a recovered backlog is drained in chunks below the server's per-request cap;
- the loop body has a final catch-all so an unexpected error logs and continues.
"""

from __future__ import annotations

import logging
import queue
import time

import agent_status
import auth_session
import auth_store
import requests

BATCH_INTERVAL_SEC = 2.0
BATCH_MAX_EVENTS = 48
# Keep each POST well under the server's MAX_BATCH (2000) so a drained backlog
# never trips the "too many events" rejection.
MAX_POST_EVENTS = 500
# Cap how many events we buffer during an outage; drop oldest beyond this.
MAX_PENDING_EVENTS = 5000

logger = logging.getLogger(__name__)
_logged_waiting_for_pair = False


def _strip_internal(events: list) -> list:
    """Drop internal bookkeeping keys (``_``-prefixed) before sending to the server."""
    return [{k: v for k, v in e.items() if not k.startswith("_")} for e in events]


def _post_batch(events: list):
    base = auth_session.get_api_base()
    url = f"{base}/api/usage-events/batch/"
    token = auth_session.get_valid_access_token()
    if not token:
        return None
    return requests.post(
        url,
        json={"events": _strip_internal(events)},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=45,
    )


def _purge_foreign_user(batch: list) -> None:
    """Drop buffered events captured under a different account than the one now paired.

    Data is attributed server-side by the paired user's JWT. If the PC is re-paired to
    another user while events are still buffered, sending them would mis-attribute one
    user's activity to another. Events whose capture-time account no longer matches the
    current paired user are dropped in place. Events captured before any pairing
    (``_paired_user_id is None``) are kept — they go to whoever first pairs.
    """
    current = auth_store.get_paired_user_id()
    if current is None or not batch:
        return  # not paired yet: nothing to send anyway; keep until a user pairs
    kept = []
    dropped = 0
    for e in batch:
        tag = e.get("_paired_user_id")
        if tag is None or tag == current:
            kept.append(e)
        else:
            dropped += 1
    if dropped:
        logger.info(
            "dropped %s buffered event(s) from a previously-paired account (now user %s)",
            dropped,
            current,
        )
        batch[:] = kept


def _send_once(events: list) -> bool:
    """POST one chunk of events.

    Returns ``True`` when the chunk was handled (accepted, or intentionally
    dropped because it can never succeed), and ``False`` on a transient error so
    the caller keeps the events buffered and retries later. Never raises.
    """
    global _logged_waiting_for_pair
    try:
        r = _post_batch(events)
    except requests.RequestException as exc:
        # Server down / sleep-wake / network blip. Transient: keep events, retry.
        logger.warning("usage ingest network error (will retry): %s", exc)
        agent_status.record_transient(f"network: {exc}")
        return False

    if r is None:
        # Before Settings → Connect, uploads cannot run — one info line, not a storm.
        agent_status.record_waiting_pair()
        if not _logged_waiting_for_pair:
            _logged_waiting_for_pair = True
            logger.info(
                "Not paired yet: open SmartAgile → Settings → Connect desktop app, "
                "or set SMARTAGILE_ACCESS_TOKEN. (Short gaps until then are normal.)"
            )
        else:
            logger.debug("No JWT yet; dropping %s events (pair when ready)", len(events))
        return True

    if r.status_code == 401:
        auth_session.clear_memory_cache()
        new = auth_session.refresh_access_token()
        if new:
            try:
                r = _post_batch(events)
            except requests.RequestException as exc:
                logger.warning("usage ingest network error after refresh (will retry): %s", exc)
                agent_status.record_transient(f"network after refresh: {exc}")
                return False
        if r is None or r.status_code == 401:
            logger.error(
                "usage ingest 401: refresh the app session and pair again. Body: %s",
                (r.text if r is not None else "")[:200],
            )
            # Auth problem on this payload — don't loop on it forever. Surface it so the
            # Settings page can prompt a reconnect instead of failing silently.
            agent_status.record_needs_reconnect("session expired — reconnect from Settings")
            return True

    sc = r.status_code
    if 200 <= sc < 300:
        _logged_waiting_for_pair = False
        agent_status.record_ok(len(events))
        return True
    if sc in (408, 429) or sc >= 500:
        # Transient server-side issue: keep events and retry next interval.
        logger.warning("usage ingest transient %s (will retry): %s", sc, (r.text or "")[:200])
        agent_status.record_transient(f"server {sc}")
        return False
    # Other 4xx — permanent for this payload; drop so it can't block the queue.
    logger.error(
        "usage ingest rejected %s; dropping %s events. Body: %s",
        sc,
        len(events),
        (r.text or "")[:200],
    )
    agent_status.record_transient(f"rejected {sc}")
    return True


def http_writer_loop(job_queue):
    """Consume lists of usage-event dicts; POST batches to /api/usage-events/batch/."""
    batch: list = []
    last_flush = time.monotonic()

    def flush():
        nonlocal batch, last_flush
        last_flush = time.monotonic()
        # Never upload another user's buffered activity under the current account.
        _purge_foreign_user(batch)
        # Drain in chunks; stop on the first transient failure so we don't hammer
        # a down server, and cap the buffer so memory can't grow unbounded.
        while batch:
            chunk = batch[:MAX_POST_EVENTS]
            if _send_once(chunk):
                del batch[: len(chunk)]
            else:
                if len(batch) > MAX_PENDING_EVENTS:
                    dropped = len(batch) - MAX_PENDING_EVENTS
                    del batch[:dropped]
                    logger.warning(
                        "usage backlog over %s; dropped %s oldest events",
                        MAX_PENDING_EVENTS,
                        dropped,
                    )
                break

    while True:
        timeout = max(0.05, BATCH_INTERVAL_SEC - (time.monotonic() - last_flush))
        try:
            msg = job_queue.get(timeout=timeout)
        except queue.Empty:
            msg = "__INTERVAL__"

        try:
            if msg is None:  # sentinel: flush + exit
                flush()
                break
            if msg == "__INTERVAL__":
                flush()
                continue
            if isinstance(msg, list):
                batch.extend(msg)
            if len(batch) >= BATCH_MAX_EVENTS:
                flush()
        except Exception as exc:  # noqa: BLE001 — final safety net: thread must not die
            logger.exception("http writer loop error (continuing): %s", exc)
            time.sleep(1.0)
