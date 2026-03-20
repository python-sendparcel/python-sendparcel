"""Type tests."""

from decimal import Decimal

from conftest import DemoShipment
from sendparcel.enums import LabelFormat
from sendparcel.types import (
    AddressInfo,
    CreateLabelOutcome,
    CreateShipmentOutcome,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentUpdateOutcome,
    ShipmentUpdateResult,
)


def test_core_types_shape_examples() -> None:
    address: AddressInfo = {
        "name": "John Doe",
        "line1": "Main St 1",
        "city": "Warsaw",
        "postal_code": "00-001",
        "country_code": "PL",
    }
    parcel: ParcelInfo = {
        "weight_kg": Decimal("1.20"),
        "length_cm": Decimal("10"),
        "width_cm": Decimal("20"),
        "height_cm": Decimal("30"),
    }
    label: LabelInfo = {
        "format": LabelFormat.PDF,
        "url": "https://example.com/label.pdf",
    }
    result: ShipmentCreateResult = {
        "external_id": "X-123",
        "tracking_number": "TRACK123",
        "label": label,
    }
    update: ShipmentUpdateResult = {
        "status": "in_transit",
        "tracking_events": [{"code": "accepted"}],
    }

    assert address["country_code"] == "PL"
    assert parcel["weight_kg"] == Decimal("1.20")
    assert result["label"]["format"] == LabelFormat.PDF
    assert update["status"] == "in_transit"


def test_create_shipment_outcome_holds_optional_label() -> None:
    shipment = DemoShipment(status="created")
    label: LabelInfo = {
        "format": LabelFormat.PDF,
        "url": "https://example.com/label.pdf",
    }

    outcome = CreateShipmentOutcome(shipment=shipment, label=label)

    assert outcome.shipment is shipment
    assert outcome.label == label


def test_create_label_outcome_holds_label_payload() -> None:
    shipment = DemoShipment(status="label_ready")
    label: LabelInfo = {"format": LabelFormat.ZPL, "content_base64": "Zm9v"}

    outcome = CreateLabelOutcome(shipment=shipment, label=label)

    assert outcome.shipment is shipment
    assert outcome.label["format"] == LabelFormat.ZPL


def test_shipment_update_outcome_holds_normalized_update() -> None:
    shipment = DemoShipment(status="in_transit")
    update: ShipmentUpdateResult = {
        "status": "delivered",
        "tracking_events": [{"code": "delivered"}],
    }

    outcome = ShipmentUpdateOutcome(shipment=shipment, update=update)

    assert outcome.shipment is shipment
    assert outcome.update == update
