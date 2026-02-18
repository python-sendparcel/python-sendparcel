"""Enum tests."""

from sendparcel.enums import ConfirmationMethod, ShipmentStatus


class TestConfirmationMethod:
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
