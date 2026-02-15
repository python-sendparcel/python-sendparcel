"""FSM transition tests -- exhaustive coverage of all valid and invalid transitions."""

import pytest
from transitions.core import MachineError

from sendparcel.enums import ShipmentStatus
from sendparcel.fsm import (
    ALLOWED_CALLBACKS,
    STATUS_TO_CALLBACK,
    create_shipment_machine,
)


class FsmShipment:
    """Minimal shipment for FSM tests with guard-required fields."""

    def __init__(
        self,
        status=ShipmentStatus.NEW,
        label_url="",
        tracking_number="",
    ):
        self.status = status
        self.label_url = label_url
        self.tracking_number = tracking_number


# === Valid transitions (one test per transition edge) ===


class TestConfirmCreated:
    def test_new_to_created(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        s.confirm_created()
        assert s.status == ShipmentStatus.CREATED


class TestConfirmLabel:
    def test_created_to_label_ready(self) -> None:
        s = FsmShipment(
            status=ShipmentStatus.CREATED,
            label_url="https://example.com/label.pdf",
        )
        create_shipment_machine(s)
        s.confirm_label()
        assert s.status == ShipmentStatus.LABEL_READY

    def test_blocked_without_label_url(self) -> None:
        s = FsmShipment(status=ShipmentStatus.CREATED, label_url="")
        create_shipment_machine(s)
        with pytest.raises(MachineError, match="label_url"):
            s.confirm_label()
        assert s.status == ShipmentStatus.CREATED


class TestMarkInTransit:
    def test_created_to_in_transit(self) -> None:
        s = FsmShipment(
            status=ShipmentStatus.CREATED,
            tracking_number="TRK-1",
        )
        create_shipment_machine(s)
        s.mark_in_transit()
        assert s.status == ShipmentStatus.IN_TRANSIT

    def test_label_ready_to_in_transit(self) -> None:
        s = FsmShipment(
            status=ShipmentStatus.LABEL_READY,
            tracking_number="TRK-2",
        )
        create_shipment_machine(s)
        s.mark_in_transit()
        assert s.status == ShipmentStatus.IN_TRANSIT

    def test_blocked_without_tracking_number(self) -> None:
        s = FsmShipment(
            status=ShipmentStatus.CREATED,
            tracking_number="",
        )
        create_shipment_machine(s)
        with pytest.raises(MachineError, match="tracking_number"):
            s.mark_in_transit()
        assert s.status == ShipmentStatus.CREATED


class TestMarkOutForDelivery:
    def test_in_transit_to_out_for_delivery(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        s.mark_out_for_delivery()
        assert s.status == ShipmentStatus.OUT_FOR_DELIVERY


class TestMarkDelivered:
    def test_in_transit_to_delivered(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        s.mark_delivered()
        assert s.status == ShipmentStatus.DELIVERED

    def test_out_for_delivery_to_delivered(self) -> None:
        s = FsmShipment(status=ShipmentStatus.OUT_FOR_DELIVERY)
        create_shipment_machine(s)
        s.mark_delivered()
        assert s.status == ShipmentStatus.DELIVERED


class TestMarkReturned:
    def test_in_transit_to_returned(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        s.mark_returned()
        assert s.status == ShipmentStatus.RETURNED

    def test_out_for_delivery_to_returned(self) -> None:
        s = FsmShipment(status=ShipmentStatus.OUT_FOR_DELIVERY)
        create_shipment_machine(s)
        s.mark_returned()
        assert s.status == ShipmentStatus.RETURNED

    def test_delivered_to_returned(self) -> None:
        s = FsmShipment(status=ShipmentStatus.DELIVERED)
        create_shipment_machine(s)
        s.mark_returned()
        assert s.status == ShipmentStatus.RETURNED


class TestCancel:
    def test_new_to_cancelled(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED

    def test_created_to_cancelled(self) -> None:
        s = FsmShipment(status=ShipmentStatus.CREATED)
        create_shipment_machine(s)
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED

    def test_label_ready_to_cancelled(self) -> None:
        s = FsmShipment(status=ShipmentStatus.LABEL_READY)
        create_shipment_machine(s)
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED


class TestFail:
    def test_new_to_failed(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED

    def test_created_to_failed(self) -> None:
        s = FsmShipment(status=ShipmentStatus.CREATED)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED

    def test_label_ready_to_failed(self) -> None:
        s = FsmShipment(status=ShipmentStatus.LABEL_READY)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED

    def test_in_transit_to_failed(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED

    def test_out_for_delivery_to_failed(self) -> None:
        s = FsmShipment(status=ShipmentStatus.OUT_FOR_DELIVERY)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED


# === Invalid transitions (terminal states cannot transition) ===


class TestInvalidTransitions:
    @pytest.mark.parametrize(
        "trigger",
        [
            "confirm_created",
            "confirm_label",
            "mark_in_transit",
            "mark_out_for_delivery",
            "mark_delivered",
            "mark_returned",
            "cancel",
            "fail",
        ],
    )
    def test_delivered_cannot_transition(self, trigger: str) -> None:
        if trigger == "mark_returned":
            pytest.skip("delivered -> returned is valid")
        s = FsmShipment(status=ShipmentStatus.DELIVERED)
        s.tracking_number = "TRK"
        s.label_url = "http://label"
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            getattr(s, trigger)()

    @pytest.mark.parametrize(
        "trigger",
        [
            "confirm_created",
            "confirm_label",
            "mark_in_transit",
            "mark_out_for_delivery",
            "mark_delivered",
            "mark_returned",
            "cancel",
            "fail",
        ],
    )
    def test_cancelled_cannot_transition(self, trigger: str) -> None:
        s = FsmShipment(status=ShipmentStatus.CANCELLED)
        s.tracking_number = "TRK"
        s.label_url = "http://label"
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            getattr(s, trigger)()

    @pytest.mark.parametrize(
        "trigger",
        [
            "confirm_created",
            "confirm_label",
            "mark_in_transit",
            "mark_out_for_delivery",
            "mark_delivered",
            "mark_returned",
            "cancel",
            "fail",
        ],
    )
    def test_failed_cannot_transition(self, trigger: str) -> None:
        s = FsmShipment(status=ShipmentStatus.FAILED)
        s.tracking_number = "TRK"
        s.label_url = "http://label"
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            getattr(s, trigger)()

    @pytest.mark.parametrize(
        "trigger",
        [
            "confirm_created",
            "confirm_label",
            "mark_in_transit",
            "mark_out_for_delivery",
            "mark_delivered",
            "cancel",
            "fail",
        ],
    )
    def test_returned_cannot_transition(self, trigger: str) -> None:
        s = FsmShipment(status=ShipmentStatus.RETURNED)
        s.tracking_number = "TRK"
        s.label_url = "http://label"
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            getattr(s, trigger)()

    def test_new_cannot_mark_delivered(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.mark_delivered()

    def test_new_cannot_mark_in_transit(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW, tracking_number="TRK")
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.mark_in_transit()

    def test_in_transit_cannot_cancel(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.cancel()


# === Happy path integration ===


class TestHappyPath:
    def test_full_delivery_lifecycle(self) -> None:
        s = FsmShipment(
            status=ShipmentStatus.NEW,
            label_url="https://example.com/label.pdf",
            tracking_number="TRK-123",
        )
        create_shipment_machine(s)

        s.confirm_created()
        assert s.status == ShipmentStatus.CREATED

        s.confirm_label()
        assert s.status == ShipmentStatus.LABEL_READY

        s.mark_in_transit()
        assert s.status == ShipmentStatus.IN_TRANSIT

        s.mark_out_for_delivery()
        assert s.status == ShipmentStatus.OUT_FOR_DELIVERY

        s.mark_delivered()
        assert s.status == ShipmentStatus.DELIVERED

    def test_cancel_from_new(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        s.cancel()
        assert s.status == ShipmentStatus.CANCELLED

    def test_fail_from_in_transit(self) -> None:
        s = FsmShipment(status=ShipmentStatus.IN_TRANSIT)
        create_shipment_machine(s)
        s.fail()
        assert s.status == ShipmentStatus.FAILED

    def test_return_after_delivery(self) -> None:
        s = FsmShipment(status=ShipmentStatus.DELIVERED)
        create_shipment_machine(s)
        s.mark_returned()
        assert s.status == ShipmentStatus.RETURNED


# === Metadata ===


class TestAllowedCallbacks:
    def test_is_frozenset(self) -> None:
        assert isinstance(ALLOWED_CALLBACKS, frozenset)

    def test_contains_all_triggers(self) -> None:
        expected = {
            "confirm_created",
            "confirm_label",
            "mark_in_transit",
            "mark_out_for_delivery",
            "mark_delivered",
            "mark_returned",
            "cancel",
            "fail",
        }
        assert expected == ALLOWED_CALLBACKS

    def test_status_to_callback_maps_all_non_new_statuses(self) -> None:
        """Every non-NEW status should have a callback mapping."""
        mapped_statuses = set(STATUS_TO_CALLBACK.keys())
        all_non_new = {
            s.value for s in ShipmentStatus if s != ShipmentStatus.NEW
        }
        assert mapped_statuses == all_non_new


class TestMachineInitialization:
    def test_creates_machine_from_existing_status(self) -> None:
        s = FsmShipment(status=ShipmentStatus.CREATED)
        machine = create_shipment_machine(s)
        assert machine is not None
        assert s.status == ShipmentStatus.CREATED

    def test_defaults_to_new_when_status_empty(self) -> None:
        s = FsmShipment()
        s.status = ""
        create_shipment_machine(s)
        assert s.status == ShipmentStatus.NEW

    def test_may_trigger_reports_correctly(self) -> None:
        s = FsmShipment(status=ShipmentStatus.NEW)
        create_shipment_machine(s)
        assert s.may_trigger("confirm_created") is True
        assert s.may_trigger("mark_delivered") is False
