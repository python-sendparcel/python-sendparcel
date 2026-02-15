"""Shared test fixtures for sendparcel core."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from sendparcel.registry import registry
from sendparcel.types import AddressInfo, ParcelInfo


@dataclass
class DemoOrder:
    """Configurable order protocol implementation for tests."""

    weight: Decimal = Decimal("1.0")
    parcels: list[ParcelInfo] | None = None
    sender_address: AddressInfo | None = None
    receiver_address: AddressInfo | None = None

    def get_total_weight(self) -> Decimal:
        return self.weight

    def get_parcels(self) -> list[ParcelInfo]:
        if self.parcels is not None:
            return self.parcels
        return [ParcelInfo(weight_kg=self.weight)]

    def get_sender_address(self) -> AddressInfo:
        if self.sender_address is not None:
            return self.sender_address
        return AddressInfo(
            name="Test Sender",
            line1="Sender St 1",
            city="Warsaw",
            postal_code="00-001",
            country_code="PL",
        )

    def get_receiver_address(self) -> AddressInfo:
        if self.receiver_address is not None:
            return self.receiver_address
        return AddressInfo(
            name="Test Receiver",
            line1="Receiver St 2",
            city="Berlin",
            postal_code="10115",
            country_code="DE",
        )


@dataclass
class DemoShipment:
    """Configurable shipment protocol implementation for tests."""

    id: str = "shipment-1"
    order: DemoOrder = field(default_factory=DemoOrder)
    status: str = "new"
    provider: str = ""
    external_id: str = ""
    tracking_number: str = ""
    label_url: str = ""


class InMemoryRepository:
    """Minimal async repository used by flow tests."""

    def __init__(self) -> None:
        self._store: dict[str, DemoShipment] = {}
        self.save_count: int = 0

    async def get_by_id(self, shipment_id: str) -> DemoShipment:
        if shipment_id not in self._store:
            raise KeyError(f"Shipment {shipment_id!r} not found")
        return self._store[shipment_id]

    async def create(self, **kwargs) -> DemoShipment:
        shipment = DemoShipment(
            order=kwargs["order"],
            provider=kwargs["provider"],
            status=kwargs.get("status", "new"),
        )
        self._store[shipment.id] = shipment
        return shipment

    async def save(self, shipment: DemoShipment) -> DemoShipment:
        self._store[shipment.id] = shipment
        self.save_count += 1
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields
    ) -> DemoShipment:
        shipment = self._store.get(shipment_id, DemoShipment(id=shipment_id))
        shipment.status = status
        for key, value in fields.items():
            setattr(shipment, key, value)
        self._store[shipment_id] = shipment
        return shipment


@pytest.fixture
def demo_order() -> DemoOrder:
    return DemoOrder()


@pytest.fixture
def demo_shipment() -> DemoShipment:
    return DemoShipment()


@pytest.fixture
def repository() -> InMemoryRepository:
    return InMemoryRepository()


@pytest.fixture(autouse=True)
def isolate_global_registry() -> Iterator[None]:
    """Reset global registry state between tests."""
    old_providers = dict(registry._providers)
    old_discovered = registry._discovered
    registry._providers = {}
    registry._discovered = True
    try:
        yield
    finally:
        registry._providers = old_providers
        registry._discovered = old_discovered
