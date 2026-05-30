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

import logging
from dataclasses import dataclass, field
from typing import Any

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import CommunicationError, ProviderCapabilityError
from sendparcel.flow import ShipmentFlow
from sendparcel.logging import get_logger
from sendparcel.protocols import ShipmentRepository
from sendparcel.registry import PluginRegistry
from sendparcel.types import (
    AddressInfo,
    CreateShipmentOutcome,
    ParcelInfo,
    ShipmentUpdateOutcome,
)

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
        self.max_concurrent = max_concurrent

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
        results: list[BatchResult] = []
        successful = 0
        failed = 0

        for i, shipment_data in enumerate(shipments):
            provider_slug = shipment_data.get("provider_slug")
            if not provider_slug:
                results.append(
                    BatchResult(
                        index=i,
                        success=False,
                        error="Missing provider_slug",
                    )
                )
                failed += 1
                continue

            try:
                # Validate provider exists
                self.registry.get_by_slug(provider_slug)

                # Create flow for this shipment
                flow = ShipmentFlow(
                    repository=self.repository,
                    config=self.config,
                    registry=self.registry,
                )

                # Create the shipment
                outcome = await flow.create_shipment(
                    provider_slug=provider_slug,
                    sender_address=shipment_data["sender_address"],
                    receiver_address=shipment_data["receiver_address"],
                    parcels=shipment_data["parcels"],
                    **{k: v for k, v in shipment_data.items()
                       if k not in ("provider_slug", "sender_address",
                                    "receiver_address", "parcels")},
                )

                results.append(
                    BatchResult(
                        index=i,
                        success=True,
                        shipment=outcome.shipment,
                        outcome=outcome,
                    )
                )
                successful += 1
                logger.info(
                    "Batch create: shipment %d created successfully "
                    "(provider=%s, tracking=%s)",
                    i,
                    provider_slug,
                    outcome.shipment.tracking_number,
                )

            except Exception as exc:
                results.append(
                    BatchResult(
                        index=i,
                        success=False,
                        error=str(exc),
                    )
                )
                failed += 1
                logger.warning(
                    "Batch create: shipment %d failed: %s",
                    i,
                    exc,
                )

        return BatchCreateResult(
            total=len(shipments),
            successful=successful,
            failed=failed,
            results=results,
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
        results: list[BatchResult] = []

        for i, shipment_id in enumerate(shipment_ids):
            try:
                shipment = await self.repository.get_by_id(shipment_id)
                flow = ShipmentFlow(
                    repository=self.repository,
                    config=self.config,
                    registry=self.registry,
                )
                outcome = await flow.fetch_and_update_status(shipment)
                results.append(
                    BatchResult(
                        index=i,
                        success=True,
                        shipment=outcome.shipment,
                        outcome=outcome,
                    )
                )
            except Exception as exc:
                results.append(
                    BatchResult(
                        index=i,
                        success=False,
                        error=str(exc),
                    )
                )

        return results

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
        results: list[BatchResult] = []

        for i, shipment_id in enumerate(shipment_ids):
            try:
                shipment = await self.repository.get_by_id(shipment_id)
                flow = ShipmentFlow(
                    repository=self.repository,
                    config=self.config,
                    registry=self.registry,
                )
                cancelled = await flow.cancel_shipment(shipment)
                results.append(
                    BatchResult(
                        index=i,
                        success=True,
                        shipment=shipment,
                        outcome={"cancelled": cancelled},
                    )
                )
            except Exception as exc:
                results.append(
                    BatchResult(
                        index=i,
                        success=False,
                        error=str(exc),
                    )
                )

        return results
