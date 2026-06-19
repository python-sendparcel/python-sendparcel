"""Base provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar

from sendparcel.enums import ConfirmationMethod
from sendparcel.exceptions import ProviderCapabilityError
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
    """Base class for parcel delivery providers.

    Capability methods (``create_label``, ``handle_callback``,
    ``fetch_shipment_status``, ``cancel_shipment``) raise
    :exc:`ProviderCapabilityError` by default.  Override only the
    methods the provider supports.

    The flow orchestrator calls capability methods directly — no
    ``isinstance`` trait checks.  If a provider doesn't support a
    capability, the default implementation raises.
    """

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

    async def create_label(self, **kwargs: Any) -> LabelInfo:
        """Create or fetch label payload for a shipment.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support label generation.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "label creation"
        )

    async def verify_callback(self, ctx: CallbackContext) -> None:
        """Verify callback authenticity.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support push callbacks.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "push callbacks"
        )

    async def handle_callback(self, ctx: CallbackContext) -> ShipmentUpdateResult:
        """Normalize callback data into a shipment update payload.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support push callbacks.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "push callbacks"
        )

    async def fetch_shipment_status(self, **kwargs: Any) -> ShipmentUpdateResult:
        """Fetch latest shipment update from provider.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support status polling.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "status polling"
        )

    async def cancel_shipment(self, **kwargs: Any) -> bool:
        """Cancel shipment if provider supports cancellation.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support cancellation.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "cancellation"
        )
