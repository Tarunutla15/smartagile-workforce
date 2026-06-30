"""
Uploader: runs the batched HTTP writer on a background thread.

Thin wrapper over the existing ``http_batch_writer`` (which POSTs to
``/api/usage-events/batch/`` with the paired JWT). The engine just calls ``put`` with a
list of event dicts and ``stop`` on shutdown.
"""

from __future__ import annotations

import logging
import queue
import threading

from http_batch_writer import http_writer_loop

logger = logging.getLogger(__name__)


class Uploader:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None
        self._stopping = False

    def _spawn(self) -> None:
        self._thread = threading.Thread(
            target=http_writer_loop, args=(self._queue,), name="smartagile-http-writer", daemon=False
        )
        self._thread.start()

    def start(self) -> None:
        self._stopping = False
        self._spawn()

    def _ensure_alive(self) -> None:
        """Restart the consumer if it ever stopped — uploads must never halt silently."""
        if self._stopping:
            return
        if self._thread is None or not self._thread.is_alive():
            logger.warning("http writer thread not alive; restarting uploader")
            self._spawn()

    def put(self, events: list) -> None:
        self._ensure_alive()
        self._queue.put(events)

    def stop(self, timeout: float = 60.0) -> None:
        self._stopping = True
        self._queue.put(None)  # sentinel: flush + exit
        if self._thread is not None:
            self._thread.join(timeout=timeout)
