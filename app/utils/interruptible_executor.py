"""Thread-pool support for interruptible, time-bounded network work."""

from __future__ import annotations

import threading
import weakref
from collections.abc import Callable, Iterable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FuturesTimeoutError
from concurrent.futures import thread as futures_thread
from typing import TypeVar

T = TypeVar("T")
R = TypeVar("R")

# Default budgets for market-data fan-out. Keep these short so a stuck Yahoo
# request cannot freeze Streamlit (or Ctrl+C) indefinitely.
DEFAULT_ITEM_TIMEOUT_SECONDS = 15.0
DEFAULT_OVERALL_TIMEOUT_SECONDS = 45.0


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


def call_with_timeout(
    func: Callable[[], T],
    *,
    timeout: float = DEFAULT_ITEM_TIMEOUT_SECONDS,
    default: T | None = None,
) -> T | None:
    """Run ``func`` in a daemon thread and abandon it after ``timeout``.

    yfinance ``.info`` and similar calls have no native timeout; this prevents
    a single hung HTTP request from blocking the caller forever.
    """
    box: dict[str, T] = {}
    error: dict[str, BaseException] = {}

    def target() -> None:
        try:
            box["value"] = func()
        except BaseException as exc:  # noqa: BLE001 — surface to caller thread
            error["error"] = exc

    worker = threading.Thread(target=target, daemon=True)
    worker.start()
    worker.join(timeout=timeout)

    if worker.is_alive():
        return default
    if "error" in error:
        return default
    return box.get("value", default)


def map_parallel(
    func: Callable[[T], R],
    items: Iterable[T],
    *,
    max_workers: int = 8,
    overall_timeout: float = DEFAULT_OVERALL_TIMEOUT_SECONDS,
    on_result: Callable[[R], None] | None = None,
) -> list[R]:
    """Map ``func`` over ``items`` with hard timeouts and Ctrl+C safety.

    Returns whatever completed before the overall deadline. Pending work is
    cancelled and workers are detached so the process can exit.
    """
    item_list = list(items)
    if not item_list:
        return []

    executor = InterruptibleThreadPoolExecutor(max_workers=max_workers)
    futures: dict[Future[R], T] = {}
    results: list[R] = []

    try:
        futures = {executor.submit(func, item): item for item in item_list}
        for future in as_completed(futures, timeout=overall_timeout):
            try:
                value = future.result(timeout=0)
            except Exception:
                continue
            results.append(value)
            if on_result is not None:
                on_result(value)
    except FuturesTimeoutError:
        for future in futures:
            future.cancel()
        executor.shutdown_now()
        return results
    except KeyboardInterrupt:
        for future in futures:
            future.cancel()
        executor.shutdown_now()
        raise
    else:
        # All submitted work finished (or raised). Do not wait on workers —
        # daemon threads must never block Streamlit/Ctrl+C shutdown.
        executor.shutdown(wait=False, cancel_futures=False)
        return results
