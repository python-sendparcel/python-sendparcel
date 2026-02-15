"""Type tests."""

from decimal import Decimal

from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
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
        "format": "PDF",
        "url": "https://example.com/label.pdf",
    }
    result: ShipmentCreateResult = {
        "external_id": "X-123",
        "tracking_number": "TRACK123",
        "label": label,
    }

    assert address["country_code"] == "PL"
    assert parcel["weight_kg"] == Decimal("1.20")
    assert result["label"]["format"] == "PDF"
