"""Batch shipment operation tests."""

from __future__ import annotations

from typing import Any

import pytest
from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import ShipmentNotFoundError
from sendparcel.logging import get_logger
from sendparcel.protocols import Shipment, ShipmentRepository
from sendparcel.registry import PluginRegistry
from sendparcel.provider import CancellableProvider, PullStatusProvider
from sendparcel.types import (
    AddressInfo,
    CreateShipmentOutcome,
    ParcelInfo,
    ShipmentUpdateOutcome,
    ShipmentUpdateResult,
)

logger = get_logger(__name__)


class MockShipment:
    """Mock shipment for testing."""

    def __init__(
        self,
        id: str = "1",
        status: str = "new",
        provider: str = "dummy",
        external_id: str = "",
        tracking_number: str = "",
    ) -> None:
        self.id = id
        self.status = status
        self.provider = provider
        self.external_id = external_id
        self.tracking_number = tracking_number


class MockRepository(ShipmentRepository):
    """Mock repository for testing batch operations."""

    def __init__(self) -> None:
        self._shipments: dict[str, Shipment] = {}
        self._counter = 0

    async def get_by_id(self, shipment_id: str) -> Shipment:
        if shipment_id not in self._shipments:
            raise ShipmentNotFoundError(shipment_id)
        return self._shipments[shipment_id]

    async def create(self, **kwargs: Any) -> Shipment:
        self._counter += 1
        shipment = MockShipment(
            id=str(self._counter),
            status="new",
            provider=kwargs.get("provider", "dummy"),
        )
        self._shipments[shipment.id] = shipment
        return shipment

    async def save(self, shipment: Shipment) -> Shipment:
        self._shipments[shipment.id] = shipment
        return shipment

    async def delete(self, shipment_id: str) -> None:
        self._shipments.pop(shipment_id, None)

    async def update_status(
        self, shipment_id: str, status: str, **fields: Any
    ) -> Shipment:
        if shipment_id not in self._shipments:
            raise ShipmentNotFoundError(shipment_id)
        shipment = self._shipments[shipment_id]
        shipment.status = status
        for key, value in fields.items():
            setattr(shipment, key, value)
        return shipment

    async def find_by_reference(
        self, provider: str, reference_id: str
    ) -> Shipment | None:
        for shipment in self._shipments.values():
            if (
                shipment.provider == provider
                and getattr(shipment, "reference_id", None) == reference_id
            ):
                return shipment
        return None


class DummyProvider(CancellableProvider, PullStatusProvider):
    """Mock provider for testing."""

    slug = "test-dummy"
    display_name = "Test Dummy"
    supported_countries = ["PL"]
    confirmation_method = "push"
    user_selectable = True

    def __init__(
        self,
        shipment: Any,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.shipment = shipment
        self.config = config or {}

    @classmethod
    def config_schema(cls) -> dict[str, Any]:
        return {}

    @classmethod
    def get_setting(cls, key: str, default: Any = None) -> Any:
        return cls.config.get(key, default) if hasattr(cls, "config") else default

    @classmethod
    async def create_shipment(
        cls,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> dict[str, Any]:
        return {"external_id": "ext-1", "tracking_number": "TRK-123"}

    @classmethod
    async def verify_callback(
        cls, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        pass

    @classmethod
    async def handle_callback(
        cls, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> ShipmentUpdateResult:
        return {"status": ShipmentStatus.IN_TRANSIT}

    @classmethod
    async def fetch_shipment_status(cls, **kwargs: Any) -> ShipmentUpdateResult:
        return {"status": ShipmentStatus.CREATED}

    @classmethod
    async def cancel_shipment(cls, **kwargs: Any) -> bool:
        return True


@pytest.fixture
def registry():
    """Create a registry with the dummy provider."""
    from sendparcel.registry import PluginRegistry

    reg = PluginRegistry()
    reg.register(DummyProvider)
    return reg


@pytest.fixture
def repository():
    """Create a mock repository."""
    return MockRepository()


async def test_create_shipments_single_success(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test creating a single shipment in a batch."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {"name": "Receiver", "country_code": "PL"},
                "parcels": [{"weight": 1.0}],
            }
        ]
    )

    assert results.total == 1
    assert results.successful == 1
    assert results.failed == 0
    assert results.success
    assert results.results[0].success
    assert results.results[0].shipment is not None
    assert results.results[0].shipment.tracking_number == "TRK-123"


async def test_create_shipments_multiple_success(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test creating multiple shipments in a batch."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {"name": "Receiver", "country_code": "PL"},
                "parcels": [{"weight": 1.0}],
            },
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {"name": "Receiver", "country_code": "PL"},
                "parcels": [{"weight": 2.0}],
            },
        ]
    )

    assert results.total == 2
    assert results.successful == 2
    assert results.failed == 0
    assert results.success


async def test_create_shipments_with_missing_provider(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test batch creation with missing provider slug."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {"name": "Receiver", "country_code": "PL"},
                "parcels": [{"weight": 1.0}],
            }
        ]
    )

    assert results.total == 1
    assert results.successful == 0
    assert results.failed == 1
    assert not results.success
    assert results.results[0].error == "Missing provider_slug"


async def test_create_shipments_with_invalid_provider(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test batch creation with invalid provider."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "provider_slug": "nonexistent",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            }
        ]
    )

    assert results.total == 1
    assert results.successful == 0
    assert results.failed == 1
    assert not results.success
    assert "nonexistent" in (results.results[0].error or "")


async def test_create_shipments_partial_failure(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test batch creation where some shipments fail."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            },
            {
                "provider_slug": "nonexistent",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            },
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            },
        ]
    )

    assert results.total == 3
    assert results.successful == 2
    assert results.failed == 1
    assert not results.success


async def test_fetch_statuses(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test fetching statuses for multiple shipments."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    # Create some shipments first
    shipment1 = await repository.create(
        provider="test-dummy", status=ShipmentStatus.NEW.value
    )
    shipment2 = await repository.create(
        provider="test-dummy", status=ShipmentStatus.NEW.value
    )

    results = await batch.fetch_statuses([shipment1.id, shipment2.id])

    assert len(results) == 2
    for r in results:
        if not r.success:
            logger.error("Fetch status failed: %s", r.error)
    assert all(r.success for r in results)
    assert all(r.shipment is not None for r in results)


async def test_cancel_shipments(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test cancelling multiple shipments."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    # Create some shipments first
    shipment1 = await repository.create(
        provider="test-dummy", status=ShipmentStatus.NEW.value
    )
    shipment2 = await repository.create(
        provider="test-dummy", status=ShipmentStatus.NEW.value
    )

    results = await batch.cancel_shipments([shipment1.id, shipment2.id])

    assert len(results) == 2
    for r in results:
        if not r.success:
            logger.error("Cancel failed: %s", r.error)
    assert all(r.success for r in results)
    assert all(r.shipment is not None for r in results)


async def test_batch_result_summary(
    registry: PluginRegistry, repository: MockRepository
) -> None:
    """Test the summary property of BatchCreateResult."""
    from sendparcel.batch import ShipmentBatch

    batch = ShipmentBatch(repository=repository, registry=registry)

    results = await batch.create_shipments(
        [
            {
                "provider_slug": "test-dummy",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            },
            {
                "provider_slug": "nonexistent",
                "sender_address": {"name": "Sender", "country_code": "PL"},
                "receiver_address": {
                    "name": "Receiver",
                    "country_code": "PL",
                },
                "parcels": [{"weight": 1.0}],
            },
        ]
    )

    summary = results.summary
    assert summary["total"] == 2
    assert summary["successful"] == 1
    assert summary["failed"] == 1
    assert summary["success_rate"] == 50.0
