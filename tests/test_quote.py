"""Tests for get_quote capability."""

from __future__ import annotations

from decimal import Decimal

import pytest

from sendparcel.exceptions import ProviderCapabilityError
from sendparcel.provider import BaseProvider
from sendparcel.types import (
    AddressInfo,
    ParcelInfo,
    Quote,
    ShipmentCreateResult,
)


class DummyShipment:
    id = "ship-1"
    status = "new"
    provider = "no-quote"
    external_id = ""
    tracking_number = ""


class NoQuoteProvider(BaseProvider):
    """Provider that does not support get_quote."""

    slug = "no-quote"
    display_name = "No Quote"

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs,
    ) -> ShipmentCreateResult:
        return {"external_id": "ext-1"}


class TestGetQuote:
    """BaseProvider.get_quote raises ProviderCapabilityError by default."""

    async def test_default_raises_capability_error(self) -> None:
        provider = NoQuoteProvider(shipment=DummyShipment())
        with pytest.raises(ProviderCapabilityError):
            await provider.get_quote(
                service="standard",
                parcels=[{"weight_kg": Decimal("1.0")}],
            )

    async def test_error_message_names_provider(self) -> None:
        provider = NoQuoteProvider(shipment=DummyShipment())
        with pytest.raises(ProviderCapabilityError) as exc_info:
            await provider.get_quote(
                service="standard",
                parcels=[{"weight_kg": Decimal("1.0")}],
            )
        assert "NoQuoteProvider" in str(exc_info.value)


class TestQuoteType:
    """Quote TypedDict shape tests."""

    def test_quote_shape(self) -> None:
        quote: Quote = {
            "provider_slug": "test",
            "service": "standard",
            "amount": Decimal("12.50"),
            "currency": "PLN",
            "valid_until": None,
            "raw": None,
        }
        assert quote["amount"] == Decimal("12.50")
        assert quote["currency"] == "PLN"

    def test_quote_amount_is_decimal(self) -> None:
        quote: Quote = {
            "provider_slug": "test",
            "service": "express",
            "amount": Decimal("25.00"),
            "currency": "EUR",
        }
        assert isinstance(quote["amount"], Decimal)
