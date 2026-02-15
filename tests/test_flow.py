"""ShipmentFlow unit tests."""

import httpx
import pytest

from conftest import DemoOrder, InMemoryRepository
from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
)
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

    async def verify_callback(self, data: dict, headers: dict, **kwargs):
        pass  # Accept all callbacks in test

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


class FlowErrorProvider(BaseProvider):
    slug = "flow-error"
    display_name = "Flow Error Provider"

    async def create_shipment(self, **kwargs):
        raise httpx.ConnectError("connection refused")

    async def verify_callback(self, data, headers, **kwargs):
        pass

    async def handle_callback(self, data, headers, **kwargs):
        pass


class TestFlowErrorHandling:
    @pytest.mark.asyncio
    async def test_create_shipment_wraps_httpx_error(self) -> None:
        repository = InMemoryRepository()
        registry.register(FlowErrorProvider)
        flow = ShipmentFlow(repository=repository)

        with pytest.raises(CommunicationError, match="connection refused"):
            await flow.create_shipment(DemoOrder(), "flow-error")

    @pytest.mark.asyncio
    async def test_create_shipment_wraps_generic_provider_error(self) -> None:
        class BrokenProvider(BaseProvider):
            slug = "broken"
            display_name = "Broken"

            async def create_shipment(self, **kwargs):
                raise RuntimeError("internal provider bug")

        repository = InMemoryRepository()
        registry.register(BrokenProvider)
        flow = ShipmentFlow(repository=repository)

        with pytest.raises(CommunicationError, match="internal provider bug"):
            await flow.create_shipment(DemoOrder(), "broken")

    @pytest.mark.asyncio
    async def test_sendparcel_exceptions_pass_through_unwrapped(self) -> None:
        """InvalidCallbackError should NOT be double-wrapped."""

        class RejectingProvider(BaseProvider):
            slug = "rejecting"
            display_name = "Rejecting"

            async def create_shipment(self, **kwargs):
                return {"external_id": "r-1", "tracking_number": "trk-r"}

            async def verify_callback(self, data, headers, **kwargs):
                raise InvalidCallbackError("bad signature")

            async def handle_callback(self, data, headers, **kwargs):
                pass

        repository = InMemoryRepository()
        registry.register(RejectingProvider)
        flow = ShipmentFlow(repository=repository)

        shipment = await flow.create_shipment(DemoOrder(), "rejecting")

        with pytest.raises(InvalidCallbackError, match="bad signature"):
            await flow.handle_callback(shipment, {}, {})
