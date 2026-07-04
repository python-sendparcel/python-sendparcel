"""Generic concurrent executor with semaphore-based concurrency control."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, TypeVar

import anyio

T = TypeVar("T")


@dataclass
class ConcurrentResult:
    """Result of a single concurrent operation."""

    index: int
    success: bool
    value: Any = None
    error: str | None = None


class ConcurrentExecutor:
    """Executes async callables with bounded concurrency.

    Backend-agnostic: uses anyio primitives, so it runs under both
    asyncio and trio.
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        self._max_concurrent = max_concurrent

    async def execute(
        self,
        items: list[Any],
        operation: Callable[[Any, int], Coroutine[Any, Any, T]],
    ) -> list[ConcurrentResult]:
        """Execute operation on each item with bounded concurrency.

        Args:
            items: List of items to process.
            operation: Async callable(item, index) -> result.

        Returns:
            List of ConcurrentResult in the same order as items.
        """
        semaphore = anyio.Semaphore(self._max_concurrent)
        results: list[ConcurrentResult | None] = [None] * len(items)

        async def _run(index: int, item: Any) -> None:
            async with semaphore:
                try:
                    value = await operation(item, index)
                    results[index] = ConcurrentResult(
                        index=index,
                        success=True,
                        value=value,
                    )
                except Exception as exc:
                    results[index] = ConcurrentResult(
                        index=index,
                        success=False,
                        error=str(exc),
                    )

        async with anyio.create_task_group() as tg:
            for i, item in enumerate(items):
                tg.start_soon(_run, i, item)

        return [r for r in results if r is not None]
