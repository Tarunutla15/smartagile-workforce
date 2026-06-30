"""
Tracking engine: the loop that ties the core trackers + plugins + uploader together.

Per poll it reads the foreground window, asks the plugin manager which enricher owns it,
and computes a stable activity key. When the key changes (or a periodic flush is due) it
closes the previous segment: computes active duration, snapshots input counters, runs the
matched plugin's ``enrich`` to build the event, and hands it to the uploader.

The previous monolithic ``track_application_usage`` lived in ``continous_task.py``; this is
the same logic, decomposed.
"""

from __future__ import annotations

import logging
import queue
import time
import uuid
from datetime import datetime, timezone

import auth_store

from ..plugins.base import Enrichment, RawWindow
from ..plugins.registry import PluginManager
from . import idle_tracker, ignore
from .classifier import Classifier
from .input_tracker import InputTracker
from .uploader import Uploader
from .window_tracker import WindowTracker

logger = logging.getLogger(__name__)


class TrackingEngine:
    def __init__(self, user_id: int) -> None:
        self.user_id = int(user_id)
        self._running = False
        self.classifier = Classifier()
        self.registry = PluginManager(self.classifier)
        self.input_tracker = InputTracker()
        self.window_tracker = WindowTracker()
        self.uploader = Uploader()

    # -- helpers ---------------------------------------------------------
    def _stable_key(self, raw: RawWindow | None, plugin):
        if raw is None or not raw.exe_path:
            return None
        if plugin is not None and plugin.splits_by_title:
            return (raw.exe_path, plugin.segment_title(raw) or "")
        return (raw.exe_path, "")

    def _wait_timeout(self, previous_raw, start_time) -> float:
        if not self._running:
            return 0.05
        if previous_raw is None:
            return max(0.1, idle_tracker.TITLE_REFRESH_SEC)
        rem = idle_tracker.PERIODIC_FLUSH_SEC - (time.time() - start_time)
        return max(0.15, min(idle_tracker.TITLE_REFRESH_SEC, rem))

    def _safe_enrich(self, raw: RawWindow, plugin) -> tuple[str, Enrichment]:
        """Run plugin.enrich with a hard fallback to the default app/browser behaviour."""
        source_type = getattr(plugin, "source_type", "application")
        try:
            enr = plugin.enrich(raw)
            if enr is not None:
                return source_type, enr
        except Exception as exc:  # noqa: BLE001
            logger.warning("plugin %s.enrich failed (%s); using fallback", getattr(plugin, "name", "?"), exc)
        # Fallback: reproduce original behaviour without the plugin.
        if source_type == "browser":
            title = self.classifier.normalize_browser_title(raw.window_title)
            return "browser", Enrichment(
                app=self.classifier.browser_software_name(raw.exe_path, title),
                activity=title,
                category=self.classifier.predict_browser_category(title),
            )
        return "application", Enrichment(
            app=self.classifier.app_software_name(raw.exe_path, raw.window_title),
            activity="(session)",
            category=self.classifier.predict_app_category(raw.exe_path),
        )

    def _flush_segment(self, raw: RawWindow, plugin, start_time: float) -> None:
        raw_spent = time.time() - start_time
        idle_raw = idle_tracker.seconds_since_last_input()
        effective = idle_tracker.effective_duration(raw_spent, idle_raw)
        ks, cl, sc = self.input_tracker.snapshot_and_reset()  # always reset (don't bleed)
        if effective < idle_tracker.MIN_SEGMENT_SEC:
            return
        # System / shell / lock-screen surfaces are not real usage -- drop (treat as away).
        if ignore.should_ignore(raw.exe_path, raw.window_title):
            return

        source_type, enr = self._safe_enrich(raw, plugin)
        occurred_iso = (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )
        name = (enr.app or "").strip() or "Unknown"
        context = enr.activity if enr.activity is not None else ""
        event = {
            "source_type": source_type,
            "name": name,
            "context": context,
            "category": str(enr.category or ""),
            "duration_seconds": float(effective),
            "idle_seconds": float(min(effective, float(idle_raw))),
            "keystrokes": float(ks),
            "clicks": float(cl),
            "scrolls": float(sc),
            "occurred_at": occurred_iso,
            # Stable per-segment id so a retried upload is idempotent server-side
            # (the backend de-dupes on (user, client_event_id)).
            "client_event_id": uuid.uuid4().hex,
            # Capture-time account: lets the uploader refuse to send this segment under a
            # different user if the PC is re-paired to another account before it flushes.
            # (Internal key; stripped before the request and ignored by the server anyway.)
            "_paired_user_id": auth_store.get_paired_user_id(),
        }
        # Optional extras (URL/domain). The ingest endpoint ignores unknown keys, so this
        # is forward-compatible without a backend migration.
        if enr.detail:
            url = enr.detail.get("url")
            domain = enr.detail.get("domain")
            if url:
                event["url"] = str(url)[:1024]
            if domain:
                event["domain"] = str(domain)[:256]

        self.uploader.put([event])

    # -- main loop -------------------------------------------------------
    def run(self) -> None:
        self._running = True
        self.input_tracker.start()
        self.window_tracker.start()
        self.uploader.start()
        logger.info(
            "Tracking engine started (user_id=%s). Foreground hook + idle tracking; batched HTTP upload.",
            self.user_id,
        )

        previous_raw: RawWindow | None = None
        previous_plugin = None
        previous_key = None
        start_time = time.time()

        try:
            while self._running:
                # Per-iteration guard: a transient error (COM hiccup, plugin edge case, a
                # bad foreground read) must never kill the tracking thread. Log and keep going.
                try:
                    try:
                        self.window_tracker.foreground_queue.get(
                            timeout=self._wait_timeout(previous_raw, start_time)
                        )
                    except queue.Empty:
                        pass
                    self.window_tracker.drain()

                    raw = self.window_tracker.read()
                    plugin = self.registry.match(raw) if raw is not None else None
                    current_key = self._stable_key(raw, plugin)

                    if current_key != previous_key:
                        if previous_raw is not None:
                            self._flush_segment(previous_raw, previous_plugin, start_time)
                        previous_raw = raw
                        previous_plugin = plugin
                        previous_key = current_key
                        start_time = time.time()
                    elif previous_raw is not None and (time.time() - start_time) >= idle_tracker.PERIODIC_FLUSH_SEC:
                        self._flush_segment(previous_raw, previous_plugin, start_time)
                        # Always advance so sustained idle does not keep growing one segment.
                        start_time = time.time()
                except Exception as exc:  # noqa: BLE001
                    logger.exception("tracking iteration error (continuing): %s", exc)
                    # Reset the segment so a half-built one is not mis-attributed, and avoid
                    # a tight error loop.
                    previous_raw = None
                    previous_plugin = None
                    previous_key = None
                    start_time = time.time()
                    time.sleep(0.5)
        except Exception as exc:  # noqa: BLE001 — should be unreachable now; last-resort log
            logger.exception("Tracking loop crashed: %s", exc)
        finally:
            self.input_tracker.stop()
            self.window_tracker.stop()
            self.uploader.stop()

    def stop(self) -> None:
        self._running = False
