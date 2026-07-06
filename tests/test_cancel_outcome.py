"""Tests for CancelOutcome and cancel_shipment result semantics."""

from __future__ import annotations

import pytest

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import CommunicationError
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.types import (
    AddressInfo,
    CancelOutcome,
    CancelReason,
    ParcelInfo,
    ShipmentCreateResult,
)


class CancelOutcomeTestProvider(BaseProvider):
    """Provider that returns configurable CancelOutcome."""

    slug = "cancel_test"
    display_name = "Cancel Test"
    cancel_result: CancelOutcome | Exception | None = None

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs,
    ) -> ShipmentCreateResult:
        return {"external_id": "ext-1"}

    async def cancel_shipment(self, **kwargs) -> CancelOutcome:
        if isinstance(self.cancel_result, Exception):
            raise self.cancel_result
        if self.cancel_result is None:
            raise NotImplementedError("cancel_result not configured")
        return self.cancel_result


class DummyShipment:
    def __init__(self, status=ShipmentStatus.CREATED) -> None:
        self.id = "ship-1"
        self.status = status
        self.provider = "cancel_test"
        self.external_id = "12345"
        self.tracking_number = "TRK-123"


class DummyRepo:
    def __init__(self) -> None:
        self.shipment = DummyShipment()
        self.updated_shipment: DummyShipment | None = None

    async def create(self, **kwargs) -> DummyShipment:
        return self.shipment

    async def save(self, shipment: DummyShipment) -> DummyShipment:
        return shipment

    async def update_status(self, shipment_id: str, status: str, **fields):
        return self.shipment

    async def update_fields(self, shipment_id: str, **fields) -> DummyShipment:
        for key, value in fields.items():
            setattr(self.shipment, key, value)
        self.updated_shipment = self.shipment
        return self.shipment

    async def delete(self, shipment_id: str) -> None:
        pass

    async def find_by_reference(self, provider: str, reference_id: str):
        return self.shipment

    async def create_with_idempotency_key(
        self, provider: str, status: str, reference_id: str, **kwargs
    ):
        return (None, self.shipment)

    def get_by_id_sync(self, shipment_id: str, *, for_update: bool = False):
        return self.shipment

    async def get_by_id(self, shipment_id: str, *, for_update: bool = False):
        return self.shipment


def _make_flow(
    provider: type[CancelOutcomeTestProvider],
) -> tuple[ShipmentFlow, CancelOutcomeTestProvider, DummyRepo]:
    from sendparcel.registry import PluginRegistry

    registry = PluginRegistry()
    registry.register(provider)
    repo = DummyRepo()
    flow = ShipmentFlow(repository=repo, registry=registry)
    instance = provider(shipment=repo.shipment)
    return flow, instance, repo


class TestCancelReason:
    """CancelReason enum tests."""

    def test_cancelled_value(self) -> None:
        assert CancelReason.CANCELLED == "cancelled"

    def test_already_cancelled_value(self) -> None:
        assert CancelReason.ALREADY_CANCELLED == "already_cancelled"

    def test_refused_in_transit_value(self) -> None:
        assert CancelReason.REFUSED_IN_TRANSIT == "refused_in_transit"

    def test_not_cancellable_value(self) -> None:
        assert CancelReason.NOT_CANCELLABLE == "not_cancellable"

    def test_transient_error_value(self) -> None:
        assert CancelReason.TRANSIENT_ERROR == "transient_error"

    def test_auth_error_value(self) -> None:
        assert CancelReason.AUTH_ERROR == "auth_error"


class TestCancelOutcome:
    """CancelOutcome TypedDict tests."""

    def test_successful_cancel(self) -> None:
        outcome: CancelOutcome = {
            "cancelled": True,
            "reason": CancelReason.CANCELLED,
            "retryable": False,
            "provider_status_code": 200,
            "detail": None,
        }
        assert outcome["cancelled"] is True
        assert outcome["retryable"] is False

    def test_already_cancelled(self) -> None:
        outcome: CancelOutcome = {
            "cancelled": True,
            "reason": CancelReason.ALREADY_CANCELLED,
            "retryable": False,
            "provider_status_code": 404,
            "detail": None,
        }
        assert outcome["cancelled"] is True
        assert outcome["reason"] == CancelReason.ALREADY_CANCELLED

    def test_refused_in_transit(self) -> None:
        outcome: CancelOutcome = {
            "cancelled": False,
            "reason": CancelReason.REFUSED_IN_TRANSIT,
            "retryable": False,
            "provider_status_code": 400,
            "detail": "Shipment already in transit",
        }
        assert outcome["cancelled"] is False
        assert outcome["retryable"] is False

    def test_transient_error(self) -> None:
        outcome: CancelOutcome = {
            "cancelled": False,
            "reason": CancelReason.TRANSIENT_ERROR,
            "retryable": True,
            "provider_status_code": 503,
            "detail": "Service unavailable",
        }
        assert outcome["cancelled"] is False
        assert outcome["retryable"] is True


class TestFlowCancelShipment:
    """ShipmentFlow.cancel_shipment integration tests."""

    async def test_successful_cancel_transitions_to_cancelled(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=True,
            reason=CancelReason.CANCELLED,
            retryable=False,
            provider_status_code=200,
            detail=None,
        )
        flow, _, repo = _make_flow(provider_class)

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is True
        assert result["reason"] == CancelReason.CANCELLED
        assert repo.shipment.status == ShipmentStatus.CANCELLED

    async def test_already_cancelled_transitions_to_cancelled(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=True,
            reason=CancelReason.ALREADY_CANCELLED,
            retryable=False,
            provider_status_code=404,
            detail=None,
        )
        flow, _, repo = _make_flow(provider_class)

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is True
        assert result["reason"] == CancelReason.ALREADY_CANCELLED
        assert repo.shipment.status == ShipmentStatus.CANCELLED

    async def test_refused_in_transit_leaves_state_unchanged(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=False,
            reason=CancelReason.REFUSED_IN_TRANSIT,
            retryable=False,
            provider_status_code=400,
            detail="Shipment already dispatched",
        )
        flow, _, repo = _make_flow(provider_class)
        repo.shipment.status = ShipmentStatus.CREATED

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is False
        assert result["retryable"] is False
        assert repo.shipment.status == ShipmentStatus.CREATED

    async def test_not_cancellable_leaves_state_unchanged(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=False,
            reason=CancelReason.NOT_CANCELLABLE,
            retryable=False,
            provider_status_code=422,
            detail="Cannot cancel collected shipment",
        )
        flow, _, repo = _make_flow(provider_class)
        original_status = ShipmentStatus.LABEL_READY
        repo.shipment.status = original_status

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is False
        assert repo.shipment.status == original_status

    async def test_transient_error_raises_communication_error(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CommunicationError(
            "API timeout",
            context={"retryable": True},
        )
        flow, _, repo = _make_flow(provider_class)
        original_status = ShipmentStatus.CREATED
        repo.shipment.status = original_status

        with pytest.raises(CommunicationError):
            await flow.cancel_shipment(repo.shipment)

        # State should not change on transient failure
        assert repo.shipment.status == original_status

    async def test_transient_error_outcome_raises_communication_error(
        self,
    ) -> None:
        """A provider returning a TRANSIENT_ERROR outcome (instead of
        raising) must still surface as CommunicationError from the flow,
        so callers get one retryable signal regardless of provider style."""
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=False,
            reason=CancelReason.TRANSIENT_ERROR,
            retryable=True,
            provider_status_code=503,
            detail="Service unavailable",
        )
        flow, _, repo = _make_flow(provider_class)
        original_status = ShipmentStatus.CREATED
        repo.shipment.status = original_status

        with pytest.raises(CommunicationError) as exc_info:
            await flow.cancel_shipment(repo.shipment)

        assert exc_info.value.context["provider_status_code"] == 503
        assert repo.shipment.status == original_status

    async def test_cancel_from_new_status(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=True,
            reason=CancelReason.CANCELLED,
            retryable=False,
            provider_status_code=200,
            detail=None,
        )
        flow, _, repo = _make_flow(provider_class)
        repo.shipment.status = ShipmentStatus.NEW

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is True
        assert repo.shipment.status == ShipmentStatus.CANCELLED

    async def test_cancel_from_label_ready_status(self) -> None:
        provider_class = CancelOutcomeTestProvider
        provider_class.cancel_result = CancelOutcome(
            cancelled=True,
            reason=CancelReason.CANCELLED,
            retryable=False,
            provider_status_code=200,
            detail=None,
        )
        flow, _, repo = _make_flow(provider_class)
        repo.shipment.status = ShipmentStatus.LABEL_READY

        result = await flow.cancel_shipment(repo.shipment)

        assert result["cancelled"] is True
        assert repo.shipment.status == ShipmentStatus.CANCELLED
