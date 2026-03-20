"""Built-in dummy provider tests."""

from decimal import Decimal
from typing import Any

import pytest

from sendparcel.enums import ConfirmationMethod
from sendparcel.exceptions import InvalidCallbackError
from sendparcel.providers.dummy import DummyProvider
from sendparcel.types import AddressInfo, ParcelInfo

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

        await provider.verify_callback({}, headers={"x-dummy-token": "secret"})

    @pytest.mark.asyncio
    async def test_rejects_wrong_token(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"callback_token": "secret"}
        )

        with pytest.raises(InvalidCallbackError, match="BAD TOKEN"):
            await provider.verify_callback(
                {}, headers={"x-dummy-token": "wrong"}
            )


class TestHandleCallback:
    @pytest.mark.asyncio
    async def test_returns_normalized_update(self) -> None:
        provider = DummyProvider(DummyShipment(status="created"), config={})

        update = await provider.handle_callback(
            {"status": "in_transit"}, headers={}
        )

        assert update == {"status": "in_transit"}

    @pytest.mark.asyncio
    async def test_missing_status_returns_empty_update(self) -> None:
        provider = DummyProvider(DummyShipment(status="created"), config={})

        update = await provider.handle_callback({}, headers={})

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
    async def test_cancel_returns_true_by_default(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})

        result = await provider.cancel_shipment()

        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_can_be_configured_to_fail(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"cancel_success": False}
        )

        result = await provider.cancel_shipment()

        assert result is False
