"""Shipment flow orchestrator."""

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import InvalidTransitionError
from sendparcel.fsm import (
    ALLOWED_CALLBACKS,
    STATUS_TO_CALLBACK,
    create_shipment_machine,
)
from sendparcel.protocols import Order, Shipment, ShipmentRepository
from sendparcel.registry import registry
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
        order: Order,
        provider_slug: str,
        **kwargs,
    ) -> Shipment:
        """Create a shipment record for an order."""
        registry.get_by_slug(provider_slug)
        shipment = await self.repository.create(
            order=order,
            provider=provider_slug,
            status=ShipmentStatus.NEW,
            **kwargs,
        )
        create_shipment_machine(shipment)
        provider = self._get_provider(shipment)
        result = await provider.create_shipment(**kwargs)
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

    async def create_label(self, shipment: Shipment, **kwargs) -> Shipment:
        """Create provider label and persist shipment."""
        run_validators({"shipment": shipment}, validators=self.validators)
        create_shipment_machine(shipment)
        provider = self._get_provider(shipment)
        label = await provider.create_label(**kwargs)
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
        await provider.verify_callback(data, headers, **kwargs)
        await provider.handle_callback(data, headers, **kwargs)
        return await self.repository.save(shipment)

    async def fetch_and_update_status(self, shipment: Shipment) -> Shipment:
        """Fetch status from provider and persist."""
        provider = self._get_provider(shipment)
        create_shipment_machine(shipment)
        response = await provider.fetch_shipment_status()
        status_value = response.get("status")
        callback = self._resolve_callback(status_value)
        if callback:
            self._trigger(shipment, callback)
        return await self.repository.save(shipment)

    async def cancel_shipment(self, shipment: Shipment, **kwargs) -> bool:
        """Cancel shipment via provider and persist state."""
        provider = self._get_provider(shipment)
        create_shipment_machine(shipment)
        cancelled = await provider.cancel_shipment(**kwargs)
        if cancelled:
            self._trigger(shipment, "cancel")
            await self.repository.save(shipment)
        return cancelled

    def _get_provider(self, shipment: Shipment):
        provider_class = registry.get_by_slug(shipment.provider)
        provider_config = self.config.get(shipment.provider, {})
        return provider_class(shipment, config=provider_config)

    def _resolve_callback(self, status_value: str | None) -> str | None:
        if status_value is None:
            return None
        if status_value in ALLOWED_CALLBACKS:
            return status_value
        callback = STATUS_TO_CALLBACK.get(status_value)
        if callback:
            return callback
        raise InvalidTransitionError(
            f"Unknown status transition {status_value!r}"
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
