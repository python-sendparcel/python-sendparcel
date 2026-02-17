"""ShipmentFlow unit tests."""

from decimal import Decimal

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
from sendparcel.types import AddressInfo, ParcelInfo

# ---------------------------------------------------------------------------
# Default test data
# ---------------------------------------------------------------------------

_SENDER = AddressInfo(
    name="Test Sender",
    line1="Sender St 1",
    city="Warsaw",
    postal_code="00-001",
    country_code="PL",
)
_RECEIVER = AddressInfo(
    name="Test Receiver",
    line1="Receiver St 2",
    city="Berlin",
    postal_code="10115",
    country_code="DE",
)
_PARCELS = [ParcelInfo(weight_kg=Decimal("1.0"))]

# ---------------------------------------------------------------------------
# Reusable test providers
# ---------------------------------------------------------------------------


class FlowProvider(BaseProvider):
    slug = "flow"
    display_name = "Flow Provider"

    async def create_shipment(
        self, *, sender_address, receiver_address, parcels, **kwargs
    ):
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


class FlowErrorProvider(BaseProvider):
    slug = "flow-error"
    display_name = "Flow Error Provider"

    async def create_shipment(
        self, *, sender_address, receiver_address, parcels, **kwargs
    ):
        raise httpx.ConnectError("connection refused")

    async def verify_callback(self, data, headers, **kwargs):
        pass

    async def handle_callback(self, data, headers, **kwargs):
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _register_and_flow(provider_cls, *, config=None, validators=None):
    """Register provider, return (flow, repository) tuple."""
    repository = InMemoryRepository()
    registry.register(provider_cls)
    flow = ShipmentFlow(
        repository=repository,
        config=config,
        validators=validators,
    )
    return flow, repository


async def _created_shipment(flow, provider_slug="flow"):
    """Create and return a shipment in 'created' state."""
    return await flow.create_shipment(
        provider_slug,
        sender_address=_SENDER,
        receiver_address=_RECEIVER,
        parcels=_PARCELS,
    )


# ---------------------------------------------------------------------------
# TestCreateShipment
# ---------------------------------------------------------------------------


class TestCreateShipment:
    @pytest.mark.asyncio
    async def test_sets_created_and_ids(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)

        shipment = await flow.create_shipment(
            "flow",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        assert shipment.status == "created"
        assert shipment.external_id == "ext-123"
        assert shipment.tracking_number == "trk-123"

    @pytest.mark.asyncio
    async def test_unknown_provider_slug_raises_key_error(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)

        with pytest.raises(KeyError):
            await flow.create_shipment(
                "nonexistent-provider",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )

    @pytest.mark.asyncio
    async def test_provider_returning_label_sets_label_ready(self) -> None:
        """When result contains a label, status is label_ready."""

        class LabelIncludedProvider(BaseProvider):
            slug = "label-incl"
            display_name = "Label Included"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {
                    "external_id": "li-1",
                    "tracking_number": "trk-li",
                    "label": {"url": "https://labels/incl.pdf"},
                }

        flow, _ = _register_and_flow(LabelIncludedProvider)

        shipment = await flow.create_shipment(
            "label-incl",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        assert shipment.status == "label_ready"
        assert shipment.label_url == "https://labels/incl.pdf"


# ---------------------------------------------------------------------------
# TestCreateLabel
# ---------------------------------------------------------------------------


class TestCreateLabel:
    @pytest.mark.asyncio
    async def test_updates_url_and_state(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        updated = await flow.create_label(shipment)

        assert updated.label_url == "https://labels/123.pdf"
        assert updated.status == "label_ready"

    @pytest.mark.asyncio
    async def test_wraps_provider_error_in_communication_error(self) -> None:
        class LabelErrorProvider(BaseProvider):
            slug = "label-err"
            display_name = "Label Error"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "le-1", "tracking_number": "trk-le"}

            async def create_label(self, **kwargs):
                raise RuntimeError("label service unavailable")

        flow, _ = _register_and_flow(LabelErrorProvider)
        shipment = await _created_shipment(flow, "label-err")

        with pytest.raises(
            CommunicationError, match="label service unavailable"
        ):
            await flow.create_label(shipment)

    @pytest.mark.asyncio
    async def test_failing_validator_raises(self) -> None:
        def reject_all(data):
            raise ValueError("shipment rejected by validator")

        flow, _ = _register_and_flow(FlowProvider, validators=[reject_all])
        shipment = await _created_shipment(flow)

        with pytest.raises(ValueError, match="shipment rejected by validator"):
            await flow.create_label(shipment)

    @pytest.mark.asyncio
    async def test_wraps_httpx_error_in_communication_error(self) -> None:
        class LabelHttpxErrorProvider(BaseProvider):
            slug = "label-httpx-err"
            display_name = "Label Httpx Error"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "lhe-1", "tracking_number": "trk-lhe"}

            async def create_label(self, **kwargs):
                raise httpx.TimeoutException("label request timed out")

        flow, _ = _register_and_flow(LabelHttpxErrorProvider)
        shipment = await _created_shipment(flow, "label-httpx-err")

        with pytest.raises(CommunicationError, match="label request timed out"):
            await flow.create_label(shipment)


# ---------------------------------------------------------------------------
# TestHandleCallback
# ---------------------------------------------------------------------------


class TestHandleCallback:
    @pytest.mark.asyncio
    async def test_callback_transitions_shipment(self) -> None:
        """handle_callback delegates to provider, transitions shipment."""
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        updated = await flow.handle_callback(shipment, {}, {})

        assert updated.status == "in_transit"

    @pytest.mark.asyncio
    async def test_wraps_generic_provider_error(self) -> None:
        class CallbackErrorProvider(BaseProvider):
            slug = "cb-err"
            display_name = "Callback Error"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "ce-1", "tracking_number": "trk-ce"}

            async def verify_callback(self, data, headers, **kwargs):
                pass

            async def handle_callback(self, data, headers, **kwargs):
                raise RuntimeError("callback processing failed")

        flow, _ = _register_and_flow(CallbackErrorProvider)
        shipment = await _created_shipment(flow, "cb-err")

        with pytest.raises(
            CommunicationError, match="callback processing failed"
        ):
            await flow.handle_callback(shipment, {}, {})

    @pytest.mark.asyncio
    async def test_wraps_httpx_error(self) -> None:
        class CallbackHttpxProvider(BaseProvider):
            slug = "cb-httpx"
            display_name = "Callback Httpx"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "ch-1", "tracking_number": "trk-ch"}

            async def verify_callback(self, data, headers, **kwargs):
                raise httpx.ReadTimeout("read timeout during callback verify")

            async def handle_callback(self, data, headers, **kwargs):
                pass

        flow, _ = _register_and_flow(CallbackHttpxProvider)
        shipment = await _created_shipment(flow, "cb-httpx")

        with pytest.raises(
            CommunicationError, match="read timeout during callback verify"
        ):
            await flow.handle_callback(shipment, {}, {})


# ---------------------------------------------------------------------------
# TestFetchAndUpdateStatus
# ---------------------------------------------------------------------------


class TestFetchAndUpdateStatus:
    @pytest.mark.asyncio
    async def test_applies_transition(self) -> None:
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": "in_transit"}},
        )
        shipment = await _created_shipment(flow)

        updated = await flow.fetch_and_update_status(shipment)

        assert updated.status == "in_transit"

    @pytest.mark.asyncio
    async def test_rejects_unknown_status(self) -> None:
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": "unknown-status"}},
        )
        shipment = await _created_shipment(flow)

        with pytest.raises(InvalidTransitionError, match="unknown-status"):
            await flow.fetch_and_update_status(shipment)

    @pytest.mark.asyncio
    async def test_none_status_does_not_transition(self) -> None:
        """Provider returns None status: shipment saved, no transition."""
        flow, repository = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": None}},
        )
        shipment = await _created_shipment(flow)
        status_before = shipment.status

        updated = await flow.fetch_and_update_status(shipment)

        assert updated.status == status_before
        # save was called (once for create, once for fetch_and_update)
        assert repository.save_count == 2

    @pytest.mark.asyncio
    async def test_wraps_provider_error(self) -> None:
        class FetchErrorProvider(BaseProvider):
            slug = "fetch-err"
            display_name = "Fetch Error"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "fe-1", "tracking_number": "trk-fe"}

            async def fetch_shipment_status(self, **kwargs):
                raise httpx.ConnectError("status endpoint down")

        flow, _ = _register_and_flow(FetchErrorProvider)
        shipment = await _created_shipment(flow, "fetch-err")

        with pytest.raises(CommunicationError, match="status endpoint down"):
            await flow.fetch_and_update_status(shipment)


# ---------------------------------------------------------------------------
# TestCancelShipment
# ---------------------------------------------------------------------------


class TestCancelShipment:
    @pytest.mark.asyncio
    async def test_transitions_to_cancelled(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        cancelled = await flow.cancel_shipment(shipment)

        assert cancelled is True
        assert shipment.status == "cancelled"

    @pytest.mark.asyncio
    async def test_provider_returns_false_keeps_status(self) -> None:
        """When provider.cancel_shipment returns False, status unchanged."""

        class NoCancelProvider(BaseProvider):
            slug = "no-cancel"
            display_name = "No Cancel"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "nc-1", "tracking_number": "trk-nc"}

            async def cancel_shipment(self, **kwargs):
                return False

        flow, repository = _register_and_flow(NoCancelProvider)
        shipment = await _created_shipment(flow, "no-cancel")
        status_before = shipment.status
        save_count_before = repository.save_count

        result = await flow.cancel_shipment(shipment)

        assert result is False
        assert shipment.status == status_before
        # save should NOT have been called again
        assert repository.save_count == save_count_before

    @pytest.mark.asyncio
    async def test_wraps_provider_error(self) -> None:
        class CancelErrorProvider(BaseProvider):
            slug = "cancel-err"
            display_name = "Cancel Error"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "ce-1", "tracking_number": "trk-ce"}

            async def cancel_shipment(self, **kwargs):
                raise RuntimeError("cancel endpoint crashed")

        flow, _ = _register_and_flow(CancelErrorProvider)
        shipment = await _created_shipment(flow, "cancel-err")

        with pytest.raises(CommunicationError, match="cancel endpoint crashed"):
            await flow.cancel_shipment(shipment)


# ---------------------------------------------------------------------------
# TestErrorWrapping
# ---------------------------------------------------------------------------


class TestErrorWrapping:
    @pytest.mark.asyncio
    async def test_create_shipment_wraps_httpx_error(self) -> None:
        flow, _ = _register_and_flow(FlowErrorProvider)

        with pytest.raises(CommunicationError, match="connection refused"):
            await flow.create_shipment(
                "flow-error",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )

    @pytest.mark.asyncio
    async def test_create_shipment_wraps_generic_provider_error(self) -> None:
        class BrokenProvider(BaseProvider):
            slug = "broken"
            display_name = "Broken"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                raise RuntimeError("internal provider bug")

        flow, _ = _register_and_flow(BrokenProvider)

        with pytest.raises(CommunicationError, match="internal provider bug"):
            await flow.create_shipment(
                "broken",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )

    @pytest.mark.asyncio
    async def test_sendparcel_exceptions_pass_through_unwrapped(self) -> None:
        """InvalidCallbackError should NOT be double-wrapped."""

        class RejectingProvider(BaseProvider):
            slug = "rejecting"
            display_name = "Rejecting"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "r-1", "tracking_number": "trk-r"}

            async def verify_callback(self, data, headers, **kwargs):
                raise InvalidCallbackError("bad signature")

            async def handle_callback(self, data, headers, **kwargs):
                pass

        flow, _ = _register_and_flow(RejectingProvider)
        shipment = await flow.create_shipment(
            "rejecting",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        with pytest.raises(InvalidCallbackError, match="bad signature"):
            await flow.handle_callback(shipment, {}, {})

    @pytest.mark.asyncio
    async def test_communication_error_includes_original_error_context(
        self,
    ) -> None:
        """CommunicationError.context should include the original error type."""
        flow, _ = _register_and_flow(FlowErrorProvider)

        with pytest.raises(CommunicationError) as exc_info:
            await flow.create_shipment(
                "flow-error",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )

        assert exc_info.value.context["original_error"] == "ConnectError"


# ---------------------------------------------------------------------------
# TestResolveCallback
# ---------------------------------------------------------------------------


class TestResolveCallback:
    @pytest.mark.asyncio
    async def test_raw_callback_name_is_rejected(self) -> None:
        """'cancel' as status should fail, not be treated as callback."""

        class RawCallbackProvider(BaseProvider):
            slug = "raw-cb"
            display_name = "Raw Callback"

            async def create_shipment(
                self, *, sender_address, receiver_address, parcels, **kwargs
            ):
                return {"external_id": "rc-1", "tracking_number": "trk-rc"}

            async def verify_callback(self, data, headers, **kwargs):
                pass

            async def handle_callback(self, data, headers, **kwargs):
                pass

            async def fetch_shipment_status(self, **kwargs):
                return {"status": "cancel"}

        flow, _ = _register_and_flow(RawCallbackProvider, config={"raw-cb": {}})
        shipment = await _created_shipment(flow, "raw-cb")

        with pytest.raises(InvalidTransitionError):
            await flow.fetch_and_update_status(shipment)


# ---------------------------------------------------------------------------
# TestTrigger
# ---------------------------------------------------------------------------


class TestTrigger:
    @pytest.mark.asyncio
    async def test_invalid_transition_from_current_status(self) -> None:
        """Invalid callback from current status raises InvalidTransition."""
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": "delivered"}},
        )
        shipment = await _created_shipment(flow)

        # Shipment is in 'created' status; 'delivered' maps to 'mark_delivered'
        # which is only allowed from 'in_transit' or 'out_for_delivery'.
        with pytest.raises(
            InvalidTransitionError, match="cannot be executed from status"
        ):
            await flow.fetch_and_update_status(shipment)

    @pytest.mark.asyncio
    async def test_cancel_from_in_transit_raises(self) -> None:
        """Cancel only allowed from new/created/label_ready, not in_transit."""
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": "in_transit"}},
        )
        shipment = await _created_shipment(flow)

        # Transition to in_transit first
        shipment = await flow.fetch_and_update_status(shipment)
        assert shipment.status == "in_transit"

        with pytest.raises(
            InvalidTransitionError, match="cannot be executed from status"
        ):
            await flow.cancel_shipment(shipment)


# ---------------------------------------------------------------------------
# TestCreateShipmentFromOrder
# ---------------------------------------------------------------------------


class TestCreateShipmentFromOrder:
    @pytest.mark.asyncio
    async def test_delegates_to_create_shipment(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        order = DemoOrder()
        shipment = await flow.create_shipment_from_order(order, "flow")
        assert shipment.status == "created"
        assert shipment.external_id == "ext-123"

    @pytest.mark.asyncio
    async def test_passes_order_id_to_kwargs(self) -> None:
        flow, repo = _register_and_flow(FlowProvider)
        order = DemoOrder()
        order.id = "order-42"
        shipment = await flow.create_shipment_from_order(order, "flow")
        assert shipment.status == "created"
