"""Base provider abstraction and capability trait mixins."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar

from sendparcel.enums import ConfirmationMethod
from sendparcel.protocols import Shipment
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
    ShipmentUpdateResult,
)


class BaseProvider(ABC):
    """Base class for parcel delivery providers."""

    slug: ClassVar[str] = ""
    display_name: ClassVar[str] = ""
    supported_countries: ClassVar[list[str]] = []
    supported_services: ClassVar[list[str]] = []
    confirmation_method: ClassVar[ConfirmationMethod] = ConfirmationMethod.NONE
    user_selectable: ClassVar[bool] = True
    config_schema: ClassVar[dict[str, Any]] = {}
    transport_factory: ClassVar[Callable[..., Any] | None] = None
    """Callable that builds a transport from config dict.
    Signature: transport_factory(**config) -> transport.
    None means the provider doesn't need HTTP transport (e.g. DummyProvider).
    """

    def __init__(
        self,
        shipment: Shipment,
        config: dict[str, Any] | None = None,
        *,
        transport: Any = None,
    ) -> None:
        self.shipment = shipment
        self.config = config or {}
        self._transport = transport

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
        """Create or fetch label payload for a shipment."""


class PushCallbackProvider(ABC):
    """Trait for providers that receive push notifications."""

    @abstractmethod
    async def verify_callback(self, ctx: CallbackContext) -> None:
        """Verify callback authenticity."""

    @abstractmethod
    async def handle_callback(self, ctx: CallbackContext) -> ShipmentUpdateResult:
        """Normalize callback data into a shipment update payload."""


class PullStatusProvider(ABC):
    """Trait for providers that support status polling."""

    @abstractmethod
    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentUpdateResult:
        """Fetch latest shipment update from provider."""


class CancellableProvider(ABC):
    """Trait for providers that support shipment cancellation."""

    @abstractmethod
    async def cancel_shipment(self, **kwargs: Any) -> bool:
        """Cancel shipment if provider supports cancellation."""
