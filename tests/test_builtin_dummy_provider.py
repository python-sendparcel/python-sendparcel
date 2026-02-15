"""Built-in dummy provider tests."""

import pytest

from sendparcel.exceptions import InvalidCallbackError
from sendparcel.providers.dummy import DummyProvider


class DemoOrder:
    def get_total_weight(self):
        return 1

    def get_parcels(self):
        return []

    def get_sender_address(self):
        return {}

    def get_receiver_address(self):
        return {}


class DemoShipment:
    id = "s-42"
    order = DemoOrder()
    status = "created"
    provider = "dummy"
    external_id = ""
    tracking_number = ""
    label_url = ""


@pytest.mark.asyncio
async def test_create_shipment_is_deterministic() -> None:
    provider = DummyProvider(DemoShipment(), config={})
    result = await provider.create_shipment()

    assert result["external_id"] == "dummy-s-42"
    assert result["tracking_number"] == "DUMMY-S-42"


@pytest.mark.asyncio
async def test_create_label_uses_shipment_id() -> None:
    provider = DummyProvider(DemoShipment(), config={})
    label = await provider.create_label()

    assert label["format"] == "PDF"
    assert label["url"].endswith("/s-42.pdf")


@pytest.mark.asyncio
async def test_verify_callback_rejects_bad_token() -> None:
    provider = DummyProvider(DemoShipment(), config={"callback_token": "good"})

    with pytest.raises(InvalidCallbackError, match="BAD TOKEN"):
        await provider.verify_callback({}, headers={"x-dummy-token": "bad"})
