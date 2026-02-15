"""Flow integration tests."""

import pytest

from conftest import DemoOrder, InMemoryRepository
from sendparcel.exceptions import CommunicationError, InvalidCallbackError
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


class CancellableProvider(IntegrationProvider):
    """Provider that accepts cancellation requests."""

    slug = "cancellable"
    display_name = "Cancellable Provider"

    async def cancel_shipment(self, **kwargs):
        return True


class RejectingCallbackProvider(IntegrationProvider):
    """Provider that rejects callbacks with InvalidCallbackError."""

    slug = "rejecting-callback"
    display_name = "Rejecting Callback Provider"

    async def verify_callback(self, data: dict, headers: dict, **kwargs):
        raise InvalidCallbackError("Invalid signature")


class FullLifecycleProvider(IntegrationProvider):
    """Provider whose handle_callback drives shipment through all states."""

    slug = "full-lifecycle"
    display_name = "Full Lifecycle Provider"

    async def handle_callback(self, data: dict, headers: dict, **kwargs):
        event = data.get("event")
        transitions = {
            "picked_up": "mark_in_transit",
            "out_for_delivery": "mark_out_for_delivery",
            "delivered": "mark_delivered",
            "returned": "mark_returned",
            "failed": "fail",
        }
        callback = transitions.get(event)
        if callback and self.shipment.may_trigger(callback):
            getattr(self.shipment, callback)()

    async def fetch_shipment_status(self, **kwargs):
        return {"status": self._poll_status}

    _poll_status = "in_transit"


class CommunicationErrorProvider(BaseProvider):
    """Provider whose create_shipment raises a non-domain exception."""

    slug = "comm-error"
    display_name = "Communication Error Provider"

    async def create_shipment(self, **kwargs):
        raise RuntimeError("Connection refused")


# ---------------------------------------------------------------------------
# Existing happy-path test
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Failure, cancellation, and return scenarios
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation_at_created_state() -> None:
    """Create shipment -> cancel (provider accepts) -> status is cancelled."""
    repository = InMemoryRepository()
    registry.register(CancellableProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "cancellable")
    assert shipment.status == "created"

    cancelled = await flow.cancel_shipment(shipment)

    assert cancelled is True
    assert shipment.status == "cancelled"


@pytest.mark.asyncio
async def test_cancel_rejected_by_provider() -> None:
    """Create shipment -> cancel (provider rejects) -> status stays created."""
    repository = InMemoryRepository()
    registry.register(IntegrationProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "integration")
    assert shipment.status == "created"

    cancelled = await flow.cancel_shipment(shipment)

    assert cancelled is False
    assert shipment.status == "created"


@pytest.mark.asyncio
async def test_failure_at_in_transit_state() -> None:
    """Create -> transit (via callback) -> fail (via callback) -> status is failed."""
    repository = InMemoryRepository()
    registry.register(FullLifecycleProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "full-lifecycle")
    shipment = await flow.handle_callback(
        shipment, data={"event": "picked_up"}, headers={}
    )
    assert shipment.status == "in_transit"

    shipment = await flow.handle_callback(
        shipment, data={"event": "failed"}, headers={}
    )

    assert shipment.status == "failed"
    assert shipment.external_id == "int-1"
    assert shipment.tracking_number == "trk-int-1"


@pytest.mark.asyncio
async def test_callback_with_invalid_signature() -> None:
    """Create -> handle_callback with invalid signature -> InvalidCallbackError propagates."""
    repository = InMemoryRepository()
    registry.register(RejectingCallbackProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "rejecting-callback")
    original_status = shipment.status

    with pytest.raises(InvalidCallbackError, match="Invalid signature"):
        await flow.handle_callback(
            shipment, data={"event": "picked_up"}, headers={}
        )

    assert shipment.status == original_status


@pytest.mark.asyncio
async def test_return_after_delivery() -> None:
    """Create -> transit -> delivered -> returned through full flow."""
    repository = InMemoryRepository()
    registry.register(FullLifecycleProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "full-lifecycle")
    shipment = await flow.handle_callback(
        shipment, data={"event": "picked_up"}, headers={}
    )
    assert shipment.status == "in_transit"

    shipment = await flow.handle_callback(
        shipment, data={"event": "delivered"}, headers={}
    )
    assert shipment.status == "delivered"

    shipment = await flow.handle_callback(
        shipment, data={"event": "returned"}, headers={}
    )

    assert shipment.status == "returned"
    assert shipment.external_id == "int-1"


@pytest.mark.asyncio
async def test_fetch_and_update_status_poll_flow() -> None:
    """Create -> fetch_and_update_status polls provider -> transitions to in_transit."""
    repository = InMemoryRepository()
    registry.register(FullLifecycleProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "full-lifecycle")
    assert shipment.status == "created"

    # FullLifecycleProvider.fetch_shipment_status returns {"status": "in_transit"}
    shipment = await flow.fetch_and_update_status(shipment)

    assert shipment.status == "in_transit"
    assert shipment.tracking_number == "trk-int-1"
    assert repository.save_count >= 2  # create + fetch_and_update


@pytest.mark.asyncio
async def test_provider_create_shipment_communication_error() -> None:
    """Provider raises non-domain error -> wrapped in CommunicationError."""
    repository = InMemoryRepository()
    registry.register(CommunicationErrorProvider)
    flow = ShipmentFlow(repository=repository)

    with pytest.raises(CommunicationError) as exc_info:
        await flow.create_shipment(DemoOrder(), "comm-error")

    assert "Connection refused" in str(exc_info.value)
    assert exc_info.value.context["original_error"] == "RuntimeError"


@pytest.mark.asyncio
async def test_full_lifecycle_create_label_transit_deliver_return() -> None:
    """Complete lifecycle: create -> label -> transit -> out_for_delivery -> deliver -> return."""
    repository = InMemoryRepository()
    registry.register(FullLifecycleProvider)
    flow = ShipmentFlow(repository=repository)

    shipment = await flow.create_shipment(DemoOrder(), "full-lifecycle")
    assert shipment.status == "created"
    assert shipment.external_id == "int-1"
    assert shipment.tracking_number == "trk-int-1"

    shipment = await flow.create_label(shipment)
    assert shipment.status == "label_ready"
    assert shipment.label_url == "https://labels/int.pdf"

    shipment = await flow.handle_callback(
        shipment, data={"event": "picked_up"}, headers={}
    )
    assert shipment.status == "in_transit"

    shipment = await flow.handle_callback(
        shipment, data={"event": "out_for_delivery"}, headers={}
    )
    assert shipment.status == "out_for_delivery"

    shipment = await flow.handle_callback(
        shipment, data={"event": "delivered"}, headers={}
    )
    assert shipment.status == "delivered"

    shipment = await flow.handle_callback(
        shipment, data={"event": "returned"}, headers={}
    )
    assert shipment.status == "returned"

    # Verify repository tracked all saves
    assert repository.save_count >= 6
