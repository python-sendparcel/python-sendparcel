"""Enum tests."""

from sendparcel.enums import ConfirmationMethod, ShipmentStatus


class TestConfirmationMethod:
    def test_none_value(self) -> None:
        assert ConfirmationMethod.NONE == "NONE"

    def test_push_value(self) -> None:
        assert ConfirmationMethod.PUSH == "PUSH"

    def test_pull_value(self) -> None:
        assert ConfirmationMethod.PULL == "PULL"


def test_shipment_status_values() -> None:
    assert ShipmentStatus.NEW.value == "new"
    assert ShipmentStatus.CREATED.value == "created"
    assert ShipmentStatus.LABEL_READY.value == "label_ready"
    assert ShipmentStatus.IN_TRANSIT.value == "in_transit"
    assert ShipmentStatus.OUT_FOR_DELIVERY.value == "out_for_delivery"
    assert ShipmentStatus.DELIVERED.value == "delivered"
    assert ShipmentStatus.CANCELLED.value == "cancelled"
    assert ShipmentStatus.FAILED.value == "failed"
    assert ShipmentStatus.RETURNED.value == "returned"
    assert ShipmentStatus.SUBMITTED.value == "submitted"


def test_shipment_status_str_enum() -> None:
    """ShipmentStatus members are valid StrEnum values."""
    for status in ShipmentStatus:
        assert isinstance(status.value, str)
        # StrEnum allows comparison with strings
        assert status == status.value


def test_submitted_state_transitions() -> None:
    """SUBMITTED can transition to CREATED or FAILED only."""
    from sendparcel.fsm import ALLOWED_STATUS_TRANSITIONS

    allowed = ALLOWED_STATUS_TRANSITIONS[ShipmentStatus.SUBMITTED]
    assert ShipmentStatus.CREATED in allowed
    assert ShipmentStatus.FAILED in allowed
    # Terminal states should NOT be reachable from SUBMITTED
    assert ShipmentStatus.DELIVERED not in allowed
    assert ShipmentStatus.CANCELLED not in allowed
