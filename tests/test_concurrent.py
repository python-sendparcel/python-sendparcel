"""Tests for ConcurrentExecutor."""

from __future__ import annotations

import asyncio
from typing import Any

from sendparcel.concurrent import ConcurrentExecutor, ConcurrentResult


async def test_concurrent_executes_all() -> None:
    """Test that all tasks are executed and results returned."""
    executor = ConcurrentExecutor(max_concurrent=3)

    async def square(item: int, index: int) -> int:
        await asyncio.sleep(0.01)  # Small delay to simulate work
        return item * item

    items = [1, 2, 3, 4, 5]
    results = await executor.execute(items, square)

    assert len(results) == 5
    assert all(isinstance(r, ConcurrentResult) for r in results)
    assert all(r.success for r in results)
    assert [r.value for r in results] == [1, 4, 9, 16, 25]


async def test_concurrent_respects_max_concurrency() -> None:
    """Test that never more than N tasks run simultaneously."""
    max_concurrent = 2
    executor = ConcurrentExecutor(max_concurrent=max_concurrent)

    concurrent_count = 0
    max_seen = 0

    async def track_concurrency(item: int, index: int) -> int:
        nonlocal concurrent_count, max_seen

        concurrent_count += 1
        max_seen = max(max_seen, concurrent_count)

        await asyncio.sleep(0.1)  # Hold the semaphore for a while

        concurrent_count -= 1
        return item

    items = [1, 2, 3, 4, 5, 6]  # More items than max_concurrent
    results = await executor.execute(items, track_concurrency)

    assert len(results) == 6
    assert all(r.success for r in results)
    assert max_seen <= max_concurrent


async def test_concurrent_preserves_order() -> None:
    """Test that results are in the same order as inputs."""
    executor = ConcurrentExecutor(max_concurrent=3)

    async def delayed_identity(item: int, index: int) -> int:
        # Introduce variable delays - later items finish first
        delay = 0.1 - (index * 0.01)
        await asyncio.sleep(delay)
        return item

    items = [10, 20, 30, 40, 50]
    results = await executor.execute(items, delayed_identity)

    assert len(results) == 5
    assert all(r.success for r in results)
    # Results should be in original order despite variable completion times
    assert [r.value for r in results] == [10, 20, 30, 40, 50]
    # Verify indices are correct
    assert [r.index for r in results] == [0, 1, 2, 3, 4]


async def test_concurrent_captures_errors() -> None:
    """Test that exceptions are captured in results, not raised."""
    executor = ConcurrentExecutor(max_concurrent=3)

    async def maybe_fail(item: int, index: int) -> int:
        if item % 2 == 0:
            raise ValueError(f"Even number: {item}")
        return item * 2

    items = [1, 2, 3, 4, 5]

    # Should not raise any exceptions
    results = await executor.execute(items, maybe_fail)

    assert len(results) == 5

    # Check successful results (odd numbers)
    for i, result in enumerate(results):
        if items[i] % 2 == 1:  # Odd number - should succeed
            assert result.success
            assert result.value == items[i] * 2
            assert result.error is None
        else:  # Even number - should fail
            assert not result.success
            assert result.value is None
            assert result.error == f"Even number: {items[i]}"
            assert result.index == i


async def test_concurrent_empty_input() -> None:
    """Test that empty input returns empty list."""
    executor = ConcurrentExecutor(max_concurrent=5)

    async def dummy_operation(item: Any, index: int) -> Any:
        return item

    results = await executor.execute([], dummy_operation)

    assert results == []


async def test_concurrent_result_index_tracking() -> None:
    """Test that result indices correctly track original positions."""
    executor = ConcurrentExecutor(max_concurrent=2)

    async def return_index(item: str, index: int) -> tuple[str, int]:
        await asyncio.sleep(0.01)
        return (item, index)

    items = ["a", "b", "c", "d"]
    results = await executor.execute(items, return_index)

    assert len(results) == 4
    for i, result in enumerate(results):
        assert result.success
        assert result.index == i
        assert result.value == (items[i], i)


def test_concurrent_runs_on_trio_backend() -> None:
    """The library advertises anyio portability; the executor must work
    under the trio backend, not just asyncio."""
    import anyio

    async def main() -> list[ConcurrentResult]:
        executor = ConcurrentExecutor(max_concurrent=2)

        async def double(item: int, index: int) -> int:
            await anyio.sleep(0.001)
            return item * 2

        return await executor.execute([1, 2, 3], double)

    results = anyio.run(main, backend="trio")

    assert [r.value for r in results] == [2, 4, 6]
    assert all(r.success for r in results)


async def test_concurrent_single_item() -> None:
    """Test behavior with a single item."""
    executor = ConcurrentExecutor(max_concurrent=5)

    async def increment(item: int, index: int) -> int:
        return item + 1

    results = await executor.execute([42], increment)

    assert len(results) == 1
    assert results[0].success
    assert results[0].value == 43
    assert results[0].index == 0
