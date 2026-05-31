"""Framework integration protocols."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Shipment(Protocol):
    """Shipment shape expected by sendparcel core."""

    id: str
    status: str
    provider: str
    external_id: str
    tracking_number: str


@runtime_checkable
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
    async def create_with_idempotency_key(
        self,
        provider: str,
        status: str,
        reference_id: str,
        **kwargs: Any,
    ) -> tuple[Shipment | None, Shipment | None]:
        """Atomically check for existing + create if absent.

        Returns:
            (existing, created) — exactly one is None.
            If a shipment with this provider + reference_id already
            exists, returns (existing, None).
            If no such shipment exists, creates one and returns
            (None, created).
        """
        ...
    async def update_fields(
        self, shipment_id: str, **fields: Any
    ) -> Shipment:
        """Atomically update shipment fields by ID.

        This is the atomic persistence primitive for callback and
        polling flows. Unlike save() which mutates an in-memory
        object, this performs a single atomic update operation,
        preventing concurrent read-modify-save races.

        Args:
            shipment_id: The shipment to update.
            **fields: Fields to update (e.g. status, tracking_number).

        Returns:
            The updated shipment object.

        Raises:
            ShipmentNotFoundError: If no shipment with this ID exists.
        """
        ...
