"""sendparcel core package."""

__version__ = "0.1.0"

from sendparcel.enums import ConfirmationMethod, LabelFormat, ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
    ProviderCapabilityError,
    SendParcelException,
    ShipmentNotFoundError,
)
from sendparcel.flow import ShipmentFlow
from sendparcel.provider import (
    BaseProvider,
    CancellableProvider,
    LabelProvider,
    PullStatusProvider,
    PushCallbackProvider,
)
from sendparcel.providers.dummy import DummyProvider
from sendparcel.registry import registry

__all__ = [
    "BaseProvider",
    "CancellableProvider",
    "CommunicationError",
    "ConfirmationMethod",
    "DummyProvider",
    "InvalidCallbackError",
    "InvalidTransitionError",
    "LabelFormat",
    "LabelProvider",
    "ProviderCapabilityError",
    "PullStatusProvider",
    "PushCallbackProvider",
    "SendParcelException",
    "ShipmentFlow",
    "ShipmentNotFoundError",
    "ShipmentStatus",
    "__version__",
    "registry",
]
