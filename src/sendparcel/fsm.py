"""Shipment state machine definitions."""

from transitions import Machine

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
    },
    {
        "trigger": "mark_in_transit",
        "source": [ShipmentStatus.CREATED, ShipmentStatus.LABEL_READY],
        "dest": ShipmentStatus.IN_TRANSIT,
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


def create_shipment_machine(shipment) -> Machine:
    """Attach shipment FSM to shipment object."""
    initial = (
        ShipmentStatus(shipment.status)
        if shipment.status
        else ShipmentStatus.NEW
    )
    return Machine(
        model=shipment,
        states=ShipmentStatus,
        transitions=SHIPMENT_TRANSITIONS,
        initial=initial,
        model_attribute="status",
        auto_transitions=False,
    )
