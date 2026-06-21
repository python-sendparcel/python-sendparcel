"""Batch shipment operations for sendparcel.

Provides batch creation, status fetching, and cancellation of shipments.
Designed for efficiency when processing multiple shipments at once.

Usage::

    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repo, config=config)
    results = await batch.create_shipments(
        [
            {
                "provider_slug": "inpost-courier",
                "sender_address": {...},
                "receiver_address": {...},
                "parcels": [...],
            },
            # ... more shipments
        ]
    )
    for result in results:
        if result.success:
            print(f"Created {result.shipment.tracking_number}")
        else:
            print(f"Failed: {result.error}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sendparcel.concurrent import ConcurrentExecutor
from sendparcel.flow import ShipmentFlow
from sendparcel.logging import get_logger
from sendparcel.protocols import ShipmentRepository
from sendparcel.registry import PluginRegistry

logger = get_logger(__name__)


@dataclass
class BatchResult:
    """Result of a single batch operation."""

    index: int
    success: bool
    shipment: Any | None = None
    error: str | None = None
    outcome: Any | None = None


@dataclass
class BatchCreateResult:
    """Result of a batch create operation."""

    total: int
    successful: int
    failed: int
    results: list[BatchResult] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """True if all shipments were created successfully."""
        return self.failed == 0

    @property
    def summary(self) -> dict[str, Any]:
        """Return a summary of the batch operation."""
        return {
            "total": self.total,
            "successful": self.successful,
            "failed": self.failed,
            "success_rate": (
                round(self.successful / self.total * 100, 2)
                if self.total > 0
                else 0.0
            ),
        }


class ShipmentBatch:
    """Batch shipment operations.

    Provides efficient batch creation, status fetching, and cancellation
    of shipments. All operations are atomic within the batch — if one
    shipment fails, the others are still processed.

    Args:
        repository: Shipment repository for persisting results.
        config: Provider configuration.
        registry: Provider registry (defaults to module-level singleton).
        max_concurrent: Maximum number of concurrent provider calls
            (default: 5).
    """

    def __init__(
        self,
        repository: ShipmentRepository,
        config: dict[str, Any] | None = None,
        registry: PluginRegistry | None = None,
        max_concurrent: int = 5,
    ) -> None:
        self.repository = repository
        self.config = config or {}
        self.registry = registry or PluginRegistry()
        self._executor = ConcurrentExecutor(max_concurrent)

    async def create_shipments(
        self,
        shipments: list[dict[str, Any]],
    ) -> BatchCreateResult:
        """Create multiple shipments in a batch.

        Each shipment dict must contain:
        - provider_slug: Provider identifier
        - sender_address: Sender address info
        - receiver_address: Receiver address info
        - parcels: List of parcel definitions
        - Optional: idempotency_key, reference_id, and other kwargs

        Args:
            shipments: List of shipment dicts to create.

        Returns:
            BatchCreateResult with per-shipment results.
        """
        async def _create_one(data: dict[str, Any], index: int) -> BatchResult:
            return await self._create_single_shipment(index, data)

        results = await self._executor.execute(shipments, _create_one)
        
        # Convert ConcurrentResult to BatchResult
        batch_results = []
        for res in results:
            if res.success:
                batch_result = res.value
            else:
                batch_result = BatchResult(
                    index=res.index,
                    success=False,
                    error=res.error,
                )
            batch_results.append(batch_result)

        successful = sum(1 for r in batch_results if r.success)
        failed = sum(1 for r in batch_results if not r.success)

        return BatchCreateResult(
            total=len(shipments),
            successful=successful,
            failed=failed,
            results=batch_results,
        )

    async def _create_single_shipment(
        self, index: int, shipment_data: dict[str, Any]
    ) -> BatchResult:
        provider_slug = shipment_data.get("provider_slug")
        if not provider_slug:
            return BatchResult(
                index=index,
                success=False,
                error="Missing provider_slug",
            )

        try:
            self.registry.get_by_slug(provider_slug)

            flow = ShipmentFlow(
                repository=self.repository,
                config=self.config,
                registry=self.registry,
            )

            outcome = await flow.create_shipment(
                provider_slug=provider_slug,
                sender_address=shipment_data["sender_address"],
                receiver_address=shipment_data["receiver_address"],
                parcels=shipment_data["parcels"],
                **{
                    k: v
                    for k, v in shipment_data.items()
                    if k
                    not in (
                        "provider_slug",
                        "sender_address",
                        "receiver_address",
                        "parcels",
                    )
                },
            )

            logger.info(
                "Batch create: shipment %d created successfully "
                "(provider=%s, tracking=%s)",
                index,
                provider_slug,
                outcome.shipment.tracking_number,
            )

            return BatchResult(
                index=index,
                success=True,
                shipment=outcome.shipment,
                outcome=outcome,
            )

        except Exception as exc:
            logger.warning(
                "Batch create: shipment %d failed: %s",
                index,
                exc,
            )
            return BatchResult(
                index=index,
                success=False,
                error=str(exc),
            )

    async def fetch_statuses(
        self,
        shipment_ids: list[str],
    ) -> list[BatchResult]:
        """Fetch statuses for multiple shipments.

        Args:
            shipment_ids: List of shipment IDs to fetch.

        Returns:
            List of BatchResult with per-shipment status updates.
        """
        async def _fetch_one(sid: str, index: int) -> BatchResult:
            try:
                shipment = await self.repository.get_by_id(sid)
                flow = ShipmentFlow(
                    repository=self.repository,
                    config=self.config,
                    registry=self.registry,
                )
                outcome = await flow.fetch_and_update_status(shipment)
                return BatchResult(
                    index=index,
                    success=True,
                    shipment=outcome.shipment,
                    outcome=outcome,
                )
            except Exception as exc:
                return BatchResult(
                    index=index,
                    success=False,
                    error=str(exc),
                )

        results = await self._executor.execute(shipment_ids, _fetch_one)
        
        # Convert ConcurrentResult to BatchResult
        batch_results = []
        for res in results:
            if res.success:
                batch_result = res.value
            else:
                batch_result = BatchResult(
                    index=res.index,
                    success=False,
                    error=res.error,
                )
            batch_results.append(batch_result)
        
        return batch_results

    async def cancel_shipments(
        self,
        shipment_ids: list[str],
    ) -> list[BatchResult]:
        """Cancel multiple shipments.

        Args:
            shipment_ids: List of shipment IDs to cancel.

        Returns:
            List of BatchResult with per-shipment cancellation results.
        """
        async def _cancel_one(sid: str, index: int) -> BatchResult:
            try:
                shipment = await self.repository.get_by_id(sid)
                flow = ShipmentFlow(
                    repository=self.repository,
                    config=self.config,
                    registry=self.registry,
                )
                cancelled = await flow.cancel_shipment(shipment)
                return BatchResult(
                    index=index,
                    success=True,
                    shipment=shipment,
                    outcome={"cancelled": cancelled},
                )
            except Exception as exc:
                return BatchResult(
                    index=index,
                    success=False,
                    error=str(exc),
                )

        results = await self._executor.execute(shipment_ids, _cancel_one)
        
        # Convert ConcurrentResult to BatchResult
        batch_results = []
        for res in results:
            if res.success:
                batch_result = res.value
            else:
                batch_result = BatchResult(
                    index=res.index,
                    success=False,
                    error=res.error,
                )
            batch_results.append(batch_result)
        
        return batch_results