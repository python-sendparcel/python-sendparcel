"""Protocol tests."""

from typing import Any

from sendparcel.protocols import Shipment, ShipmentRepository


class DemoShipment:
    id = "s-1"
    status = "new"
    provider = "dummy"
    external_id = ""
    tracking_number = ""


class DemoRepository:
    async def get_by_id(self, shipment_id: str) -> DemoShipment:
        return DemoShipment()

    async def create(self, **kwargs: Any) -> DemoShipment:
        return DemoShipment()

    async def save(self, shipment: DemoShipment) -> DemoShipment:
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields: Any
    ) -> DemoShipment:
        shipment = DemoShipment()
        shipment.status = status
        for key, value in fields.items():
            setattr(shipment, key, value)
        return shipment

    async def delete(self, shipment_id: str) -> None:
        pass

    async def find_by_reference(
        self, provider: str, reference_id: str
    ) -> DemoShipment | None:
        return None


def test_runtime_protocol_checks_shipment_without_label_url() -> None:
    assert isinstance(DemoShipment(), Shipment)


def test_runtime_protocol_checks_repository() -> None:
    assert isinstance(DemoRepository(), ShipmentRepository)
