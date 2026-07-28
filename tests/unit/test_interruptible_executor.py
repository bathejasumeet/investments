"""Unit tests for interruptible / time-bounded parallel helpers."""

from __future__ import annotations

import threading
import time

import pytest

from app.utils.interruptible_executor import (
    call_with_timeout,
    map_parallel,
)


@pytest.mark.unit
class TestCallWithTimeout:
    """Tests for abandoning hung callables."""

    def test_returns_value_when_fast(self) -> None:
        assert call_with_timeout(lambda: 42, timeout=1.0) == 42

    def test_returns_default_when_callable_hangs(self) -> None:
        started = threading.Event()

        def hang() -> int:
            started.set()
            time.sleep(30)
            return 1

        t0 = time.monotonic()
        result = call_with_timeout(hang, timeout=0.2, default=None)
        elapsed = time.monotonic() - t0

        assert started.wait(1.0)
        assert result is None
        assert elapsed < 2.0

    def test_returns_default_on_exception(self) -> None:
        def boom() -> int:
            raise RuntimeError("network")

        assert call_with_timeout(boom, timeout=1.0, default=-1) == -1


@pytest.mark.unit
class TestMapParallel:
    """Tests for bounded parallel map used by recommendations."""

    def test_maps_all_items(self) -> None:
        assert sorted(map_parallel(lambda x: x * 2, [1, 2, 3])) == [2, 4, 6]

    def test_empty_input_returns_empty(self) -> None:
        assert map_parallel(lambda x: x, []) == []

    def test_overall_timeout_returns_partial_results(self) -> None:
        release_fast = threading.Event()
        release_fast.set()

        def work(item: str) -> str:
            if item == "slow":
                time.sleep(30)
            return item

        t0 = time.monotonic()
        results = map_parallel(
            work,
            ["fast1", "slow", "fast2"],
            max_workers=3,
            overall_timeout=0.4,
        )
        elapsed = time.monotonic() - t0

        assert "slow" not in results
        assert set(results) <= {"fast1", "fast2"}
        assert elapsed < 3.0

    def test_on_result_callback_invoked(self) -> None:
        seen: list[int] = []
        map_parallel(
            lambda x: x + 1,
            [1, 2, 3],
            on_result=seen.append,
        )
        assert sorted(seen) == [2, 3, 4]

    def test_swallows_item_exceptions(self) -> None:
        def flaky(item: int) -> int:
            if item == 2:
                raise RuntimeError("boom")
            return item

        # Exceptions inside the future are skipped by map_parallel.
        assert sorted(map_parallel(flaky, [1, 2, 3])) == [1, 3]
