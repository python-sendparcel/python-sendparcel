"""Shared type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from sendparcel.enums import LabelFormat
from sendparcel.protocols import Shipment


class AddressInfo(TypedDict, total=False):
    """Address payload used by providers."""

    name: str
    line1: str
    line2: str
    city: str
    postal_code: str
    country_code: str
    state: str
    company: str
    phone: str
    email: str
    first_name: str
    last_name: str
    street: str
    building_number: str
    flat_number: str


class _ParcelInfoRequired(TypedDict):
    weight_kg: Decimal


class ParcelInfo(_ParcelInfoRequired, total=False):
    """Parcel dimensions and weight."""

    length_cm: Decimal
    width_cm: Decimal
    height_cm: Decimal


class _LabelInfoRequired(TypedDict):
    format: LabelFormat


class LabelInfo(_LabelInfoRequired, total=False):
    """Shipping label payload returned by providers."""

    url: str
    content_base64: str


class TrackingEvent(TypedDict, total=False):
    """Single tracking timeline event."""

    code: str
    description: str
    occurred_at: str
    location: str


class _ShipmentCreateResultRequired(TypedDict):
    external_id: str


class ShipmentCreateResult(_ShipmentCreateResultRequired, total=False):
    """Provider response for create_shipment."""

    tracking_number: str
    label: LabelInfo


class ShipmentUpdateResult(TypedDict, total=False):
    """Normalized provider update for callback and polling flows."""

    status: str | None
    tracking_number: str
    tracking_events: list[TrackingEvent]


ShipmentStatusResponse = ShipmentUpdateResult


@dataclass(frozen=True, slots=True)
class CreateShipmentOutcome:
    """Flow result for shipment creation."""

    shipment: Shipment
    label: LabelInfo | None = None


@dataclass(frozen=True, slots=True)
class CreateLabelOutcome:
    """Flow result for label creation."""

    shipment: Shipment
    label: LabelInfo


@dataclass(frozen=True, slots=True)
class ShipmentUpdateOutcome:
    """Flow result for callback and polling updates."""

    shipment: Shipment
    update: ShipmentUpdateResult
