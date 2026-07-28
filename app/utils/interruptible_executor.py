"""Thread-pool support for interruptible network work."""

from __future__ import annotations

import threading
import weakref
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import thread as futures_thread


class InterruptibleThreadPoolExecutor(ThreadPoolExecutor):
    """Thread pool whose workers do not block interpreter shutdown."""

    def _adjust_thread_count(self) -> None:
        if self._idle_semaphore.acquire(timeout=0):
            return

        def weakref_callback(
            _, work_queue=self._work_queue
        ) -> None:
            work_queue.put(None)

        if len(self._threads) >= self._max_workers:
            return

        worker = threading.Thread(
            name=f"{self._thread_name_prefix or self}_{len(self._threads)}",
            target=futures_thread._worker,
            args=(
                weakref.ref(self, weakref_callback),
                self._work_queue,
                self._initializer,
                self._initargs,
            ),
            daemon=True,
        )
        worker.start()
        self._threads.add(worker)
        futures_thread._threads_queues[worker] = self._work_queue

    def shutdown_now(self) -> None:
        """Cancel pending work and detach active workers during interruption."""
        self.shutdown(wait=False, cancel_futures=True)
        for worker in self._threads:
            futures_thread._threads_queues.pop(worker, None)
