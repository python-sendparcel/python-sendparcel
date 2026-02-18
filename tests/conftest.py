"""Shared test fixtures for sendparcel core."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import pytest

from sendparcel.exceptions import ShipmentNotFoundError
from sendparcel.protocols import Shipment
from sendparcel.registry import registry


@dataclass
class DemoShipment:
    """Configurable shipment protocol implementation for tests."""

    id: str = "shipment-1"
    status: str = "new"
    provider: str = ""
    external_id: str = ""
    tracking_number: str = ""
    label_url: str = ""


class InMemoryRepository:
    """Minimal async repository used by flow tests."""

    def __init__(self) -> None:
        self._store: dict[str, Shipment] = {}
        self.save_count: int = 0

    async def get_by_id(self, shipment_id: str) -> Shipment:
        if shipment_id not in self._store:
            raise ShipmentNotFoundError(shipment_id)
        return self._store[shipment_id]

    async def create(self, **kwargs: Any) -> Shipment:
        shipment = DemoShipment(
            provider=kwargs["provider"],
            status=kwargs.get("status", "new"),
        )
        self._store[shipment.id] = shipment
        return shipment

    async def save(self, shipment: Shipment) -> Shipment:
        self._store[shipment.id] = shipment
        self.save_count += 1
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields: Any
    ) -> Shipment:
        shipment = self._store.get(shipment_id, DemoShipment(id=shipment_id))
        shipment.status = status
        for key, value in fields.items():
            setattr(shipment, key, value)
        self._store[shipment_id] = shipment
        return shipment


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
