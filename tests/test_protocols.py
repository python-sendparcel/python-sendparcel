"""Protocol tests."""

from sendparcel.protocols import Shipment


class DemoShipment:
    id = "s-1"
    status = "new"
    provider = "dummy"
    external_id = ""
    tracking_number = ""
    label_url = ""


def test_runtime_protocol_checks() -> None:
    assert isinstance(DemoShipment(), Shipment)
