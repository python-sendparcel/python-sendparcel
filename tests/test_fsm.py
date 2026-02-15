"""FSM transition tests."""

import pytest
from transitions.core import MachineError

from sendparcel.enums import ShipmentStatus
from sendparcel.fsm import ALLOWED_CALLBACKS, create_shipment_machine


def test_happy_path_transitions() -> None:
    class Shipment:
        status = ShipmentStatus.NEW
        label_url = "https://example.com/label.pdf"
        tracking_number = "TRK-123"

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


class TestFSMGuards:
    """Test that FSM guards prevent invalid transitions."""

    def test_confirm_label_requires_label_url(self) -> None:
        """Cannot transition to LABEL_READY without label_url."""

        class Shipment:
            status = ShipmentStatus.CREATED
            label_url = ""
            tracking_number = ""

        shipment = Shipment()
        create_shipment_machine(shipment)

        with pytest.raises(MachineError, match="label_url"):
            shipment.confirm_label()

    def test_confirm_label_passes_with_label_url(self) -> None:
        class Shipment:
            status = ShipmentStatus.CREATED
            label_url = "https://example.com/label.pdf"
            tracking_number = ""

        shipment = Shipment()
        create_shipment_machine(shipment)

        shipment.confirm_label()
        assert shipment.status == ShipmentStatus.LABEL_READY

    def test_mark_in_transit_requires_tracking_number(self) -> None:
        """Cannot transition to IN_TRANSIT without tracking_number."""

        class Shipment:
            status = ShipmentStatus.CREATED
            label_url = ""
            tracking_number = ""

        shipment = Shipment()
        create_shipment_machine(shipment)

        with pytest.raises(MachineError, match="tracking_number"):
            shipment.mark_in_transit()

    def test_mark_in_transit_passes_with_tracking_number(self) -> None:
        class Shipment:
            status = ShipmentStatus.CREATED
            label_url = ""
            tracking_number = "TRK-123"

        shipment = Shipment()
        create_shipment_machine(shipment)

        shipment.mark_in_transit()
        assert shipment.status == ShipmentStatus.IN_TRANSIT
