"""sendparcel core package."""

__version__ = "0.1.0"

from sendparcel.enums import ConfirmationMethod, ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
    SendParcelException,
)
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import BaseProvider
from sendparcel.providers.dummy import DummyProvider
from sendparcel.registry import registry

__all__ = [
    "BaseProvider",
    "CommunicationError",
    "ConfirmationMethod",
    "DummyProvider",
    "InvalidCallbackError",
    "InvalidTransitionError",
    "SendParcelException",
    "ShipmentFlow",
    "ShipmentStatus",
    "__version__",
    "registry",
]
