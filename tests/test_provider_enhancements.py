"""Tests for Wave 1 BaseProvider enhancements."""

import pytest
from typing import Any, ClassVar

from conftest import DemoShipment
from sendparcel.provider import BaseProvider
from sendparcel.types import AddressInfo, ParcelInfo, ShipmentCreateResult
from decimal import Decimal


class EnhancedTestProvider(BaseProvider):
    """Test provider with config schema for testing."""
    
    slug = "test"
    display_name = "Test Provider"
    config_schema: ClassVar[dict[str, Any]] = {
        "api_key": {
            "type": "str",
            "required": True,
        },
        "sandbox": {
            "type": "bool",
            "required": False,
        },
        "timeout": {
            "type": "int",
            "required": True,
        },
    }
    
    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="test-1")


class CamelCaseProvider(BaseProvider):
    """Provider that prefers camelCase output."""
    
    slug = "camel"
    display_name = "Camel Provider"
    _address_format = "camel"
    
    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="camel-1")


class PascalCaseProvider(BaseProvider):
    """Provider that prefers PascalCase output."""
    
    slug = "pascal"
    display_name = "Pascal Provider"
    _address_format = "pascal"
    
    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="pascal-1")


class TestGetClient:
    """Test _get_client method."""
    
    def test_get_client_with_transport(self) -> None:
        """_get_client returns the injected transport."""
        mock_transport = object()
        provider = EnhancedTestProvider(
            DemoShipment(),
            config={"api_key": "test", "timeout": 30},
            transport=mock_transport,
        )
        
        client = provider._get_client()
        assert client is mock_transport
    
    def test_get_client_without_transport_raises(self) -> None:
        """_get_client raises RuntimeError when no transport."""
        provider = EnhancedTestProvider(
            DemoShipment(), 
            config={"api_key": "test", "timeout": 30}
        )
        
        with pytest.raises(RuntimeError) as exc_info:
            provider._get_client()
        
        assert "EnhancedTestProvider requires a transport" in str(exc_info.value)
        assert "Use create_provider() to wire the provider" in str(exc_info.value)


class TestValidateConfig:
    """Test _validate_config method."""
    
    def test_validate_config_all_required_present(self) -> None:
        """_validate_config passes when all required fields present."""
        provider = EnhancedTestProvider(
            DemoShipment(),
            config={"api_key": "test-key", "timeout": 30, "sandbox": True},
        )
        
        # Should not raise
        provider._validate_config()
    
    def test_validate_config_missing_required_raises(self) -> None:
        """Provider construction raises ValueError when required field missing."""
        with pytest.raises(ValueError) as exc_info:
            EnhancedTestProvider(
                DemoShipment(),
                config={"api_key": "test-key"},  # missing required 'timeout'
            )
        
        assert "EnhancedTestProvider requires 'timeout' in config" in str(exc_info.value)
    
    def test_validate_config_empty_string_raises(self) -> None:
        """Provider construction raises ValueError when required field is empty."""
        with pytest.raises(ValueError) as exc_info:
            EnhancedTestProvider(
                DemoShipment(),
                config={"api_key": "", "timeout": 30},  # empty api_key
            )
        
        assert "EnhancedTestProvider requires 'api_key' in config" in str(exc_info.value)
    
    def test_validate_config_wrong_type_raises(self) -> None:
        """Provider construction raises TypeError when field has wrong type."""
        with pytest.raises(TypeError) as exc_info:
            EnhancedTestProvider(
                DemoShipment(),
                config={"api_key": "test-key", "timeout": "not-an-int"},
            )
        
        assert "EnhancedTestProvider config 'timeout' must be int, got str" in str(exc_info.value)


class TestAddressToProvider:
    """Test _address_to_provider method."""
    
    def test_address_to_provider_snake_case(self) -> None:
        """_address_to_provider converts to snake_case by default."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        address: AddressInfo = {
            "first_name": "John",
            "last_name": "Doe",
            "company": "ACME Corp",
            "street": "Main St",
            "building_number": "123",
            "flat_number": "4A",
            "city": "New York",
            "postal_code": "10001",
            "country_code": "US",
            "phone": "+1234567890",
            "email": "john@example.com",
        }
        
        result = provider._address_to_provider(address)
        
        expected = {
            "first_name": "John",
            "last_name": "Doe", 
            "company": "ACME Corp",
            "street": "Main St",
            "building_number": "123",
            "flat_number": "4A",
            "city": "New York",
            "postal_code": "10001",
            "country_code": "US",
            "phone": "+1234567890",
            "email": "john@example.com",
        }
        assert result == expected
    
    def test_address_to_provider_camel_case(self) -> None:
        """_address_to_provider converts to camelCase."""
        provider = CamelCaseProvider(DemoShipment())
        
        address: AddressInfo = {
            "first_name": "John",
            "last_name": "Doe",
            "building_number": "123",
            "flat_number": "4A",
            "postal_code": "10001",
            "country_code": "US",
        }
        
        result = provider._address_to_provider(address)
        
        expected = {
            "firstName": "John",
            "lastName": "Doe",
            "buildingNumber": "123",
            "flatNumber": "4A",
            "postalCode": "10001",
            "countryCode": "US",
        }
        assert result == expected
    
    def test_address_to_provider_pascal_case(self) -> None:
        """_address_to_provider converts to PascalCase."""
        provider = PascalCaseProvider(DemoShipment())
        
        address: AddressInfo = {
            "first_name": "John", 
            "last_name": "Doe",
            "building_number": "123",
            "flat_number": "4A",
            "postal_code": "10001",
            "country_code": "US",
        }
        
        result = provider._address_to_provider(address)
        
        expected = {
            "FirstName": "John",
            "LastName": "Doe", 
            "BuildingNumber": "123",
            "FlatNumber": "4A",
            "PostalCode": "10001",
            "CountryCode": "US",
        }
        assert result == expected
    
    def test_address_to_provider_override_format(self) -> None:
        """_address_to_provider respects field_format parameter."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        address: AddressInfo = {
            "first_name": "John",
            "postal_code": "10001",
        }
        
        result = provider._address_to_provider(address, field_format="camel")
        
        expected = {
            "firstName": "John",
            "postalCode": "10001",
        }
        assert result == expected
    
    def test_address_to_provider_filters_empty_values(self) -> None:
        """_address_to_provider excludes None and empty values."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        address: AddressInfo = {
            "first_name": "John",
            "last_name": "",  # empty string
            "company": None,  # None value (this won't be in dict but testing anyway)
            "city": "New York",
        }
        
        result = provider._address_to_provider(address)
        
        expected = {
            "first_name": "John",
            "city": "New York",
        }
        assert result == expected


class TestParcelsToProvider:
    """Test _parcels_to_provider method."""
    
    def test_parcels_to_provider_with_dimensions(self) -> None:
        """_parcels_to_provider converts parcels with dimensions."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        parcels: list[ParcelInfo] = [
            {
                "weight_kg": Decimal("2.5"),
                "length_cm": Decimal("30"),
                "width_cm": Decimal("20"),
                "height_cm": Decimal("10"),
            },
            {
                "weight_kg": Decimal("1.0"),
                "length_cm": Decimal("15"),
                "width_cm": Decimal("10"), 
                "height_cm": Decimal("5"),
            },
        ]
        
        result = provider._parcels_to_provider(parcels)
        
        expected = [
            {
                "weight": 2.5,
                "length": 30.0,
                "width": 20.0,
                "height": 10.0,
            },
            {
                "weight": 1.0,
                "length": 15.0,
                "width": 10.0,
                "height": 5.0,
            },
        ]
        assert result == expected
    
    def test_parcels_to_provider_without_dimensions(self) -> None:
        """_parcels_to_provider defaults to 1.0 kg when empty."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        result = provider._parcels_to_provider([])
        
        expected = [{"weight": 1.0}]
        assert result == expected
    
    def test_parcels_to_provider_partial_dimensions(self) -> None:
        """_parcels_to_provider handles parcels with some dimensions missing."""
        provider = EnhancedTestProvider(DemoShipment(), config={"api_key": "test", "timeout": 30})
        
        parcels: list[ParcelInfo] = [
            {
                "weight_kg": Decimal("1.5"),
                "length_cm": Decimal("25"),
                # missing width_cm, height_cm
            },
            {
                "weight_kg": Decimal("0.8"),
                # missing all dimensions
            },
        ]
        
        result = provider._parcels_to_provider(parcels)
        
        expected = [
            {
                "weight": 1.5,
                "length": 25.0,
            },
            {
                "weight": 0.8,
            },
        ]
        assert result == expected