"""Enum tests."""

from sendparcel.enums import ConfirmationMethod, ShipmentStatus


class TestConfirmationMethod:
    def test_push_value(self) -> None:
        assert ConfirmationMethod.PUSH == "PUSH"

    def test_pull_value(self) -> None:
        assert ConfirmationMethod.PULL == "PULL"


def test_shipment_status_values() -> None:
    assert ShipmentStatus.NEW == "new"
    assert ShipmentStatus.CREATED == "created"
    assert ShipmentStatus.LABEL_READY == "label_ready"
    assert ShipmentStatus.IN_TRANSIT == "in_transit"
    assert ShipmentStatus.OUT_FOR_DELIVERY == "out_for_delivery"
    assert ShipmentStatus.DELIVERED == "delivered"
    assert ShipmentStatus.CANCELLED == "cancelled"
    assert ShipmentStatus.FAILED == "failed"
    assert ShipmentStatus.RETURNED == "returned"
