"""Generic concurrent executor with semaphore-based concurrency control."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, TypeVar

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
    
    Replaces the semaphore pattern in ShipmentBatch with a generic
    reusable primitive.
    """
    
    def __init__(self, max_concurrent: int = 5) -> None:
        self._semaphore = asyncio.Semaphore(max_concurrent)
    
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
        async def _run(index: int, item: Any) -> ConcurrentResult:
            async with self._semaphore:
                try:
                    value = await operation(item, index)
                    return ConcurrentResult(
                        index=index,
                        success=True,
                        value=value,
                    )
                except Exception as exc:
                    return ConcurrentResult(
                        index=index,
                        success=False,
                        error=str(exc),
                    )
        
        results = await asyncio.gather(
            *(_run(i, item) for i, item in enumerate(items))
        )
        results.sort(key=lambda r: r.index)
        return results