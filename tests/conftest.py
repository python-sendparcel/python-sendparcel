"""Shared test fixtures for sendparcel core."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal

import pytest

from sendparcel.registry import registry


@dataclass
class DemoOrder:
    """Minimal order protocol implementation for tests."""

    def get_total_weight(self) -> Decimal:
        return Decimal("1.0")

    def get_parcels(self) -> list[dict]:
        return []

    def get_sender_address(self) -> dict:
        return {}

    def get_receiver_address(self) -> dict:
        return {}


@dataclass
class DemoShipment:
    """Minimal shipment protocol implementation for tests."""

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
        self.saved: list[DemoShipment] = []

    async def get_by_id(self, shipment_id: str) -> DemoShipment:
        return DemoShipment(id=shipment_id)

    async def create(self, **kwargs) -> DemoShipment:
        shipment = DemoShipment(
            order=kwargs["order"],
            provider=kwargs["provider"],
            status=kwargs.get("status", "new"),
        )
        self.saved.append(shipment)
        return shipment

    async def save(self, shipment: DemoShipment) -> DemoShipment:
        self.saved.append(shipment)
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields
    ) -> DemoShipment:
        shipment = DemoShipment(id=shipment_id, status=status)
        for key, value in fields.items():
            setattr(shipment, key, value)
        self.saved.append(shipment)
        return shipment


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
