"""Shared type definitions."""

from decimal import Decimal
from typing import TypedDict


class AddressInfo(TypedDict, total=False):
    """Address payload used by providers."""

    name: str
    company: str
    line1: str
    line2: str
    city: str
    state: str
    postal_code: str
    country_code: str
    phone: str
    email: str


class ParcelInfo(TypedDict, total=False):
    """Parcel dimensions and weight."""

    weight_kg: Decimal
    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal


class LabelInfo(TypedDict, total=False):
    """Shipping label metadata."""

    format: str
    url: str
    content_base64: str


class TrackingEvent(TypedDict, total=False):
    """Single tracking timeline event."""

    code: str
    description: str
    occurred_at: str
    location: str


class ShipmentCreateResult(TypedDict, total=False):
    """Provider response for create_shipment."""

    external_id: str
    tracking_number: str
    label: LabelInfo


class ShipmentStatusResponse(TypedDict, total=False):
    """Provider response for fetch_shipment_status."""

    status: str | None
    tracking_events: list[TrackingEvent]
