"""Flow integration tests."""

import pytest

from conftest import DemoOrder, InMemoryRepository
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.registry import registry


class IntegrationProvider(BaseProvider):
    slug = "integration"
    display_name = "Integration Provider"

    async def create_shipment(self, **kwargs):
        return {"external_id": "int-1", "tracking_number": "trk-int-1"}

    async def create_label(self, **kwargs):
        return {"format": "PDF", "url": "https://labels/int.pdf"}

    async def verify_callback(self, data: dict, headers: dict, **kwargs):
        pass  # Accept all callbacks in test

    async def handle_callback(self, data: dict, headers: dict, **kwargs):
        if data.get("event") == "picked_up" and self.shipment.may_trigger(
            "mark_in_transit"
        ):
            self.shipment.mark_in_transit()

    async def fetch_shipment_status(self, **kwargs):
        return {"status": "in_transit"}

    async def cancel_shipment(self, **kwargs):
        return False


@pytest.mark.asyncio
async def test_full_flow_create_label_callback() -> None:
    repository = InMemoryRepository()
    registry.register(IntegrationProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "integration")
    shipment = await flow.create_label(shipment)
    shipment = await flow.handle_callback(
        shipment,
        data={"event": "picked_up"},
        headers={},
    )

    assert shipment.external_id == "int-1"
    assert shipment.label_url == "https://labels/int.pdf"
    assert shipment.status == "in_transit"
