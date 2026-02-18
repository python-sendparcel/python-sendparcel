"""Exception hierarchy for sendparcel."""

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
        message = f"Shipment {shipment_id} not found"
        super().__init__(message, context)
        self.shipment_id = shipment_id


class ProviderCapabilityError(SendParcelException):
    """Provider does not support the requested capability."""
