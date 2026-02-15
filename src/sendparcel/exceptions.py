"""Exception hierarchy for sendparcel."""


class SendParcelException(Exception):
    """Base exception for sendparcel."""

    def __init__(self, message: str = "", context: dict | None = None) -> None:
        super().__init__(message)
        self.context = context or {}


class CommunicationError(SendParcelException):
    """Provider communication failed."""


class InvalidCallbackError(SendParcelException):
    """Webhook callback validation failed."""


class InvalidTransitionError(SendParcelException):
    """Invalid shipment state transition requested."""
