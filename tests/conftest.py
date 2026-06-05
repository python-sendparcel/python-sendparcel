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
    reference_id: str = ""


class InMemoryRepository:
    """Minimal async repository used by flow tests."""

    def __init__(self) -> None:
        self._store: dict[str, Shipment] = {}
        self.save_count = 0
        self.update_fields_count = 0
        self.create_count = 0

    def get_by_id_sync(
        self, shipment_id: str, *, for_update: bool = False
    ) -> Shipment:
        if shipment_id not in self._store:
            raise ShipmentNotFoundError(shipment_id)
        return self._store[shipment_id]

    async def get_by_id(
        self, shipment_id: str, *, for_update: bool = False
    ) -> Shipment:
        if shipment_id not in self._store:
            raise ShipmentNotFoundError(shipment_id)
        return self._store[shipment_id]

    async def create(self, **kwargs: Any) -> Shipment:
        self.create_count += 1
        shipment = DemoShipment(
            id=str(kwargs.get("id", "shipment-1")),
            provider=kwargs["provider"],
            status=kwargs.get("status", "new"),
            external_id=str(kwargs.get("external_id", "")),
            tracking_number=str(kwargs.get("tracking_number", "")),
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

    async def create_with_idempotency_key(
        self,
        provider: str,
        status: str,
        reference_id: str,
        **kwargs: Any,
    ) -> tuple[Shipment | None, Shipment | None]:
        """Atomically check for existing + create if absent."""
        for existing in self._store.values():
            if getattr(existing, "reference_id", None) == reference_id:
                return (existing, None)
        self.create_count += 1
        shipment = DemoShipment(
            id=str(kwargs.get("id", f"shipment-{self.create_count}")),
            provider=provider,
            status=status,
            reference_id=reference_id,
        )
        self._store[shipment.id] = shipment
        return (None, shipment)

    async def update_fields(self, shipment_id: str, **fields: Any) -> Shipment:
        """Atomically update shipment fields by ID."""
        if shipment_id not in self._store:
            raise ShipmentNotFoundError(shipment_id)
        shipment = self._store[shipment_id]
        for key, value in fields.items():
            setattr(shipment, key, value)
        self.update_fields_count += 1
        return shipment

    async def find_by_reference(
        self, provider: str, reference_id: str
    ) -> Shipment | None:
        for existing in self._store.values():
            if getattr(existing, "reference_id", None) == reference_id:
                return existing
        return None

    async def delete(self, shipment_id: str) -> None:
        self._store.pop(shipment_id, None)


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
