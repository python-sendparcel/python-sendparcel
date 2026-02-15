"""Shared type definitions."""

from decimal import Decimal
from typing import TypedDict


class _AddressInfoRequired(TypedDict):
    """Required address fields."""

    name: str
    line1: str
    city: str
    postal_code: str
    country_code: str


class AddressInfo(_AddressInfoRequired, total=False):
    """Address payload used by providers."""

    company: str
    line2: str
    state: str
    phone: str
    email: str


class _ParcelInfoRequired(TypedDict):
    """Required parcel fields."""

    weight_kg: Decimal


class ParcelInfo(_ParcelInfoRequired, total=False):
    """Parcel dimensions and weight."""

    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal


class _LabelInfoRequired(TypedDict):
    """Required label fields."""

    format: str


class LabelInfo(_LabelInfoRequired, total=False):
    """Shipping label metadata."""

    url: str
    content_base64: str


class TrackingEvent(TypedDict, total=False):
    """Single tracking timeline event."""

    code: str
    description: str
    occurred_at: str
    location: str


class _ShipmentCreateResultRequired(TypedDict):
    """Required result fields."""

    external_id: str


class ShipmentCreateResult(_ShipmentCreateResultRequired, total=False):
    """Provider response for create_shipment."""

    tracking_number: str
    label: LabelInfo


class ShipmentStatusResponse(TypedDict, total=False):
    """Provider response for fetch_shipment_status."""

    status: str | None
    tracking_events: list[TrackingEvent]
