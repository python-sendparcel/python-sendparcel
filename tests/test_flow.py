"""ShipmentFlow unit tests."""

import pytest

from conftest import DemoOrder, InMemoryRepository
from sendparcel.exceptions import InvalidTransitionError
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.registry import registry


class FlowProvider(BaseProvider):
    slug = "flow"
    display_name = "Flow Provider"

    async def create_shipment(self, **kwargs):
        return {"external_id": "ext-123", "tracking_number": "trk-123"}

    async def create_label(self, **kwargs):
        return {"format": "PDF", "url": "https://labels/123.pdf"}

    async def handle_callback(self, data: dict, headers: dict, **kwargs):
        if self.shipment.may_trigger("mark_in_transit"):
            self.shipment.mark_in_transit()

    async def fetch_shipment_status(self, **kwargs):
        return {"status": self.get_setting("status_override")}

    async def cancel_shipment(self, **kwargs):
        return True


@pytest.mark.asyncio
async def test_create_shipment_sets_created_and_ids() -> None:
    repository = InMemoryRepository()
    registry.register(FlowProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "flow")

    assert shipment.status == "created"
    assert shipment.external_id == "ext-123"
    assert shipment.tracking_number == "trk-123"


@pytest.mark.asyncio
async def test_create_label_updates_url_and_state() -> None:
    repository = InMemoryRepository()
    registry.register(FlowProvider)
    flow = ShipmentFlow(repository=repository)
    shipment = await flow.create_shipment(DemoOrder(), "flow")

    updated = await flow.create_label(shipment)

    assert updated.label_url == "https://labels/123.pdf"
    assert updated.status == "label_ready"


@pytest.mark.asyncio
async def test_fetch_and_update_status_applies_transition() -> None:
    repository = InMemoryRepository()
    registry.register(FlowProvider)
    flow = ShipmentFlow(
        repository=repository,
        config={"flow": {"status_override": "in_transit"}},
    )
    shipment = await flow.create_shipment(DemoOrder(), "flow")

    updated = await flow.fetch_and_update_status(shipment)

    assert updated.status == "in_transit"


@pytest.mark.asyncio
async def test_fetch_and_update_status_rejects_unknown_status() -> None:
    repository = InMemoryRepository()
    registry.register(FlowProvider)
    flow = ShipmentFlow(
        repository=repository,
        config={"flow": {"status_override": "unknown-status"}},
    )
    shipment = await flow.create_shipment(DemoOrder(), "flow")

    with pytest.raises(InvalidTransitionError, match="unknown-status"):
        await flow.fetch_and_update_status(shipment)


@pytest.mark.asyncio
async def test_cancel_shipment_transitions_to_cancelled() -> None:
    repository = InMemoryRepository()
    registry.register(FlowProvider)
    flow = ShipmentFlow(repository=repository)
    shipment = await flow.create_shipment(DemoOrder(), "flow")

    cancelled = await flow.cancel_shipment(shipment)

    assert cancelled is True
    assert shipment.status == "cancelled"
