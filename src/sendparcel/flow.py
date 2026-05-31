"""Shipment flow orchestrator."""

from __future__ import annotations

from typing import Any

import httpx

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    ProviderCapabilityError,
    SendParcelException,
)
from sendparcel.fsm import transition_shipment
from sendparcel.protocols import Shipment, ShipmentRepository
from sendparcel.provider import (
    BaseProvider,
    CancellableProvider,
    LabelProvider,
    PullStatusProvider,
    PushCallbackProvider,
)
from sendparcel.registry import PluginRegistry
from sendparcel.registry import registry as default_registry
from sendparcel.types import (
    AddressInfo,
    CreateLabelOutcome,
    CreateShipmentOutcome,
    ParcelInfo,
    ShipmentUpdateOutcome,
    ShipmentUpdateResult,
)
from sendparcel.validators import run_validators


class ShipmentFlow:
    """Framework-agnostic shipment orchestration."""

    def __init__(
        self,
        repository: ShipmentRepository,
        config: dict[str, Any] | None = None,
        validators: list[Any] | None = None,
        registry: PluginRegistry | None = None,
    ) -> None:
        self.repository = repository
        self.config = config or {}
        self.validators = validators or []
        self.registry = registry or default_registry

    async def create_shipment(
        self,
        provider_slug: str,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        idempotency_key: str | None = None,
        **kwargs: Any,
    ) -> CreateShipmentOutcome:
        """Create a shipment record with explicit address and parcel data.

        Uses persistence-enforced idempotency: if a shipment with the same
        provider + idempotency_key already exists, it is returned without
        calling the provider again.

        On provider failure:
        - CommunicationError (timeout, network): marks shipment as
          ``SUBMITTED`` (ambiguous — provider may have accepted).
          The caller should reconcile via polling or callback.
        - Other errors: marks shipment as ``FAILED`` and re-raises.

        The shipment record is never deleted on failure, ensuring that
        retries and reconciliation always have a record to work with.

        Args:
            provider_slug: Provider identifier.
            sender_address: Sender address info.
            receiver_address: Receiver address info.
            parcels: List of parcel definitions.
            idempotency_key: Optional key for retry safety. Stored in the
                ``reference_id`` field of the shipment record.
            **kwargs: Passed to the provider (after repo-only fields
                are stripped).

        Returns:
            CreateShipmentOutcome with the persisted shipment and
            optional label payload.
        """
        self.registry.get_by_slug(provider_slug)

        # Separate repository kwargs from provider kwargs.
        repo_kwargs: dict[str, Any] = {}
        for key in ("reference_id",):
            if key in kwargs:
                repo_kwargs[key] = kwargs.pop(key)

        # Apply idempotency key to reference_id if provided.
        if idempotency_key is not None:
            repo_kwargs.setdefault("reference_id", idempotency_key)

        # Create shipment — use atomic idempotency if key provided.
        if idempotency_key is not None:
            existing, created = (
                await self.repository.create_with_idempotency_key(
                    provider=provider_slug,
                    status=ShipmentStatus.NEW.value,
                    **repo_kwargs,
                )
            )
            if existing is not None:
                return CreateShipmentOutcome(shipment=existing, label=None)
            assert created is not None
            shipment = created
        else:
            shipment = await self.repository.create(
                provider=provider_slug,
                status=ShipmentStatus.NEW.value,
                **repo_kwargs,
            )

        provider = self._get_provider(shipment)
        try:
            result = await self._call_provider(
                provider.create_shipment(
                    sender_address=sender_address,
                    receiver_address=receiver_address,
                    parcels=parcels,
                    **kwargs,
                )
            )
        except CommunicationError:
            # Ambiguous: provider may have accepted the shipment
            # (e.g. timeout after acceptance). Mark as SUBMITTED for
            # reconciliation via polling or callback.
            transition_shipment(shipment, ShipmentStatus.SUBMITTED)
            await self.repository.save(shipment)
            return CreateShipmentOutcome(shipment=shipment, label=None)
        except Exception:
            # Non-communication error: mark as FAILED, never delete.
            transition_shipment(shipment, ShipmentStatus.FAILED)
            await self.repository.save(shipment)
            raise

        shipment.external_id = str(result.get("external_id", ""))
        shipment.tracking_number = str(result.get("tracking_number", ""))
        transition_shipment(shipment, ShipmentStatus.CREATED)
        label = result.get("label")
        if label is not None:
            transition_shipment(shipment, ShipmentStatus.LABEL_READY)
        saved = await self.repository.save(shipment)
        return CreateShipmentOutcome(shipment=saved, label=label)

    async def create_label(
        self, shipment: Shipment, **kwargs: Any
    ) -> CreateLabelOutcome:
        """Create provider label and persist shipment metadata."""

        run_validators({"shipment": shipment}, validators=self.validators)
        provider = self._get_provider(shipment)
        if not isinstance(provider, LabelProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support "
                "label creation"
            )
        label = await self._call_provider(provider.create_label(**kwargs))
        transition_shipment(shipment, ShipmentStatus.LABEL_READY)
        saved = await self.repository.update_fields(
            shipment_id=shipment.id, status=shipment.status
        )
        return CreateLabelOutcome(shipment=saved, label=label)

    async def handle_callback(
        self,
        shipment: Shipment,
        data: dict[str, Any],
        headers: dict[str, Any],
        **kwargs: Any,
    ) -> ShipmentUpdateOutcome:
        """Verify and apply provider callback."""

        provider = self._get_provider(shipment)
        if not isinstance(provider, PushCallbackProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support "
                "push callbacks"
            )
        await self._call_provider(
            provider.verify_callback(data, headers, **kwargs)
        )
        update = await self._call_provider(
            provider.handle_callback(data, headers, **kwargs)
        )
        normalized_update = update or ShipmentUpdateResult()
        saved = await self._apply_update(shipment, normalized_update)
        return ShipmentUpdateOutcome(shipment=saved, update=normalized_update)

    async def fetch_and_update_status(
        self, shipment: Shipment
    ) -> ShipmentUpdateOutcome:
        """Fetch status from provider and persist."""

        provider = self._get_provider(shipment)
        if not isinstance(provider, PullStatusProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support "
                "status polling"
            )
        update = await self._call_provider(provider.fetch_shipment_status())
        normalized_update = update or ShipmentUpdateResult()
        saved = await self._apply_update(shipment, normalized_update)
        return ShipmentUpdateOutcome(shipment=saved, update=normalized_update)

    async def cancel_shipment(self, shipment: Shipment, **kwargs: Any) -> bool:
        """Cancel shipment via provider and persist state."""

        provider = self._get_provider(shipment)
        if not isinstance(provider, CancellableProvider):
            raise ProviderCapabilityError(
                f"Provider {shipment.provider!r} does not support cancellation"
            )
        cancelled = await self._call_provider(
            provider.cancel_shipment(**kwargs)
        )
        if cancelled:
            transition_shipment(shipment, ShipmentStatus.CANCELLED)
            await self.repository.update_fields(
                shipment_id=shipment.id, status=shipment.status
            )
        return bool(cancelled)

    def _get_provider(self, shipment: Shipment) -> BaseProvider:
        provider_class = self.registry.get_by_slug(shipment.provider)
        provider_config = self.config.get(shipment.provider, {})
        return provider_class(shipment, config=provider_config)

    async def _apply_update(
        self, shipment: Shipment, update: ShipmentUpdateResult
    ) -> Shipment:
        """Apply a normalized update to a shipment atomically.

        Uses the atomic ``update_fields`` persistence primitive to
        prevent concurrent read-modify-save races.
        """
        fields: dict[str, Any] = {}
        tracking_number = update.get("tracking_number")
        if tracking_number:
            fields["tracking_number"] = str(tracking_number)
        status = update.get("status")
        if status is not None:
            transition_shipment(shipment, status)
            fields["status"] = shipment.status
        return await self.repository.update_fields(
            shipment_id=shipment.id, **fields
        )

    async def _call_provider(self, coro: Any) -> Any:
        """Call a provider coroutine, wrapping only network errors.

        Domain errors (ValueError, KeyError, TypeError, etc.) are re-raised
        as-is so they are distinguishable from communication failures.
        """

        try:
            return await coro
        except SendParcelException:
            raise
        except httpx.HTTPError as exc:
            raise CommunicationError(
                str(exc),
                context={"original_error": type(exc).__name__},
            ) from exc
        except TimeoutError as exc:
            raise CommunicationError(
                str(exc),
                context={"original_error": type(exc).__name__},
            ) from exc
        except ExceptionGroup as exc:
            # Preserve typed inner exceptions: if any inner exception is a
            # SendParcelException, re-raise it directly. Otherwise wrap the
            # entire group in a CommunicationError.
            for e in exc.exceptions:
                if isinstance(e, SendParcelException):
                    raise e from exc
            raise CommunicationError(
                str(exc),
                context={"original_error": type(exc).__name__},
            ) from exc
