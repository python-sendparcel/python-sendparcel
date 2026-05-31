"""Explicit shipment status transitions."""

from __future__ import annotations

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import InvalidTransitionError
from sendparcel.protocols import Shipment

ALLOWED_STATUS_TRANSITIONS: dict[ShipmentStatus, frozenset[ShipmentStatus]] = {
    ShipmentStatus.NEW: frozenset(
        {
            ShipmentStatus.CREATED,
            ShipmentStatus.CANCELLED,
            ShipmentStatus.FAILED,
            ShipmentStatus.SUBMITTED,
        }
    ),
    ShipmentStatus.CREATED: frozenset(
        {
            ShipmentStatus.LABEL_READY,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED,
            ShipmentStatus.CANCELLED,
            ShipmentStatus.FAILED,
        }
    ),
    ShipmentStatus.LABEL_READY: frozenset(
        {
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED,
            ShipmentStatus.CANCELLED,
            ShipmentStatus.FAILED,
        }
    ),
    ShipmentStatus.IN_TRANSIT: frozenset(
        {
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED,
            ShipmentStatus.FAILED,
        }
    ),
    ShipmentStatus.OUT_FOR_DELIVERY: frozenset(
        {
            ShipmentStatus.DELIVERED,
            ShipmentStatus.RETURNED,
            ShipmentStatus.FAILED,
        }
    ),
    ShipmentStatus.DELIVERED: frozenset({ShipmentStatus.RETURNED}),
    ShipmentStatus.CANCELLED: frozenset(),
    ShipmentStatus.FAILED: frozenset(),
    ShipmentStatus.RETURNED: frozenset(),
    ShipmentStatus.SUBMITTED: frozenset(
        {
            ShipmentStatus.CREATED,
            ShipmentStatus.FAILED,
        }
    ),
}


def normalize_status(status: str | ShipmentStatus) -> ShipmentStatus:
    """Normalise a status to a :class:`ShipmentStatus` enum member."""

    try:
        return ShipmentStatus(status)
    except ValueError as exc:
        raise InvalidTransitionError(
            f"Unknown shipment status {status!r}"
        ) from exc


def can_transition(
    current_status: str | ShipmentStatus,
    target_status: str | ShipmentStatus,
) -> bool:
    """Check whether a shipment status transition is allowed."""

    current = normalize_status(current_status)
    target = normalize_status(target_status)
    if current == target:
        return True
    return target in ALLOWED_STATUS_TRANSITIONS[current]


def transition_shipment(
    shipment: Shipment, target_status: str | ShipmentStatus
) -> Shipment:
    """Apply a validated status transition to a shipment."""

    current = normalize_status(shipment.status)
    target = normalize_status(target_status)
    if current == target:
        shipment.status = target.value
        return shipment
    if target not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"Shipment cannot transition from {current!r} to {target!r}"
        )
    shipment.status = target.value
    return shipment
