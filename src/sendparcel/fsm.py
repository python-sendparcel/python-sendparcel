"""Explicit shipment status transitions."""

from __future__ import annotations

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import InvalidTransitionError
from sendparcel.protocols import Shipment

ALLOWED_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    ShipmentStatus.NEW.value: frozenset(
        {
            ShipmentStatus.CREATED.value,
            ShipmentStatus.CANCELLED.value,
            ShipmentStatus.FAILED.value,
        }
    ),
    ShipmentStatus.CREATED.value: frozenset(
        {
            ShipmentStatus.LABEL_READY.value,
            ShipmentStatus.IN_TRANSIT.value,
            ShipmentStatus.OUT_FOR_DELIVERY.value,
            ShipmentStatus.DELIVERED.value,
            ShipmentStatus.RETURNED.value,
            ShipmentStatus.CANCELLED.value,
            ShipmentStatus.FAILED.value,
        }
    ),
    ShipmentStatus.LABEL_READY.value: frozenset(
        {
            ShipmentStatus.IN_TRANSIT.value,
            ShipmentStatus.OUT_FOR_DELIVERY.value,
            ShipmentStatus.DELIVERED.value,
            ShipmentStatus.RETURNED.value,
            ShipmentStatus.CANCELLED.value,
            ShipmentStatus.FAILED.value,
        }
    ),
    ShipmentStatus.IN_TRANSIT.value: frozenset(
        {
            ShipmentStatus.OUT_FOR_DELIVERY.value,
            ShipmentStatus.DELIVERED.value,
            ShipmentStatus.RETURNED.value,
            ShipmentStatus.FAILED.value,
        }
    ),
    ShipmentStatus.OUT_FOR_DELIVERY.value: frozenset(
        {
            ShipmentStatus.DELIVERED.value,
            ShipmentStatus.RETURNED.value,
            ShipmentStatus.FAILED.value,
        }
    ),
    ShipmentStatus.DELIVERED.value: frozenset({ShipmentStatus.RETURNED.value}),
    ShipmentStatus.CANCELLED.value: frozenset(),
    ShipmentStatus.FAILED.value: frozenset(),
    ShipmentStatus.RETURNED.value: frozenset(),
}


def normalize_status(status: str | ShipmentStatus) -> str:
    """Return a normalized shipment status string."""

    try:
        return ShipmentStatus(status).value
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
        shipment.status = target
        return shipment
    if target not in ALLOWED_STATUS_TRANSITIONS[current]:
        raise InvalidTransitionError(
            f"Shipment cannot transition from {current!r} to {target!r}"
        )
    shipment.status = target
    return shipment
