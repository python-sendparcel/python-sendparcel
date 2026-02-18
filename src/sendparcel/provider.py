"""Base provider abstraction and capability trait mixins."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from sendparcel.enums import ConfirmationMethod
from sendparcel.protocols import Shipment
from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentStatusResponse,
)


class BaseProvider(ABC):
    """Base class for parcel delivery providers.

    This is the minimal required interface. Providers can extend with
    capability traits (LabelProvider, PushCallbackProvider, etc.) to
    declare additional supported operations.
    """

    slug: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    supported_countries: ClassVar[list[str]] = []
    supported_services: ClassVar[list[str]] = []
    confirmation_method: ClassVar[ConfirmationMethod] = ConfirmationMethod.PUSH
    user_selectable: ClassVar[bool] = True
    config_schema: ClassVar[dict[str, Any]] = {}

    def __init__(
        self, shipment: Shipment, config: dict[str, Any] | None = None
    ) -> None:
        self.shipment = shipment
        self.config = config or {}

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Read provider setting from config."""
        return self.config.get(name, default)

    @abstractmethod
    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        """Create shipment in provider API."""


class LabelProvider(ABC):
    """Trait for providers that support label generation."""

    @abstractmethod
    async def create_label(self, **kwargs: Any) -> LabelInfo:
        """Create/fetch label for shipment."""


class PushCallbackProvider(ABC):
    """Trait for providers that receive push notifications (webhooks)."""

    @abstractmethod
    async def verify_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        """Verify callback authenticity.

        Providers that accept callbacks MUST override this to validate
        signatures/tokens. Raise InvalidCallbackError to reject.
        """

    @abstractmethod
    async def handle_callback(
        self, data: dict[str, Any], headers: dict[str, Any], **kwargs: Any
    ) -> None:
        """Apply callback updates to shipment."""


class PullStatusProvider(ABC):
    """Trait for providers that support status polling."""

    @abstractmethod
    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentStatusResponse:
        """Fetch latest shipment status from provider."""


class CancellableProvider(ABC):
    """Trait for providers that support shipment cancellation."""

    @abstractmethod
    async def cancel_shipment(self, **kwargs: Any) -> bool:
        """Cancel shipment if provider supports cancellation."""
