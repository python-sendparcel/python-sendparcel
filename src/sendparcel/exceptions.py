"""Exception hierarchy for sendparcel."""

from __future__ import annotations

from typing import Any


class SendParcelException(Exception):
    """Base exception for sendparcel."""

    def __init__(
        self, message: str = "", context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.context = context or {}


class CommunicationError(SendParcelException):
    """Provider communication failed."""


class InvalidCallbackError(SendParcelException):
    """Webhook callback validation failed."""


class InvalidTransitionError(SendParcelException):
    """Invalid shipment state transition requested."""


class ShipmentNotFoundError(SendParcelException):
    """Shipment not found in repository."""

    def __init__(
        self, shipment_id: str, context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(f"Shipment {shipment_id} not found", context)
        self.shipment_id = shipment_id


class ProviderNotFoundError(SendParcelException):
    """Provider slug not found in the registry."""

    def __init__(
        self, provider_slug: str, context: dict[str, Any] | None = None
    ) -> None:
        super().__init__(
            f"Provider {provider_slug!r} is not registered", context
        )
        self.provider_slug = provider_slug


class ProviderCapabilityError(SendParcelException):
    """Provider does not support the requested capability."""
