"""Status transition tests."""

from dataclasses import dataclass

import pytest

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import InvalidTransitionError
from sendparcel.fsm import (
    ALLOWED_STATUS_TRANSITIONS,
    can_transition,
    transition_shipment,
)


@dataclass
class FsmShipment:
    id: str = "shipment-1"
    status: str = "new"
    provider: str = "dummy"
    external_id: str = ""
    tracking_number: str = ""


def test_created_can_transition_directly_to_delivered() -> None:
    shipment = FsmShipment(status="created")

    transition_shipment(shipment, ShipmentStatus.DELIVERED)

    assert shipment.status == "delivered"


def test_label_ready_can_transition_to_cancelled() -> None:
    shipment = FsmShipment(status="label_ready")

    transition_shipment(shipment, ShipmentStatus.CANCELLED)

    assert shipment.status == "cancelled"


def test_delivered_can_transition_to_returned() -> None:
    shipment = FsmShipment(status="delivered")

    transition_shipment(shipment, ShipmentStatus.RETURNED)

    assert shipment.status == "returned"


def test_same_status_transition_is_idempotent() -> None:
    shipment = FsmShipment(status="in_transit")

    transition_shipment(shipment, ShipmentStatus.IN_TRANSIT)

    assert shipment.status == "in_transit"


def test_new_cannot_transition_directly_to_in_transit() -> None:
    shipment = FsmShipment(status="new")

    with pytest.raises(InvalidTransitionError, match="cannot transition"):
        transition_shipment(shipment, ShipmentStatus.IN_TRANSIT)


def test_cancelled_status_is_terminal() -> None:
    shipment = FsmShipment(status="cancelled")

    with pytest.raises(InvalidTransitionError, match="cannot transition"):
        transition_shipment(shipment, ShipmentStatus.DELIVERED)


def test_unknown_target_status_is_rejected() -> None:
    shipment = FsmShipment(status="created")

    with pytest.raises(InvalidTransitionError, match="Unknown shipment status"):
        transition_shipment(shipment, "teleported")


def test_can_transition_reports_current_rules() -> None:
    assert can_transition("created", "delivered") is True
    assert can_transition("new", "in_transit") is False


def test_allowed_status_transitions_cover_all_statuses() -> None:
    assert set(ALLOWED_STATUS_TRANSITIONS) == {
        status.value for status in ShipmentStatus
    }
