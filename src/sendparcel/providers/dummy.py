"""Deterministic built-in dummy provider implementation."""

from typing import Any, ClassVar

import anyio

from sendparcel.enums import LabelFormat
from sendparcel.exceptions import InvalidCallbackError
from sendparcel.fsm import STATUS_TO_CALLBACK
from sendparcel.provider import (
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider,
)
from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentStatusResponse,
)


class DummyProvider(
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider,
):
    """Reference provider for local/dev/testing usage."""

    slug: ClassVar[str] = "dummy"
    display_name: ClassVar[str] = "Dummy"
    supported_countries: ClassVar[list[str]] = ["PL", "DE", "US"]
    supported_services: ClassVar[list[str]] = ["standard", "express"]

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

    async def verify_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        expected = self.get_setting("callback_token", "dummy-token")
        provided = headers.get("x-dummy-token", "")
        if provided != expected:
            raise InvalidCallbackError("BAD TOKEN")

    async def handle_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        await self._simulate_latency()
        status_value = data.get("status")
        if not status_value:
            return

        callback = STATUS_TO_CALLBACK.get(str(status_value), str(status_value))
        trigger = getattr(self.shipment, callback, None)
        may_trigger = getattr(self.shipment, "may_trigger", None)
        if trigger is None or may_trigger is None:
            return
        if may_trigger(callback):
            trigger()

    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentStatusResponse:
        await self._simulate_latency()
        return ShipmentStatusResponse(
            status=self.get_setting("status_override", self.shipment.status),
        )

    async def cancel_shipment(self, **kwargs: Any) -> bool:
        await self._simulate_latency()
        return bool(self.get_setting("cancel_success", True))
