"""POST batched usage events to the Django ingestion API (no direct DB from the agent)."""

from __future__ import annotations

import logging
import queue
import time

import auth_session
import requests

BATCH_INTERVAL_SEC = 2.0
BATCH_MAX_EVENTS = 48

logger = logging.getLogger(__name__)
_logged_waiting_for_pair = False


def _post_batch(events: list):
    base = auth_session.get_api_base()
    url = f"{base}/api/usage-events/batch/"
    token = auth_session.get_valid_access_token()
    if not token:
        return None
    return requests.post(
        url,
        json={"events": events},
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=45,
    )


def _post_batch_with_retry(events: list) -> None:
    global _logged_waiting_for_pair
    r = _post_batch(events)
    if r is None:
        # Before Settings → Connect, uploads cannot run — one info line, not a storm of warnings.
        if not _logged_waiting_for_pair:
            _logged_waiting_for_pair = True
            logger.info(
                "Not paired yet: open SmartAgile → Settings → Connect desktop app, "
                "or set SMARTAGILE_ACCESS_TOKEN. (Short gaps until then are normal.)"
            )
        else:
            logger.debug("No JWT yet; dropping %s events (pair when ready)", len(events))
        return
    if r.status_code == 401:
        auth_session.clear_memory_cache()
        new = auth_session.refresh_access_token()
        if new:
            r = _post_batch(events)
        if r is None or r.status_code == 401:
            logger.error(
                "usage ingest 401: refresh the app session and pair again. Body: %s",
                (r.text if r is not None else "")[:200],
            )
            return
    try:
        r.raise_for_status()
    except Exception as exc:
        logger.warning("usage ingest failed: %s", exc)
        return
    _logged_waiting_for_pair = False


def http_writer_loop(job_queue):
    """Consume lists of usage-event dicts; POST batches to /api/usage-events/batch/."""
    batch = []
    last_flush = time.monotonic()

    def should_flush():
        if len(batch) >= BATCH_MAX_EVENTS:
            return True
        return (time.monotonic() - last_flush) >= BATCH_INTERVAL_SEC

    def flush():
        nonlocal batch, last_flush
        if not batch:
            return
        events = batch[:]
        batch = []
        last_flush = time.monotonic()
        _post_batch_with_retry(events)

    while True:
        timeout = max(0.05, BATCH_INTERVAL_SEC - (time.monotonic() - last_flush))
        try:
            msg = job_queue.get(timeout=timeout)
        except queue.Empty:
            msg = "__INTERVAL__"

        if msg is None:
            flush()
            break

        if msg == "__INTERVAL__":
            if batch:
                flush()
            last_flush = time.monotonic()
            continue

        if isinstance(msg, list):
            batch.extend(msg)
        if should_flush():
            flush()
            last_flush = time.monotonic()
