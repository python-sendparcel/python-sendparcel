"""Shipment flow orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import httpx

from sendparcel.enums import ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    SendParcelException,
)
from sendparcel.fsm import transition_shipment
from sendparcel.protocols import Shipment, ShipmentRepository
from sendparcel.provider import BaseProvider
from sendparcel.registry import PluginRegistry
from sendparcel.registry import registry as default_registry
from sendparcel.types import (
    AddressInfo,
    CallbackContext,
    CancelOutcome,
    CancelReason,
    CreateLabelOutcome,
    CreateShipmentOutcome,
    GeoPoint,
    ParcelInfo,
    PickupPoint,
    ShipmentUpdateOutcome,
    ShipmentUpdateResult,
)


@dataclass(slots=True)
class _PointSearchShipment:
    """Placeholder satisfying the Shipment protocol for provider calls
    that do not operate on a specific shipment (e.g. point search)."""

    provider: str
    id: str = ""
    status: str = "new"
    external_id: str = ""
    tracking_number: str = ""


class ShipmentFlow:
    """Framework-agnostic shipment orchestration."""

    def __init__(
        self,
        repository: ShipmentRepository,
        config: dict[str, Any] | None = None,
        registry: PluginRegistry | None = None,
    ) -> None:
        self.repository = repository
        self.config = config or {}
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
        for key in ("reference_id", "order"):
            if key in kwargs:
                repo_kwargs[key] = kwargs.pop(key)

        # Apply idempotency key to reference_id if provided.
        if idempotency_key is not None:
            repo_kwargs.setdefault("reference_id", idempotency_key)

        # Create shipment — use atomic idempotency if key provided.
        if idempotency_key is not None:
            (
                existing,
                created,
            ) = await self.repository.create_with_idempotency_key(
                provider=provider_slug,
                status=ShipmentStatus.NEW.value,
                **repo_kwargs,
            )
            if existing is not None:
                return CreateShipmentOutcome(shipment=existing, label=None)
            if created is None:
                raise RuntimeError(
                    "create_with_idempotency_key returned (None, None) "
                    "— repository contract violated"
                )
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

        provider = self._get_provider(shipment)
        label = await self._call_provider(provider.create_label(**kwargs))
        transition_shipment(shipment, ShipmentStatus.LABEL_READY)
        saved = await self.repository.update_fields(
            shipment_id=shipment.id, status=shipment.status
        )
        return CreateLabelOutcome(shipment=saved, label=label)

    async def handle_callback(
        self,
        ctx: CallbackContext,
        *,
        shipment: Shipment | None = None,
    ) -> ShipmentUpdateOutcome:
        """Verify and apply provider callback.

        The caller is responsible for loading the shipment (from
        ``ctx.shipment_id``) and passing it in. If ``shipment`` is not
        provided, it will be loaded from the repository.
        """
        if shipment is None:
            shipment = await self.repository.get_by_id(ctx.shipment_id)
        provider = self._get_provider(shipment)
        await self._call_provider(provider.verify_callback(ctx))
        update = await self._call_provider(provider.handle_callback(ctx))
        normalized_update = update or ShipmentUpdateResult()
        saved = await self._apply_update(shipment, normalized_update)
        return ShipmentUpdateOutcome(shipment=saved, update=normalized_update)

    async def fetch_and_update_status(
        self, shipment: Shipment
    ) -> ShipmentUpdateOutcome:
        """Fetch status from provider and persist."""

        provider = self._get_provider(shipment)
        update = await self._call_provider(provider.fetch_shipment_status())
        normalized_update = update or ShipmentUpdateResult()
        saved = await self._apply_update(shipment, normalized_update)
        return ShipmentUpdateOutcome(shipment=saved, update=normalized_update)

    async def cancel_shipment(
        self, shipment: Shipment, **kwargs: Any
    ) -> CancelOutcome:
        """Cancel shipment via provider and persist state.

        Returns a structured :class:`CancelOutcome` so callers can
        distinguish permanent denies from retryable failures.

        - ``CANCELLED`` / ``ALREADY_CANCELLED`` → transitions shipment to
          ``CANCELLED``.
        - ``REFUSED_IN_TRANSIT`` / ``NOT_CANCELLABLE`` → leaves shipment
          in current state (caller decides UX).
        - ``TRANSIENT_ERROR`` → raises ``CommunicationError`` (retryable),
          no state change.
        - ``AUTH_ERROR`` → re-raises provider auth error.
        """
        provider = self._get_provider(shipment)
        outcome = cast(
            "CancelOutcome",
            await self._call_provider(provider.cancel_shipment(**kwargs)),
        )
        if outcome.get("reason") == CancelReason.TRANSIENT_ERROR:
            raise CommunicationError(
                outcome.get("detail") or "Cancel failed with transient error",
                context={
                    "provider_status_code": outcome.get("provider_status_code"),
                    "reason": CancelReason.TRANSIENT_ERROR,
                },
            )
        if outcome.get("cancelled"):
            transition_shipment(shipment, ShipmentStatus.CANCELLED)
            await self.repository.update_fields(
                shipment_id=shipment.id, status=shipment.status
            )
        return outcome

    async def search_points(
        self,
        provider_slug: str,
        *,
        query: str | None = None,
        near: GeoPoint | None = None,
        radius_m: int | None = None,
        point_type: str | None = None,
        limit: int = 20,
        **kwargs: Any,
    ) -> list[PickupPoint]:
        """Search carrier pickup points via the registered provider.

        Convenience method that delegates to the provider's
        ``search_points`` capability. Raises
        ``ProviderCapabilityError`` if the provider does not support
        point search.

        Args:
            provider_slug: Provider identifier.
            query: Free-text search (city, address, or point code).
            near: :class:`GeoPoint` for proximity search.
            radius_m: Search radius in metres when ``near`` is given.
            point_type: Provider taxonomy filter.
            limit: Maximum number of results.

        Returns:
            List of :class:`PickupPoint` results.
        """
        provider_class = self.registry.get_by_slug(provider_slug)
        provider_config = self.config.get(provider_slug, {})
        from sendparcel.factory import create_provider

        provider = create_provider(
            _PointSearchShipment(provider=provider_slug),
            provider_class,
            provider_config,
        )
        return cast(
            "list[PickupPoint]",
            await self._call_provider(
                provider.search_points(
                    query=query,
                    near=near,
                    radius_m=radius_m,
                    point_type=point_type,
                    limit=limit,
                    **kwargs,
                )
            ),
        )

    def _get_provider(self, shipment: Shipment) -> BaseProvider:
        from sendparcel.factory import create_provider

        provider_class = self.registry.get_by_slug(shipment.provider)
        provider_config = self.config.get(shipment.provider, {})
        return create_provider(shipment, provider_class, provider_config)

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
