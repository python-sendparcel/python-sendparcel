"""Base provider tests."""

from typing import Any, ClassVar

import pytest

from conftest import DemoShipment
from sendparcel.enums import ConfirmationMethod
from sendparcel.provider import BaseProvider
from sendparcel.types import ShipmentCreateResult


class MinimalProvider(BaseProvider):
    slug = "minimal"
    display_name = "Minimal"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="ex-1", tracking_number="trk-1")


def test_get_setting_reads_config() -> None:
    provider = MinimalProvider(DemoShipment(), config={"token": "abc"})

    assert provider.get_setting("token") == "abc"
    assert provider.get_setting("missing", "fallback") == "fallback"


class TestConfirmationMethodOnProvider:
    def test_default_confirmation_method_is_push(self) -> None:
        provider = MinimalProvider(DemoShipment(), config={})
        assert provider.confirmation_method == ConfirmationMethod.PUSH

    def test_confirmation_method_is_class_var(self) -> None:
        assert MinimalProvider.confirmation_method == ConfirmationMethod.PUSH


class TestConfigSchema:
    def test_base_provider_has_empty_config_schema(self) -> None:
        assert hasattr(BaseProvider, "config_schema")
        assert BaseProvider.config_schema == {}

    def test_subclass_can_declare_config_schema(self) -> None:
        class TestProvider(BaseProvider):
            slug = "test"
            display_name = "Test"
            config_schema: ClassVar[dict[str, Any]] = {
                "api_key": {
                    "type": "str",
                    "required": True,
                    "secret": True,
                    "description": "API key for authentication",
                },
                "sandbox": {
                    "type": "bool",
                    "required": False,
                    "secret": False,
                    "description": "Use sandbox environment",
                    "default": False,
                },
            }

            async def create_shipment(
                self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any
            ) -> ShipmentCreateResult:
                return ShipmentCreateResult(external_id="test-1")

        assert TestProvider.config_schema["api_key"]["required"] is True
        assert TestProvider.config_schema["api_key"]["secret"] is True
        assert TestProvider.config_schema["sandbox"]["default"] is False

    def test_subclass_without_schema_inherits_empty(self) -> None:
        class MinimalProvider(BaseProvider):
            slug = "minimal"
            display_name = "Minimal"

            async def create_shipment(
                self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any
            ) -> ShipmentCreateResult:
                return ShipmentCreateResult(external_id="m-1")

        assert MinimalProvider.config_schema == {}
