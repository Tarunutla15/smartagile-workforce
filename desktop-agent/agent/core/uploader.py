"""
Uploader: runs the batched HTTP writer on a background thread.

Thin wrapper over the existing ``http_batch_writer`` (which POSTs to
``/api/usage-events/batch/`` with the paired JWT). The engine just calls ``put`` with a
list of event dicts and ``stop`` on shutdown.
"""

from __future__ import annotations

import queue
import threading

from http_batch_writer import http_writer_loop


class Uploader:
    def __init__(self) -> None:
        self._queue: queue.Queue = queue.Queue()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=http_writer_loop, args=(self._queue,), name="smartagile-http-writer", daemon=False
        )
        self._thread.start()

    def put(self, events: list) -> None:
        self._queue.put(events)

    def stop(self, timeout: float = 60.0) -> None:
        self._queue.put(None)  # sentinel: flush + exit
        if self._thread is not None:
            self._thread.join(timeout=timeout)
