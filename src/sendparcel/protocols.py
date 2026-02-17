"""Framework integration protocols."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Shipment(Protocol):
    """Shipment shape expected by sendparcel core."""

    id: str
    status: str
    provider: str
    external_id: str
    tracking_number: str
    label_url: str


@runtime_checkable
class ShipmentRepository(Protocol):
    """Persistence abstraction for adapters."""

    async def get_by_id(self, shipment_id: str) -> Shipment: ...
    async def create(self, **kwargs) -> Shipment: ...
    async def save(self, shipment: Shipment) -> Shipment: ...
    async def update_status(
        self, shipment_id: str, status: str, **fields
    ) -> Shipment: ...
