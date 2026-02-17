"""Shipment flow orchestrator."""

import httpx

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    InvalidTransitionError,
    SendParcelException,
)
from sendparcel.fsm import (
    STATUS_TO_CALLBACK,
    create_shipment_machine,
)
from sendparcel.protocols import Order, Shipment, ShipmentRepository
from sendparcel.registry import registry
from sendparcel.types import AddressInfo, ParcelInfo
from sendparcel.validators import run_validators


class ShipmentFlow:
    """Framework-agnostic shipment orchestration."""

    def __init__(
        self,
        repository: ShipmentRepository,
        config: dict | None = None,
        validators: list | None = None,
    ) -> None:
        self.repository = repository
        self.config = config or {}
        self.validators = validators or []

    async def create_shipment(
        self,
        provider_slug: str,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs,
    ) -> Shipment:
        """Create a shipment record with explicit address and parcel data."""
        registry.get_by_slug(provider_slug)
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
            if shipment.may_trigger("confirm_label"):  # ty: ignore[unresolved-attribute]  # dynamic FSM trigger guard
                shipment.confirm_label()  # ty: ignore[unresolved-attribute]  # dynamic FSM trigger
        return await self.repository.save(shipment)

    async def create_shipment_from_order(
        self,
        order: Order,
        provider_slug: str,
        **kwargs,
    ) -> Shipment:
        """Convenience: create a shipment from an Order object."""
        order_id = getattr(order, "id", None)
        if order_id is not None:
            kwargs.setdefault("order_id", str(order_id))
        return await self.create_shipment(
            provider_slug,
            sender_address=order.get_sender_address(),
            receiver_address=order.get_receiver_address(),
            parcels=order.get_parcels(),
            **kwargs,
        )

    async def create_label(self, shipment: Shipment, **kwargs) -> Shipment:
        """Create provider label and persist shipment."""
        run_validators({"shipment": shipment}, validators=self.validators)
        create_shipment_machine(shipment)
        provider = self._get_provider(shipment)
        label = await self._call_provider(provider.create_label(**kwargs))
        shipment.label_url = label.get("url", "")
        if shipment.may_trigger("confirm_label"):  # ty: ignore[unresolved-attribute]  # dynamic FSM trigger guard
            shipment.confirm_label()  # ty: ignore[unresolved-attribute]  # dynamic FSM trigger
        return await self.repository.save(shipment)

    async def handle_callback(
        self,
        shipment: Shipment,
        data: dict,
        headers: dict,
        **kwargs,
    ) -> Shipment:
        """Verify and apply provider callback."""
        provider = self._get_provider(shipment)
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
        create_shipment_machine(shipment)
        response = await self._call_provider(provider.fetch_shipment_status())
        status_value = response.get("status")
        callback = self._resolve_callback(status_value)
        if callback:
            self._trigger(shipment, callback)
        return await self.repository.save(shipment)

    async def cancel_shipment(self, shipment: Shipment, **kwargs) -> bool:
        """Cancel shipment via provider and persist state."""
        provider = self._get_provider(shipment)
        create_shipment_machine(shipment)
        cancelled = await self._call_provider(
            provider.cancel_shipment(**kwargs)
        )
        if cancelled:
            self._trigger(shipment, "cancel")
            await self.repository.save(shipment)
        return cancelled

    def _get_provider(self, shipment: Shipment):
        provider_class = registry.get_by_slug(shipment.provider)
        provider_config = self.config.get(shipment.provider, {})
        return provider_class(shipment, config=provider_config)

    async def _call_provider(self, coro):
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

    def _trigger(self, shipment: Shipment, callback: str, **kwargs) -> None:
        trigger = getattr(shipment, callback, None)
        if trigger is None or not callable(trigger):
            raise InvalidTransitionError(
                f"Shipment has no callback trigger {callback!r}"
            )
        if not shipment.may_trigger(callback):  # ty: ignore[unresolved-attribute]  # dynamic FSM trigger guard
            raise InvalidTransitionError(
                f"Callback {callback!r} cannot be executed from status "
                f"{shipment.status!r}"
            )
        trigger(**kwargs)
