"""FSM transition tests."""

import pytest
from transitions.core import MachineError

from sendparcel.enums import ShipmentStatus
from sendparcel.fsm import ALLOWED_CALLBACKS, create_shipment_machine


def test_happy_path_transitions() -> None:
    class Shipment:
        status = ShipmentStatus.NEW

    shipment = Shipment()
    create_shipment_machine(shipment)

    shipment.confirm_created()
    assert shipment.status == ShipmentStatus.CREATED

    shipment.confirm_label()
    assert shipment.status == ShipmentStatus.LABEL_READY

    shipment.mark_in_transit()
    shipment.mark_out_for_delivery()
    shipment.mark_delivered()

    assert shipment.status == ShipmentStatus.DELIVERED


def test_invalid_transition_raises_machine_error() -> None:
    class Shipment:
        status = ShipmentStatus.NEW

    shipment = Shipment()
    create_shipment_machine(shipment)

    with pytest.raises(MachineError):
        shipment.mark_delivered()


def test_allowed_callbacks_contains_expected_triggers() -> None:
    assert "confirm_created" in ALLOWED_CALLBACKS
    assert "confirm_label" in ALLOWED_CALLBACKS
    assert "mark_in_transit" in ALLOWED_CALLBACKS
    assert "mark_delivered" in ALLOWED_CALLBACKS
    assert "cancel" in ALLOWED_CALLBACKS
    assert "fail" in ALLOWED_CALLBACKS
