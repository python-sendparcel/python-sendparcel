"""Flow integration tests."""

from decimal import Decimal
from typing import Any

import pytest

from conftest import InMemoryRepository
from sendparcel.enums import LabelFormat
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.registry import registry
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentUpdateResult,
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


class IntegrationProvider(BaseProvider):
    slug = "integration"
    display_name = "Integration Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(
            external_id="int-1",
            tracking_number="trk-int-1",
        )

    async def create_label(self, **kwargs: Any) -> LabelInfo:
        return LabelInfo(format=LabelFormat.PDF, url="https://labels/int.pdf")

    async def verify_callback(
        self, ctx: CallbackContext
    ) -> None:
        return None

    async def handle_callback(
        self, ctx: CallbackContext
    ) -> ShipmentUpdateResult:
        return ShipmentUpdateResult(
            status=str(ctx.payload["status"]),
            tracking_events=[{"code": "callback"}],
        )

    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentUpdateResult:
        return ShipmentUpdateResult(
            status=self.get_setting("poll_status", "delivered"),
            tracking_events=[{"code": "poll"}],
        )

    async def cancel_shipment(self, **kwargs: Any) -> bool:
        return bool(self.get_setting("cancel_success", True))


class InlineLabelProvider(IntegrationProvider):
    slug = "inline-label"
    display_name = "Inline Label Provider"

    async def create_shipment(
        self,
        *,
        sender_address: Any,
        receiver_address: Any,
        parcels: Any,
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(
            external_id="inline-1",
            tracking_number="trk-inline-1",
            label=LabelInfo(
                format=LabelFormat.PDF,
                url="https://labels/inline.pdf",
            ),
        )


def _flow(
    provider_cls: type[BaseProvider],
    *,
    config: dict[str, Any] | None = None,
) -> tuple[ShipmentFlow, InMemoryRepository]:
    repository = InMemoryRepository()
    registry.register(provider_cls)
    return ShipmentFlow(repository=repository, config=config), repository


def _create_kwargs() -> dict[str, Any]:
    return dict(
        sender_address=_SENDER,
        receiver_address=_RECEIVER,
        parcels=_PARCELS,
    )


@pytest.mark.asyncio
async def test_full_flow_uses_payload_outcomes_without_persisted_label() -> (
    None
):
    flow, repository = _flow(IntegrationProvider)

    created = await flow.create_shipment("integration", **_create_kwargs())
    assert created.shipment.status == "created"

    labelled = await flow.create_label(created.shipment)
    assert labelled.shipment.status == "label_ready"

    callback = await flow.handle_callback(
        CallbackContext(
            shipment_id=labelled.shipment.id,
            payload={"status": "in_transit"},
            headers={},
            source_ip="127.0.0.1",
            raw_body=b"",
        ),
    )
    assert callback.shipment.status == "in_transit"

    polled = await flow.fetch_and_update_status(callback.shipment)

    assert labelled.label.get("url") == "https://labels/int.pdf"
    assert callback.update == {
        "status": "in_transit",
        "tracking_events": [{"code": "callback"}],
    }
    assert polled.shipment.status == "delivered"
    assert repository.save_count == 1
    assert repository.update_fields_count == 3


@pytest.mark.asyncio
async def test_inline_label_create_shipment_returns_label_payload() -> None:
    flow, _ = _flow(InlineLabelProvider)

    outcome = await flow.create_shipment("inline-label", **_create_kwargs())

    assert outcome.shipment.status == "label_ready"
    assert outcome.label is not None
    assert outcome.label.get("url") == "https://labels/inline.pdf"


@pytest.mark.asyncio
async def test_callback_and_polling_share_same_normalized_shape() -> None:
    flow, _ = _flow(
        IntegrationProvider,
        config={"integration": {"poll_status": "out_for_delivery"}},
    )
    shipment = (
        await flow.create_shipment("integration", **_create_kwargs())
    ).shipment

    callback = await flow.handle_callback(
        CallbackContext(
            shipment_id=shipment.id,
            payload={"status": "in_transit"},
            headers={},
            source_ip="127.0.0.1",
            raw_body=b"",
        ),
    )
    polled = await flow.fetch_and_update_status(callback.shipment)

    assert set(callback.update) == {"status", "tracking_events"}
    assert set(polled.update) == {"status", "tracking_events"}
    assert polled.shipment.status == "out_for_delivery"


@pytest.mark.asyncio
async def test_cancel_rejection_keeps_current_status() -> None:
    flow, _ = _flow(
        IntegrationProvider,
        config={"integration": {"cancel_success": False}},
    )
    shipment = (
        await flow.create_shipment("integration", **_create_kwargs())
    ).shipment

    cancelled = await flow.cancel_shipment(shipment)

    assert cancelled is False
    assert shipment.status == "created"
