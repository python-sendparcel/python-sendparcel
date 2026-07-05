"""Shared type definitions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, TypedDict

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


class CancelReason(StrEnum):
    """Reason for a cancel_shipment outcome."""

    CANCELLED = "cancelled"
    ALREADY_CANCELLED = "already_cancelled"
    REFUSED_IN_TRANSIT = "refused_in_transit"
    NOT_CANCELLABLE = "not_cancellable"
    TRANSIENT_ERROR = "transient_error"
    AUTH_ERROR = "auth_error"


class _CancelOutcomeRequired(TypedDict):
    cancelled: bool
    reason: CancelReason
    retryable: bool


class CancelOutcome(_CancelOutcomeRequired, total=False):
    """Structured result from cancel_shipment.

    Replaces the bare bool return so callers can distinguish permanent
    denies (REFUSED_IN_TRANSIT, NOT_CANCELLABLE) from retryable failures
    (TRANSIENT_ERROR).
    """

    provider_status_code: int | None
    detail: str | None


class GeoPoint(TypedDict):
    """Geographic coordinate pair."""

    lat: float
    lng: float


class _PickupPointRequired(TypedDict):
    code: str
    name: str
    provider_slug: str
    address: str


class PickupPoint(_PickupPointRequired, total=False):
    """Carrier pickup point (locker, parcel shop, etc.).

    ``code`` is the machine id used as ``target_point`` in
    ``create_shipment``, so a searched point is directly usable
    without translation.
    """

    location: GeoPoint | None
    opening_hours: str | None
    point_type: str | None
    raw: dict[str, Any] | None


class _QuoteRequired(TypedDict):
    provider_slug: str
    service: str
    amount: Decimal
    currency: str


class Quote(_QuoteRequired, total=False):
    """Shipping rate quote from a carrier.

    ``amount`` is the carrier cost in the provider's currency.
    Use ``Decimal`` — never ``float`` — for monetary values.
    """

    valid_until: str | None
    raw: dict[str, Any] | None


@dataclass(slots=True)
class CallbackContext:
    """Everything needed to process a webhook callback.

    Framework layers build this in one place. Core operates on it.
    The retry store persists this as a single blob.

    The ``dedup_hash`` is computed from the payload alone (not headers
    or source_ip) so that legitimate re-submissions of the same callback
    data are deduplicated regardless of transport metadata.
    """

    shipment_id: str
    payload: dict[str, Any]
    headers: dict[str, str]
    source_ip: str
    raw_body: bytes
    provider_slug: str = ""

    @property
    def dedup_hash(self) -> str:
        """Deterministic SHA-256 hash of the payload for dedup checks."""
        raw = json.dumps(self.payload, sort_keys=True, default=str).encode(
            "utf-8"
        )
        return hashlib.sha256(raw).hexdigest()
