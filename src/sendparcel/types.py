"""Shared type definitions."""

from decimal import Decimal
from typing import TypedDict

from sendparcel.enums import LabelFormat


class AddressInfo(TypedDict, total=False):
    """Address payload used by providers.

    All fields are optional to support diverse provider address models.
    Providers validate required fields at their own layer.

    Common patterns:
    - Generic: name + line1 + city + postal_code + country_code
    - InPost:  first_name + last_name + street + building_number
               + city + postal_code + country_code
    """

    # Generic / legacy fields
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

    # Structured name fields (InPost and others)
    first_name: str
    last_name: str

    # Structured address fields (InPost and others)
    street: str
    building_number: str
    flat_number: str


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

    format: LabelFormat


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
