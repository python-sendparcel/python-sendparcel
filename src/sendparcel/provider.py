"""Base provider abstraction."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sendparcel.enums import ConfirmationMethod
from sendparcel.protocols import Shipment
from sendparcel.types import (
    LabelInfo,
    ShipmentCreateResult,
    ShipmentStatusResponse,
)


class BaseProvider(ABC):
    """Base class for parcel delivery providers."""

    slug: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    supported_countries: ClassVar[list[str]] = []
    supported_services: ClassVar[list[str]] = []
    confirmation_method: ClassVar[ConfirmationMethod] = ConfirmationMethod.PUSH
    user_selectable: ClassVar[bool] = True
    config_schema: ClassVar[dict[str, Any]] = {}

    def __init__(self, shipment: Shipment, config: dict | None = None) -> None:
        self.shipment = shipment
        self.config = config or {}

    def get_setting(self, name: str, default=None):
        """Read provider setting from config."""
        return self.config.get(name, default)

    @abstractmethod
    async def create_shipment(self, **kwargs) -> ShipmentCreateResult:
        """Create shipment in provider API."""

    async def create_label(self, **kwargs) -> LabelInfo:
        """Create/fetch label for shipment."""
        raise NotImplementedError

    async def verify_callback(
        self, data: dict, headers: dict, **kwargs
    ) -> None:
        """Verify callback authenticity.

        Providers that accept callbacks MUST override this to validate
        signatures/tokens. Raise InvalidCallbackError to reject.
        """
        raise NotImplementedError

    async def handle_callback(
        self, data: dict, headers: dict, **kwargs
    ) -> None:
        """Apply callback updates to shipment."""
        raise NotImplementedError

    async def fetch_shipment_status(self, **kwargs) -> ShipmentStatusResponse:
        """Fetch latest shipment status from provider."""
        raise NotImplementedError

    async def cancel_shipment(self, **kwargs) -> bool:
        """Cancel shipment if provider supports cancellation."""
        raise NotImplementedError
