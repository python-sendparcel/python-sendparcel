"""Built-in dummy provider tests."""

from decimal import Decimal
from typing import Any

import pytest

from sendparcel.enums import ConfirmationMethod
from sendparcel.exceptions import InvalidCallbackError
from sendparcel.providers.dummy import DummyProvider
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    CancelReason,
    ParcelInfo,
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


def _create_kwargs() -> dict[str, Any]:
    return dict(
        sender_address=_SENDER,
        receiver_address=_RECEIVER,
        parcels=_PARCELS,
    )


class DummyShipment:
    def __init__(
        self, shipment_id: str = "s-42", status: str = "created"
    ) -> None:
        self.id = shipment_id
        self.status = status
        self.provider = "dummy"
        self.external_id = ""
        self.tracking_number = ""


class TestCreateShipment:
    def test_confirmation_method_is_push(self) -> None:
        assert DummyProvider.confirmation_method == ConfirmationMethod.PUSH

    @pytest.mark.asyncio
    async def test_returns_deterministic_ids(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})

        result = await provider.create_shipment(**_create_kwargs())

        assert result["external_id"] == "dummy-s-42"
        assert result.get("tracking_number") == "DUMMY-S-42"


class TestCreateLabel:
    @pytest.mark.asyncio
    async def test_returns_pdf_format(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})

        label = await provider.create_label()

        assert label["format"] == "PDF"

    @pytest.mark.asyncio
    async def test_custom_label_base_url(self) -> None:
        provider = DummyProvider(
            DummyShipment(),
            config={"label_base_url": "https://custom.local/labels"},
        )

        label = await provider.create_label()

        assert str(label.get("url", "")).startswith(
            "https://custom.local/labels/"
        )


class TestVerifyCallback:
    @pytest.mark.asyncio
    async def test_accepts_correct_token(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"callback_token": "secret"}
        )
        ctx = CallbackContext(
            shipment_id="s-42",
            payload={},
            headers={"x-dummy-token": "secret"},
            source_ip="127.0.0.1",
            raw_body=b"",
        )
        await provider.verify_callback(ctx)

    @pytest.mark.asyncio
    async def test_rejects_wrong_token(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"callback_token": "secret"}
        )
        ctx = CallbackContext(
            shipment_id="s-42",
            payload={},
            headers={"x-dummy-token": "wrong"},
            source_ip="127.0.0.1",
            raw_body=b"",
        )
        with pytest.raises(InvalidCallbackError, match="BAD TOKEN"):
            await provider.verify_callback(ctx)


class TestHandleCallback:
    @pytest.mark.asyncio
    async def test_returns_normalized_update(self) -> None:
        provider = DummyProvider(DummyShipment(status="created"), config={})
        ctx = CallbackContext(
            shipment_id="s-42",
            payload={"status": "in_transit"},
            headers={},
            source_ip="127.0.0.1",
            raw_body=b"",
        )
        update = await provider.handle_callback(ctx)
        assert update == {"status": "in_transit"}

    @pytest.mark.asyncio
    async def test_missing_status_returns_empty_update(self) -> None:
        provider = DummyProvider(DummyShipment(status="created"), config={})
        ctx = CallbackContext(
            shipment_id="s-42",
            payload={},
            headers={},
            source_ip="127.0.0.1",
            raw_body=b"",
        )
        update = await provider.handle_callback(ctx)
        assert update == {}


class TestFetchShipmentStatus:
    @pytest.mark.asyncio
    async def test_returns_current_status(self) -> None:
        shipment = DummyShipment(status="in_transit")
        provider = DummyProvider(shipment, config={})

        response = await provider.fetch_shipment_status()

        assert response.get("status") == "in_transit"

    @pytest.mark.asyncio
    async def test_status_override_config(self) -> None:
        shipment = DummyShipment(status="created")
        provider = DummyProvider(
            shipment, config={"status_override": "delivered"}
        )

        response = await provider.fetch_shipment_status()

        assert response.get("status") == "delivered"


class TestCancelShipment:
    @pytest.mark.asyncio
    async def test_cancel_returns_outcome_by_default(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})

        outcome = await provider.cancel_shipment()

        assert outcome["cancelled"] is True
        assert outcome["reason"] == CancelReason.CANCELLED
        assert outcome["retryable"] is False

    @pytest.mark.asyncio
    async def test_cancel_can_be_configured_to_refuse(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"cancel_success": False}
        )

        outcome = await provider.cancel_shipment()

        assert outcome["cancelled"] is False
        assert outcome["reason"] == CancelReason.NOT_CANCELLABLE
        assert outcome["retryable"] is False

    @pytest.mark.asyncio
    async def test_cancel_reason_is_configurable(self) -> None:
        provider = DummyProvider(
            DummyShipment(),
            config={
                "cancel_success": False,
                "cancel_reason": "refused_in_transit",
            },
        )

        outcome = await provider.cancel_shipment()

        assert outcome["cancelled"] is False
        assert outcome["reason"] == CancelReason.REFUSED_IN_TRANSIT
