"""Framework integration protocols."""

from typing import Any, Protocol


class Shipment(Protocol):
    """Shipment shape expected by sendparcel core."""

    id: str
    status: str
    provider: str
    external_id: str
    tracking_number: str


class ShipmentRepository(Protocol):
    """Persistence abstraction for adapters."""

    async def get_by_id(self, shipment_id: str) -> Shipment: ...
    async def create(self, **kwargs: Any) -> Shipment: ...
    async def save(self, shipment: Shipment) -> Shipment: ...
    async def update_status(
        self, shipment_id: str, status: str, **fields: Any
    ) -> Shipment: ...
    async def delete(self, shipment_id: str) -> None: ...
    async def find_by_reference(
        self, provider: str, reference_id: str
    ) -> Shipment | None: ...
