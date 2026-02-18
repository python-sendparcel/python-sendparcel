"""Shipment state machine definitions.

Triggers:
- confirm_created: NEW → CREATED
- confirm_label: CREATED → LABEL_READY (requires label_url)
- mark_in_transit: CREATED|LABEL_READY → IN_TRANSIT (requires tracking_number)
- mark_out_for_delivery: IN_TRANSIT → OUT_FOR_DELIVERY
- mark_delivered: IN_TRANSIT|OUT_FOR_DELIVERY → DELIVERED
- mark_returned: IN_TRANSIT|OUT_FOR_DELIVERY|DELIVERED → RETURNED
- cancel: NEW|CREATED|LABEL_READY → CANCELLED
- fail: NEW|CREATED|LABEL_READY|IN_TRANSIT|OUT_FOR_DELIVERY → FAILED
  (also used for callback retry exhaustion)

Retry Exhaustion:
When callback retries are exhausted, transition to FAILED via the "fail" trigger.
This reuses the existing failure pathway — no new status needed.
"""

from typing import Any

from transitions import Machine
from transitions.core import EventData, MachineError

from sendparcel.enums import ShipmentStatus

CALLBACK_NAMES = (
    "confirm_created",
    "confirm_label",
    "mark_in_transit",
    "mark_out_for_delivery",
    "mark_delivered",
    "mark_returned",
    "cancel",
    "fail",
)


def _require_label_url(event_data: EventData) -> None:
    """Guard: reject confirm_label if shipment has no label_url."""
    model = event_data.model
    if not getattr(model, "label_url", ""):
        raise MachineError(
            f"Transition '{event_data.event.name}'"
            " requires label_url to be set."
        )


def _require_tracking_number(event_data: EventData) -> None:
    """Guard: reject mark_in_transit if shipment has no tracking_number."""
    model = event_data.model
    if not getattr(model, "tracking_number", ""):
        raise MachineError(
            f"Transition '{event_data.event.name}'"
            " requires tracking_number to be set."
        )


SHIPMENT_TRANSITIONS = [
    {
        "trigger": "confirm_created",
        "source": ShipmentStatus.NEW,
        "dest": ShipmentStatus.CREATED,
    },
    {
        "trigger": "confirm_label",
        "source": ShipmentStatus.CREATED,
        "dest": ShipmentStatus.LABEL_READY,
        "before": _require_label_url,
    },
    {
        "trigger": "mark_in_transit",
        "source": [ShipmentStatus.CREATED, ShipmentStatus.LABEL_READY],
        "dest": ShipmentStatus.IN_TRANSIT,
        "before": _require_tracking_number,
    },
    {
        "trigger": "mark_out_for_delivery",
        "source": ShipmentStatus.IN_TRANSIT,
        "dest": ShipmentStatus.OUT_FOR_DELIVERY,
    },
    {
        "trigger": "mark_delivered",
        "source": [
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
        ],
        "dest": ShipmentStatus.DELIVERED,
    },
    {
        "trigger": "mark_returned",
        "source": [
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
            ShipmentStatus.DELIVERED,
        ],
        "dest": ShipmentStatus.RETURNED,
    },
    {
        "trigger": "cancel",
        "source": [
            ShipmentStatus.NEW,
            ShipmentStatus.CREATED,
            ShipmentStatus.LABEL_READY,
        ],
        "dest": ShipmentStatus.CANCELLED,
    },
    {
        "trigger": "fail",
        "source": [
            ShipmentStatus.NEW,
            ShipmentStatus.CREATED,
            ShipmentStatus.LABEL_READY,
            ShipmentStatus.IN_TRANSIT,
            ShipmentStatus.OUT_FOR_DELIVERY,
        ],
        "dest": ShipmentStatus.FAILED,
    },
]

ALLOWED_CALLBACKS: frozenset[str] = frozenset(CALLBACK_NAMES)

STATUS_TO_CALLBACK: dict[str, str] = {
    ShipmentStatus.CREATED.value: "confirm_created",
    ShipmentStatus.LABEL_READY.value: "confirm_label",
    ShipmentStatus.IN_TRANSIT.value: "mark_in_transit",
    ShipmentStatus.OUT_FOR_DELIVERY.value: "mark_out_for_delivery",
    ShipmentStatus.DELIVERED.value: "mark_delivered",
    ShipmentStatus.RETURNED.value: "mark_returned",
    ShipmentStatus.CANCELLED.value: "cancel",
    ShipmentStatus.FAILED.value: "fail",
}


def create_shipment_machine(shipment: Any) -> Machine:
    """Attach shipment FSM to shipment object."""
    initial = (
        ShipmentStatus(shipment.status)
        if shipment.status
        else ShipmentStatus.NEW
    )
    return Machine(
        model=shipment,
        states=ShipmentStatus,
        transitions=SHIPMENT_TRANSITIONS,  # type: ignore[arg-type]  # transitions library expects complex union type
        initial=initial,
        model_attribute="status",
        auto_transitions=False,
        send_event=True,
    )
