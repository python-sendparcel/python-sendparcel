"""Base provider abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ClassVar

from sendparcel.enums import ConfirmationMethod
from sendparcel.exceptions import ProviderCapabilityError
from sendparcel.protocols import Shipment
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    CancelOutcome,
    GeoPoint,
    LabelInfo,
    ParcelInfo,
    PickupPoint,
    Quote,
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
        if self.config_schema:
            self._validate_config()

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Read provider setting from config."""
        return self.config.get(name, default)

    def _get_client(self) -> Any:
        """Return the injected transport, or raise if not configured."""
        if self._transport is None:
            raise RuntimeError(
                f"{self.__class__.__name__} requires a transport. "
                "Use create_provider() to wire the provider."
            )
        return self._transport

    def _validate_config(self) -> None:
        """Validate configuration against config_schema."""
        for field_name, spec in self.config_schema.items():
            if not spec.get("required", False):
                continue
            value = self.get_setting(field_name)
            if value is None or value == "":
                raise ValueError(
                    f"{self.__class__.__name__} requires "
                    f"'{field_name}' in config."
                )
            expected_type = spec.get("type")
            if expected_type and value is not None:
                type_map: dict[str, type | tuple[type, ...]] = {
                    "str": str,
                    "int": int,
                    "float": (int, float),
                    "bool": bool,
                    "list[str]": list,
                }
                python_type = type_map.get(expected_type)
                if python_type and not isinstance(value, python_type):
                    raise TypeError(
                        f"{self.__class__.__name__} config '{field_name}' "
                        f"must be {expected_type}, got {type(value).__name__}"
                    )

    def _address_to_provider(
        self,
        addr: AddressInfo,
        *,
        field_format: str = "snake",
    ) -> dict[str, Any]:
        """Convert AddressInfo to provider-specific address dict.

        field_format: 'snake' (default), 'camel', 'pascal'
        Subclasses can override _address_format ClassVar to set their default.
        """
        fmt = getattr(self, "_address_format", field_format)

        def _convert(key: str) -> str:
            if fmt == "camel":
                parts = key.split("_")
                return parts[0] + "".join(p.capitalize() for p in parts[1:])
            elif fmt == "pascal":
                return "".join(p.capitalize() for p in key.split("_"))
            return key  # snake

        result: dict[str, Any] = {}

        # Map common fields
        field_mappings = [
            ("company", "company"),
            ("first_name", "first_name"),
            ("last_name", "last_name"),
            ("name", "name"),
            ("street", "street"),
            ("building_number", "building_number"),
            ("flat_number", "flat_number"),
            ("line1", "line1"),
            ("city", "city"),
            ("country_code", "country_code"),
            ("postal_code", "postal_code"),
            ("phone", "phone"),
            ("email", "email"),
        ]

        for src, dst in field_mappings:
            value = addr.get(src)
            if value:
                result[_convert(dst)] = value

        return result

    def _parcels_to_provider(
        self,
        parcels: list[ParcelInfo],
    ) -> list[dict[str, Any]]:
        """Convert ParcelInfo list to provider-specific parcel dicts."""
        result = []
        for parcel in parcels:
            p: dict[str, Any] = {}
            weight = parcel.get("weight_kg")
            if weight is not None:
                p["weight"] = float(weight)

            length = parcel.get("length_cm")
            width = parcel.get("width_cm")
            height = parcel.get("height_cm")
            if length:
                p["length"] = float(length)
            if width:
                p["width"] = float(width)
            if height:
                p["height"] = float(height)

            result.append(p)

        return result or [{"weight": 1.0}]

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

    async def handle_callback(
        self, ctx: CallbackContext
    ) -> ShipmentUpdateResult:
        """Normalize callback data into a shipment update payload.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support push callbacks.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "push callbacks"
        )

    async def fetch_shipment_status(
        self, **kwargs: Any
    ) -> ShipmentUpdateResult:
        """Fetch latest shipment update from provider.

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support status polling.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "status polling"
        )

    async def cancel_shipment(self, **kwargs: Any) -> CancelOutcome:
        """Cancel shipment if provider supports cancellation.

        Returns a structured :class:`CancelOutcome` so callers can
        distinguish permanent denies (REFUSED_IN_TRANSIT, NOT_CANCELLABLE)
        from retryable failures (TRANSIENT_ERROR).

        Raises :exc:`ProviderCapabilityError` if the provider does not
        support cancellation.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "cancellation"
        )

    async def search_points(
        self,
        *,
        query: str | None = None,
        near: GeoPoint | None = None,
        radius_m: int | None = None,
        point_type: str | None = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> list[PickupPoint]:
        """Search carrier pickup points (lockers, parcel shops, etc.).

        Args:
            query: Free-text search (city, address, or point code).
            near: :class:`GeoPoint` for proximity search.
            radius_m: Search radius in metres when ``near`` is given.
            point_type: Provider taxonomy filter (e.g. "parcel_locker").
            limit: Maximum number of results to return.

        Returns:
            List of :class:`PickupPoint` results, ordered by distance
            when ``near`` is given, else by relevance/name.

        Raises:
            ProviderCapabilityError: If the provider does not support
                point search.
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support "
            "pickup point search"
        )

    async def get_quote(
        self,
        *,
        service: str,
        parcels: list[ParcelInfo],
        sender_address: AddressInfo | None = None,
        receiver_address: AddressInfo | None = None,
        **kwargs: Any,
    ) -> Quote:
        """Get a shipping rate quote for a service/route combination.

        Args:
            service: Service slug (e.g. "parcel_locker_31_0").
            parcels: List of parcel definitions.
            sender_address: Optional sender address.
            receiver_address: Optional receiver address.

        Returns:
            :class:`Quote` with carrier cost as ``Decimal``.

        Raises:
            ProviderCapabilityError: If the provider does not support
                rate lookup (callers should fall back to static pricing).
        """
        raise ProviderCapabilityError(
            f"Provider {self.__class__.__name__!r} does not support rate lookup"
        )
