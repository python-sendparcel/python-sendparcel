"""Shipment flow orchestrator."""

from typing import Any

import httpx

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    InvalidTransitionError,
    ProviderCapabilityError,
    SendParcelException,
)
from sendparcel.fsm import (
    STATUS_TO_CALLBACK,
    create_shipment_machine,
)
from sendparcel.protocols import Shipment, ShipmentRepository
from sendparcel.provider import (
    CancellableProvider,
    LabelProvider,
    PullStatusProvider,
    PushCallbackProvider,
)
from sendparcel.registry import registry
from sendparcel.types import AddressInfo, ParcelInfo
from sendparcel.validators import run_validators


class ShipmentFlow:
    """Framework-agnostic shipment orchestration."""

    def __init__(
        self,
        repository: ShipmentRepository,
        config: dict[str, Any] | None = None,
        validators: list[Any] | None = None,
        registry: Any = None,
    ) -> None:
        self.repository = repository
        self.config = config or {}
        self.validators = validators or []
        # Local import to avoid circular dependency if registry imports flow
        from sendparcel.registry import registry as default_registry

        self.registry = registry or default_registry

    async def create_shipment(
        self,
        provider_slug: str,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> Shipment:
        """Create a shipment record with explicit address and parcel data."""
        self.registry.get_by_slug(provider_slug)
        shipment = await self.repository.create(
            provider=provider_slug,
            status=ShipmentStatus.NEW,
            **kwargs,
        )
        create_shipment_machine(shipment)
        provider = self._get_provider(shipment)
        result = await self._call_provider(
            provider.create_shipment(
                sender_address=sender_address,
                receiver_address=receiver_address,
                parcels=parcels,
                **kwargs,
            )
        )
        shipment.external_id = result.get("external_id", "")
        shipment.tracking_number = result.get("tracking_number", "")
        self._trigger(shipment, "confirm_created")
        label = result.get("label") or {}
        label_url = label.get("url", "")
        if label_url:
            shipment.label_url = label_url
            if shipment.may_trigger("confirm_label"):  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
                shipment.confirm_label()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        return await self.repository.save(shipment)

    async def create_label(self, shipment: Shipment, **kwargs: Any) -> Shipment:
        """Create provider label and persist shipment."""
        run_validators({"shipment": shipment}, validators=self.validators)
        create_shipment_machine(shipment)
        provider = self._get_provider(shipment)
        if not isinstance(provider, LabelProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support label creation"
            )
        label = await self._call_provider(provider.create_label(**kwargs))
        shipment.label_url = label.get("url", "")
        if shipment.may_trigger("confirm_label"):  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
            shipment.confirm_label()  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
        return await self.repository.save(shipment)

    async def handle_callback(
        self,
        shipment: Shipment,
        data: dict[str, Any],
        headers: dict[str, Any],
        **kwargs: Any,
    ) -> Shipment:
        """Verify and apply provider callback."""
        provider = self._get_provider(shipment)
        if not isinstance(provider, PushCallbackProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support push callbacks"
            )
        create_shipment_machine(shipment)
        await self._call_provider(
            provider.verify_callback(data, headers, **kwargs)
        )
        await self._call_provider(
            provider.handle_callback(data, headers, **kwargs)
        )
        return await self.repository.save(shipment)

    async def fetch_and_update_status(self, shipment: Shipment) -> Shipment:
        """Fetch status from provider and persist."""
        provider = self._get_provider(shipment)
        if not isinstance(provider, PullStatusProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support status polling"
            )
        create_shipment_machine(shipment)
        response = await self._call_provider(provider.fetch_shipment_status())
        status_value = response.get("status")
        callback = self._resolve_callback(status_value)
        if callback:
            self._trigger(shipment, callback)
        return await self.repository.save(shipment)

    async def cancel_shipment(self, shipment: Shipment, **kwargs: Any) -> bool:
        """Cancel shipment via provider and persist state."""
        provider = self._get_provider(shipment)
        if not isinstance(provider, CancellableProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support cancellation"
            )
        create_shipment_machine(shipment)
        cancelled = await self._call_provider(
            provider.cancel_shipment(**kwargs)
        )
        if cancelled:
            self._trigger(shipment, "cancel")
            await self.repository.save(shipment)
        return bool(cancelled)

    def _get_provider(self, shipment: Shipment) -> Any:
        provider_class = self.registry.get_by_slug(shipment.provider)
        provider_config = self.config.get(shipment.provider, {})
        return provider_class(shipment, config=provider_config)

    async def _call_provider(self, coro: Any) -> Any:
        """Call a provider coroutine, wrapping non-domain errors."""
        try:
            return await coro
        except SendParcelException:
            raise
        except httpx.HTTPError as exc:
            raise CommunicationError(
                str(exc),
                context={"original_error": type(exc).__name__},
            ) from exc
        except Exception as exc:
            raise CommunicationError(
                str(exc),
                context={"original_error": type(exc).__name__},
            ) from exc

    def _resolve_callback(self, status_value: str | None) -> str | None:
        """Map a provider status value to an FSM callback name.

        Only accepts values from STATUS_TO_CALLBACK mapping.
        Raw callback names (e.g., "cancel") are NOT accepted as
        status values -- providers must return status enum values
        (e.g., "cancelled").
        """
        if status_value is None:
            return None
        callback = STATUS_TO_CALLBACK.get(status_value)
        if callback:
            return callback
        raise InvalidTransitionError(
            f"Unknown status value {status_value!r}. "
            f"Expected one of: {', '.join(sorted(STATUS_TO_CALLBACK))}"
        )

    def _trigger(
        self, shipment: Shipment, callback: str, **kwargs: Any
    ) -> None:
        trigger = getattr(shipment, callback, None)
        if trigger is None or not callable(trigger):
            raise InvalidTransitionError(
                f"Shipment has no callback trigger {callback!r}"
            )
        if not shipment.may_trigger(callback):  # type: ignore[attr-defined]  # Method added dynamically by transitions.Machine
            raise InvalidTransitionError(
                f"Callback {callback!r} cannot be executed from status "
                f"{shipment.status!r}"
            )
        trigger(**kwargs)
