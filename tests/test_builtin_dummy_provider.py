"""Built-in dummy provider tests -- comprehensive coverage."""

from decimal import Decimal

import pytest

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import InvalidCallbackError
from sendparcel.fsm import create_shipment_machine
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


def _create_kwargs():
    return dict(
        sender_address=_SENDER, receiver_address=_RECEIVER, parcels=_PARCELS
    )


class DummyShipment:
    """Shipment for dummy provider tests with FSM support."""

    def __init__(self, shipment_id="s-42", status=ShipmentStatus.CREATED):
        self.id = shipment_id
        self.status = status
        self.provider = "dummy"
        self.external_id = ""
        self.tracking_number = ""
        self.label_url = ""


class TestCreateShipment:
    @pytest.mark.asyncio
    async def test_returns_deterministic_ids(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})
        result = await provider.create_shipment(**_create_kwargs())
        assert result["external_id"] == "dummy-s-42"
        assert result["tracking_number"] == "DUMMY-S-42"

    @pytest.mark.asyncio
    async def test_different_shipment_id_gives_different_result(self) -> None:
        provider = DummyProvider(DummyShipment(shipment_id="s-99"), config={})
        result = await provider.create_shipment(**_create_kwargs())
        assert result["external_id"] == "dummy-s-99"
        assert result["tracking_number"] == "DUMMY-S-99"

    @pytest.mark.asyncio
    async def test_result_is_typed(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})
        result = await provider.create_shipment(**_create_kwargs())
        assert isinstance(result, dict)
        assert "external_id" in result


class TestCreateLabel:
    @pytest.mark.asyncio
    async def test_returns_pdf_format(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})
        label = await provider.create_label()
        assert label["format"] == "PDF"

    @pytest.mark.asyncio
    async def test_url_contains_shipment_id(self) -> None:
        provider = DummyProvider(DummyShipment(shipment_id="s-77"), config={})
        label = await provider.create_label()
        assert "s-77.pdf" in label["url"]

    @pytest.mark.asyncio
    async def test_custom_label_base_url(self) -> None:
        provider = DummyProvider(
            DummyShipment(),
            config={"label_base_url": "https://custom.local/labels"},
        )
        label = await provider.create_label()
        assert label["url"].startswith("https://custom.local/labels/")


class TestVerifyCallback:
    @pytest.mark.asyncio
    async def test_accepts_correct_token(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"callback_token": "secret"}
        )
        # Should not raise
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

    @pytest.mark.asyncio
    async def test_rejects_missing_token(self) -> None:
        provider = DummyProvider(
            DummyShipment(), config={"callback_token": "secret"}
        )
        with pytest.raises(InvalidCallbackError, match="BAD TOKEN"):
            await provider.verify_callback({}, headers={})

    @pytest.mark.asyncio
    async def test_default_token_is_dummy_token(self) -> None:
        provider = DummyProvider(DummyShipment(), config={})
        await provider.verify_callback(
            {}, headers={"x-dummy-token": "dummy-token"}
        )


class TestHandleCallback:
    @pytest.mark.asyncio
    async def test_applies_status_transition(self) -> None:
        shipment = DummyShipment(status=ShipmentStatus.CREATED)
        shipment.tracking_number = "TRK-1"
        create_shipment_machine(shipment)
        provider = DummyProvider(shipment, config={})

        await provider.handle_callback({"status": "in_transit"}, headers={})
        assert shipment.status == ShipmentStatus.IN_TRANSIT

    @pytest.mark.asyncio
    async def test_ignores_empty_status(self) -> None:
        shipment = DummyShipment(status=ShipmentStatus.CREATED)
        create_shipment_machine(shipment)
        provider = DummyProvider(shipment, config={})

        await provider.handle_callback({"status": ""}, headers={})
        assert shipment.status == ShipmentStatus.CREATED

    @pytest.mark.asyncio
    async def test_ignores_missing_status(self) -> None:
        shipment = DummyShipment(status=ShipmentStatus.CREATED)
        create_shipment_machine(shipment)
        provider = DummyProvider(shipment, config={})

        await provider.handle_callback({}, headers={})
        assert shipment.status == ShipmentStatus.CREATED

    @pytest.mark.asyncio
    async def test_ignores_invalid_transition(self) -> None:
        """Callback with invalid transition does not raise or crash."""
        shipment = DummyShipment(status=ShipmentStatus.CREATED)
        create_shipment_machine(shipment)
        provider = DummyProvider(shipment, config={})

        await provider.handle_callback({"status": "delivered"}, headers={})
        assert shipment.status == ShipmentStatus.CREATED


class TestFetchShipmentStatus:
    @pytest.mark.asyncio
    async def test_returns_current_status(self) -> None:
        shipment = DummyShipment(status=ShipmentStatus.IN_TRANSIT)
        provider = DummyProvider(shipment, config={})
        response = await provider.fetch_shipment_status()
        assert response["status"] == ShipmentStatus.IN_TRANSIT

    @pytest.mark.asyncio
    async def test_status_override_config(self) -> None:
        shipment = DummyShipment(status=ShipmentStatus.CREATED)
        provider = DummyProvider(
            shipment, config={"status_override": "delivered"}
        )
        response = await provider.fetch_shipment_status()
        assert response["status"] == "delivered"


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


class TestLatencySimulation:
    @pytest.mark.asyncio
    async def test_latency_does_not_crash(self) -> None:
        """With zero latency, operations complete immediately."""
        provider = DummyProvider(DummyShipment(), config={"latency_seconds": 0})
        result = await provider.create_shipment(**_create_kwargs())
        assert result["external_id"]
