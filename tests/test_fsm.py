"""FSM transition tests.

Exhaustive coverage of all valid and invalid transitions.
"""

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
        status: str = "new",
        label_url: str = "",
        tracking_number: str = "",
    ) -> None:
        self.status = status
        self.label_url = label_url
        self.tracking_number = tracking_number


# === Valid transitions (one test per transition edge) ===


class TestConfirmCreated:
    def test_new_to_created(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        s.confirm_created()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "created"


class TestConfirmLabel:
    def test_created_to_label_ready(self) -> None:
        s = FsmShipment(
            status="created",
            label_url="https://example.com/label.pdf",
        )
        create_shipment_machine(s)
        s.confirm_label()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "label_ready"

    def test_blocked_without_label_url(self) -> None:
        s = FsmShipment(status="created", label_url="")
        create_shipment_machine(s)
        with pytest.raises(MachineError, match="label_url"):
            s.confirm_label()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "created"


class TestMarkInTransit:
    def test_created_to_in_transit(self) -> None:
        s = FsmShipment(
            status="created",
            tracking_number="TRK-1",
        )
        create_shipment_machine(s)
        s.mark_in_transit()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "in_transit"

    def test_label_ready_to_in_transit(self) -> None:
        s = FsmShipment(
            status="label_ready",
            tracking_number="TRK-2",
        )
        create_shipment_machine(s)
        s.mark_in_transit()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "in_transit"

    def test_blocked_without_tracking_number(self) -> None:
        s = FsmShipment(
            status="created",
            tracking_number="",
        )
        create_shipment_machine(s)
        with pytest.raises(MachineError, match="tracking_number"):
            s.mark_in_transit()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "created"


class TestMarkOutForDelivery:
    def test_in_transit_to_out_for_delivery(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        s.mark_out_for_delivery()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "out_for_delivery"


class TestMarkDelivered:
    def test_in_transit_to_delivered(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        s.mark_delivered()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "delivered"

    def test_out_for_delivery_to_delivered(self) -> None:
        s = FsmShipment(status="out_for_delivery")
        create_shipment_machine(s)
        s.mark_delivered()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "delivered"


class TestMarkReturned:
    def test_in_transit_to_returned(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        s.mark_returned()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "returned"

    def test_out_for_delivery_to_returned(self) -> None:
        s = FsmShipment(status="out_for_delivery")
        create_shipment_machine(s)
        s.mark_returned()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "returned"

    def test_delivered_to_returned(self) -> None:
        s = FsmShipment(status="delivered")
        create_shipment_machine(s)
        s.mark_returned()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "returned"


class TestCancel:
    def test_new_to_cancelled(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        s.cancel()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "cancelled"

    def test_created_to_cancelled(self) -> None:
        s = FsmShipment(status="created")
        create_shipment_machine(s)
        s.cancel()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "cancelled"

    def test_label_ready_to_cancelled(self) -> None:
        s = FsmShipment(status="label_ready")
        create_shipment_machine(s)
        s.cancel()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "cancelled"


class TestFail:
    def test_new_to_failed(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"

    def test_created_to_failed(self) -> None:
        s = FsmShipment(status="created")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"

    def test_label_ready_to_failed(self) -> None:
        s = FsmShipment(status="label_ready")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"

    def test_in_transit_to_failed(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"

    def test_out_for_delivery_to_failed(self) -> None:
        s = FsmShipment(status="out_for_delivery")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"


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
        s = FsmShipment(status="delivered")
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
        s = FsmShipment(status="cancelled")
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
        s = FsmShipment(status="failed")
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
        s = FsmShipment(status="returned")
        s.tracking_number = "TRK"
        s.label_url = "http://label"
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            getattr(s, trigger)()

    def test_new_cannot_mark_delivered(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.mark_delivered()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine

    def test_new_cannot_mark_in_transit(self) -> None:
        s = FsmShipment(status="new", tracking_number="TRK")
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.mark_in_transit()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine

    def test_in_transit_cannot_cancel(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        with pytest.raises(MachineError):
            s.cancel()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine


# === Happy path integration ===


class TestHappyPath:
    def test_full_delivery_lifecycle(self) -> None:
        s = FsmShipment(
            status="new",
            label_url="https://example.com/label.pdf",
            tracking_number="TRK-123",
        )
        create_shipment_machine(s)

        s.confirm_created()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "created"

        s.confirm_label()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "label_ready"

        s.mark_in_transit()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "in_transit"

        s.mark_out_for_delivery()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "out_for_delivery"

        s.mark_delivered()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "delivered"

    def test_cancel_from_new(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        s.cancel()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "cancelled"

    def test_fail_from_in_transit(self) -> None:
        s = FsmShipment(status="in_transit")
        create_shipment_machine(s)
        s.fail()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "failed"

    def test_return_after_delivery(self) -> None:
        s = FsmShipment(status="delivered")
        create_shipment_machine(s)
        s.mark_returned()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.status == "returned"


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
        s = FsmShipment(status="created")
        machine = create_shipment_machine(s)
        assert machine is not None
        assert s.status == "created"

    def test_defaults_to_new_when_status_empty(self) -> None:
        s = FsmShipment()
        s.status = ""
        create_shipment_machine(s)
        assert s.status == "new"

    def test_may_trigger_reports_correctly(self) -> None:
        s = FsmShipment(status="new")
        create_shipment_machine(s)
        assert s.may_trigger("confirm_created") is True  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        assert s.may_trigger("mark_delivered") is False  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
