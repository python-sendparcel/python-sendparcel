"""Base provider tests."""

import pytest

from conftest import DemoShipment
from sendparcel.enums import ConfirmationMethod
from sendparcel.provider import BaseProvider


class MinimalProvider(BaseProvider):
    slug = "minimal"
    display_name = "Minimal"

    async def create_shipment(self, **kwargs):
        return {"external_id": "ex-1", "tracking_number": "trk-1"}


def test_get_setting_reads_config() -> None:
    provider = MinimalProvider(DemoShipment(), config={"token": "abc"})

    assert provider.get_setting("token") == "abc"
    assert provider.get_setting("missing", "fallback") == "fallback"


@pytest.mark.asyncio
async def test_optional_methods_default_to_not_implemented() -> None:
    provider = MinimalProvider(DemoShipment(), config={})

    with pytest.raises(NotImplementedError):
        await provider.create_label()
    with pytest.raises(NotImplementedError):
        await provider.handle_callback({}, {})
    with pytest.raises(NotImplementedError):
        await provider.fetch_shipment_status()
    with pytest.raises(NotImplementedError):
        await provider.cancel_shipment()


class TestConfirmationMethodOnProvider:
    def test_default_confirmation_method_is_push(self) -> None:
        provider = MinimalProvider(DemoShipment(), config={})
        assert provider.confirmation_method == ConfirmationMethod.PUSH

    def test_confirmation_method_is_class_var(self) -> None:
        assert MinimalProvider.confirmation_method == ConfirmationMethod.PUSH
