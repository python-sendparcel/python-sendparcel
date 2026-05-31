"""ShipmentFlow unit tests."""

from decimal import Decimal
from typing import Any

import httpx
import pytest

from conftest import InMemoryRepository
from sendparcel.enums import LabelFormat
from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
    ProviderCapabilityError,
    ProviderNotFoundError,
)
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import (
    BaseProvider,
    CancellableProvider,
    LabelProvider,
    PullStatusProvider,
    PushCallbackProvider,
)
from sendparcel.registry import registry
from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentUpdateResult,
)

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


class FlowProvider(
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider,
):
    slug = "flow"
    display_name = "Flow Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(
            external_id="ext-123",
            tracking_number="trk-123",
        )

    async def create_label(self, **kwargs: Any) -> LabelInfo:
        return LabelInfo(format=LabelFormat.PDF, url="https://labels/123.pdf")

    async def verify_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        if headers.get("x-flow-token") == "bad":
            raise InvalidCallbackError("bad signature")

    async def handle_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> ShipmentUpdateResult:
        status = str(data.get("status", "in_transit"))
        return ShipmentUpdateResult(
            status=status,
            tracking_events=[{"code": "accepted"}],
        )

    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentUpdateResult:
        return ShipmentUpdateResult(
            status=self.get_setting("status_override", "in_transit"),
            tracking_events=[{"code": "polled"}],
        )

    async def cancel_shipment(self, **kwargs: Any) -> bool:
        return bool(self.get_setting("cancel_success", True))


class LabelIncludedProvider(BaseProvider):
    slug = "label-included"
    display_name = "Label Included"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(
            external_id="li-1",
            tracking_number="trk-li",
            label=LabelInfo(
                format=LabelFormat.PDF,
                url="https://labels/included.pdf",
            ),
        )


class BareProvider(BaseProvider):
    slug = "bare"
    display_name = "Bare Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="bare-1")


class BrokenProvider(BaseProvider):
    slug = "broken"
    display_name = "Broken Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        raise httpx.ConnectError("connection refused")


class ValueErrorProvider(BaseProvider):
    slug = "value-error"
    display_name = "ValueError Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        raise ValueError("provider bug: missing field")


def _register_and_flow(
    provider_cls: type[BaseProvider],
    *,
    config: dict[str, Any] | None = None,
    validators: list[Any] | None = None,
) -> tuple[ShipmentFlow, InMemoryRepository]:
    repository = InMemoryRepository()
    registry.register(provider_cls)
    flow = ShipmentFlow(
        repository=repository,
        config=config,
        validators=validators,
    )
    return flow, repository


async def _created_shipment(
    flow: ShipmentFlow, provider_slug: str = "flow"
) -> Any:
    outcome = await flow.create_shipment(
        provider_slug,
        sender_address=_SENDER,
        receiver_address=_RECEIVER,
        parcels=_PARCELS,
    )
    return outcome.shipment


class TestCreateShipment:
    @pytest.mark.asyncio
    async def test_returns_outcome_and_persists_metadata(self) -> None:
        flow, repository = _register_and_flow(FlowProvider)

        outcome = await flow.create_shipment(
            "flow",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        assert outcome.label is None
        assert outcome.shipment.status == "created"
        assert outcome.shipment.external_id == "ext-123"
        assert outcome.shipment.tracking_number == "trk-123"
        assert repository.create_count == 1
        assert repository.save_count == 1

    @pytest.mark.asyncio
    async def test_inline_label_returns_payload_and_label_ready_status(
        self,
    ) -> None:
        flow, _ = _register_and_flow(LabelIncludedProvider)

        outcome = await flow.create_shipment(
            "label-included",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        assert outcome.shipment.status == "label_ready"
        assert outcome.label is not None
        assert outcome.label.get("url") == "https://labels/included.pdf"

    @pytest.mark.asyncio
    async def test_unknown_provider_raises_provider_not_found(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)

        with pytest.raises(ProviderNotFoundError):
            await flow.create_shipment(
                "ghost",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )

    @pytest.mark.asyncio
    async def test_provider_error_is_wrapped(self) -> None:
        """CommunicationError marks shipment as SUBMITTED for reconciliation."""
        flow, _ = _register_and_flow(BrokenProvider)

        outcome = await flow.create_shipment(
            "broken",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )
        assert outcome.shipment.status == "submitted"
        assert outcome.label is None

    @pytest.mark.asyncio
    async def test_non_http_exception_propagates_as_is(self) -> None:
        """Domain errors (ValueError, TypeError, etc.) must NOT be wrapped."""
        flow, _ = _register_and_flow(ValueErrorProvider)

        with pytest.raises(ValueError, match="provider bug: missing field"):
            await flow.create_shipment(
                "value-error",
                sender_address=_SENDER,
                receiver_address=_RECEIVER,
                parcels=_PARCELS,
            )


class RollbackProvider(BaseProvider):
    slug = "rollback"
    display_name = "Rollback Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        raise httpx.ConnectError("provider unavailable")


class TestCreateLabel:
    @pytest.mark.asyncio
    async def test_returns_payload_and_marks_shipment_label_ready(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        outcome = await flow.create_label(shipment)

        assert outcome.shipment.status == "label_ready"
        assert outcome.label.get("url") == "https://labels/123.pdf"

    @pytest.mark.asyncio
    async def test_validator_failure_is_propagated(self) -> None:
        def reject_all(data: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("shipment rejected")

        flow, _ = _register_and_flow(FlowProvider, validators=[reject_all])
        shipment = await _created_shipment(flow)

        with pytest.raises(ValueError, match="shipment rejected"):
            await flow.create_label(shipment)

    @pytest.mark.asyncio
    async def test_provider_without_label_capability_is_rejected(self) -> None:
        flow, _ = _register_and_flow(BareProvider)
        shipment = await _created_shipment(flow, "bare")

        with pytest.raises(ProviderCapabilityError, match="label creation"):
            await flow.create_label(shipment)


class TestHandleCallback:
    @pytest.mark.asyncio
    async def test_returns_normalized_update_and_applies_status(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        outcome = await flow.handle_callback(
            shipment,
            {"status": "in_transit"},
            {},
        )

        assert outcome.shipment.status == "in_transit"
        assert outcome.update.get("status") == "in_transit"
        assert outcome.update.get("tracking_events") == [{"code": "accepted"}]

    @pytest.mark.asyncio
    async def test_invalid_callback_error_passes_through(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        with pytest.raises(InvalidCallbackError, match="bad signature"):
            await flow.handle_callback(
                shipment,
                {"status": "in_transit"},
                {"x-flow-token": "bad"},
            )

    @pytest.mark.asyncio
    async def test_unknown_status_is_rejected(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        with pytest.raises(
            InvalidTransitionError, match="Unknown shipment status"
        ):
            await flow.handle_callback(
                shipment,
                {"status": "teleported"},
                {},
            )


class TestFetchAndUpdateStatus:
    @pytest.mark.asyncio
    async def test_returns_update_outcome(self) -> None:
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"status_override": "out_for_delivery"}},
        )
        shipment = await _created_shipment(flow)

        outcome = await flow.fetch_and_update_status(shipment)

        assert outcome.shipment.status == "out_for_delivery"
        assert outcome.update.get("tracking_events") == [{"code": "polled"}]

    @pytest.mark.asyncio
    async def test_provider_without_polling_capability_is_rejected(
        self,
    ) -> None:
        flow, _ = _register_and_flow(BareProvider)
        shipment = await _created_shipment(flow, "bare")

        with pytest.raises(ProviderCapabilityError, match="status polling"):
            await flow.fetch_and_update_status(shipment)


class TestCancelShipment:
    @pytest.mark.asyncio
    async def test_provider_accepts_cancel_and_status_changes(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)

        cancelled = await flow.cancel_shipment(shipment)

        assert cancelled is True
        assert shipment.status == "cancelled"

    @pytest.mark.asyncio
    async def test_provider_rejects_cancel_and_status_stays_created(
        self,
    ) -> None:
        flow, _ = _register_and_flow(
            FlowProvider,
            config={"flow": {"cancel_success": False}},
        )
        shipment = await _created_shipment(flow)

        cancelled = await flow.cancel_shipment(shipment)

        assert cancelled is False
        assert shipment.status == "created"

    @pytest.mark.asyncio
    async def test_cancel_from_in_transit_is_rejected(self) -> None:
        flow, _ = _register_and_flow(FlowProvider)
        shipment = await _created_shipment(flow)
        shipment = (
            await flow.handle_callback(shipment, {"status": "in_transit"}, {})
        ).shipment

        with pytest.raises(InvalidTransitionError, match="cannot transition"):
            await flow.cancel_shipment(shipment)


class TestCreateShipmentRollback:
    @pytest.mark.asyncio
    async def test_provider_failure_marks_submitted_not_deleted(self) -> None:
        """If the provider call fails with CommunicationError, the record
        is marked as SUBMITTED (not deleted), enabling reconciliation."""
        flow, repository = _register_and_flow(RollbackProvider)

        outcome = await flow.create_shipment(
            "rollback",
            sender_address=_SENDER,
            receiver_address=_RECEIVER,
            parcels=_PARCELS,
        )

        # The partial record must NOT be deleted.
        assert repository.create_count == 1
        assert len(repository._store) == 1
        # The shipment should be marked as SUBMITTED for reconciliation.
        assert outcome.shipment.status == "submitted"
