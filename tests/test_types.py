"""Type tests."""

from decimal import Decimal

from sendparcel.enums import LabelFormat
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
        "format": LabelFormat.PDF,
        "url": "https://example.com/label.pdf",
    }
    result: ShipmentCreateResult = {
        "external_id": "X-123",
        "tracking_number": "TRACK123",
        "label": label,
    }

    assert address["country_code"] == "PL"
    assert parcel["weight_kg"] == Decimal("1.20")
    assert result["label"]["format"] == LabelFormat.PDF


class TestAddressInfoAllOptional:
    def test_generic_address_pattern(self) -> None:
        addr: AddressInfo = {
            "name": "John",
            "line1": "Main St 1",
            "city": "Warsaw",
            "postal_code": "00-001",
            "country_code": "PL",
        }
        assert addr["country_code"] == "PL"

    def test_inpost_address_pattern(self) -> None:
        addr: AddressInfo = {
            "first_name": "Jan",
            "last_name": "Kowalski",
            "street": "Marszalkowska",
            "building_number": "1",
            "city": "Warszawa",
            "postal_code": "00-001",
            "country_code": "PL",
            "phone": "500100200",
            "email": "jan@example.com",
        }
        assert addr["first_name"] == "Jan"
        assert addr["building_number"] == "1"

    def test_empty_address_is_valid(self) -> None:
        addr: AddressInfo = {}
        assert isinstance(addr, dict)

    def test_optional_fields_can_be_omitted(self) -> None:
        addr: AddressInfo = {
            "name": "John",
            "line1": "Main St 1",
            "city": "Warsaw",
            "postal_code": "00-001",
            "country_code": "PL",
        }
        assert "company" not in addr
        assert "line2" not in addr
        assert "state" not in addr
        assert "phone" not in addr
        assert "email" not in addr
        assert "first_name" not in addr
        assert "last_name" not in addr
        assert "street" not in addr
        assert "building_number" not in addr
        assert "flat_number" not in addr


class TestParcelInfoRequired:
    def test_weight_is_required(self) -> None:
        parcel: ParcelInfo = {"weight_kg": Decimal("1.5")}
        assert parcel["weight_kg"] == Decimal("1.5")

    def test_dimensions_are_optional(self) -> None:
        parcel: ParcelInfo = {"weight_kg": Decimal("1.5")}
        assert "length_cm" not in parcel


class TestShipmentCreateResultRequired:
    def test_external_id_is_required(self) -> None:
        result: ShipmentCreateResult = {"external_id": "X-1"}
        assert result["external_id"] == "X-1"

    def test_optional_fields_can_be_omitted(self) -> None:
        result: ShipmentCreateResult = {"external_id": "X-1"}
        assert "tracking_number" not in result
        assert "label" not in result


class TestLabelInfoRequired:
    def test_format_is_required(self) -> None:
        label: LabelInfo = {"format": LabelFormat.PDF}
        assert label["format"] == LabelFormat.PDF

    def test_url_and_content_are_optional(self) -> None:
        label: LabelInfo = {"format": LabelFormat.PDF}
        assert "url" not in label
        assert "content_base64" not in label
