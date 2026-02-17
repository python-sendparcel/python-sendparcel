"""Protocol tests."""

from decimal import Decimal

from sendparcel.protocols import Order, Shipment


class DemoOrder:
    def get_total_weight(self) -> Decimal:
        return Decimal("1.0")

    def get_parcels(self):
        return []

    def get_sender_address(self):
        return {}

    def get_receiver_address(self):
        return {}


class DemoShipment:
    id = "s-1"
    status = "new"
    provider = "dummy"
    external_id = ""
    tracking_number = ""
    label_url = ""


def test_runtime_protocol_checks() -> None:
    assert isinstance(DemoOrder(), Order)
    assert isinstance(DemoShipment(), Shipment)
