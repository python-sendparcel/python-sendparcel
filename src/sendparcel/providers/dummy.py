"""Deterministic built-in dummy provider implementation."""

from __future__ import annotations

from typing import Any, ClassVar

import anyio

from sendparcel.enums import ConfirmationMethod, LabelFormat
from sendparcel.exceptions import InvalidCallbackError
from sendparcel.provider import (
    BaseProvider,
    CancellableProvider,
    LabelProvider,
    PullStatusProvider,
    PushCallbackProvider,
)
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentUpdateResult,
)


class DummyProvider(
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider,
):
    """Reference provider for local, development, and test usage."""

    slug: ClassVar[str] = "dummy"
    display_name: ClassVar[str] = "Dummy"
    supported_countries: ClassVar[list[str]] = ["PL", "DE", "US"]
    supported_services: ClassVar[list[str]] = ["standard", "express"]
    confirmation_method: ClassVar[ConfirmationMethod] = ConfirmationMethod.PUSH

    def _label_url(self) -> str:
        base = self.get_setting("label_base_url", "https://dummy.local/labels")
        return f"{str(base).rstrip('/')}/{self.shipment.id}.pdf"

    async def _simulate_latency(self) -> None:
        delay = float(self.get_setting("latency_seconds", 0.0))
        await anyio.sleep(delay)

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        await self._simulate_latency()
        shipment_id = str(self.shipment.id)
        return ShipmentCreateResult(
            external_id=f"dummy-{shipment_id}",
            tracking_number=f"DUMMY-{shipment_id.upper()}",
        )

    async def create_label(self, **kwargs: Any) -> LabelInfo:
        await self._simulate_latency()
        return LabelInfo(format=LabelFormat.PDF, url=self._label_url())

    async def verify_callback(self, ctx: CallbackContext) -> None:
        expected = self.get_setting("callback_token", "dummy-token")
        provided = ctx.headers.get("x-dummy-token", "")
        if provided != expected:
            raise InvalidCallbackError("BAD TOKEN")

    async def handle_callback(self, ctx: CallbackContext) -> ShipmentUpdateResult:
        await self._simulate_latency()
        status_value = ctx.payload.get("status")
        if not status_value:
            return ShipmentUpdateResult()
        return ShipmentUpdateResult(status=str(status_value))

    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentUpdateResult:
        await self._simulate_latency()
        return ShipmentUpdateResult(
            status=self.get_setting("status_override", self.shipment.status)
        )

    async def cancel_shipment(self, **kwargs: Any) -> bool:
        await self._simulate_latency()
        return bool(self.get_setting("cancel_success", True))
