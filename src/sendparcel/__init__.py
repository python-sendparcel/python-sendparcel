"""sendparcel core package."""

__version__ = "0.1.1"

from sendparcel.enums import ConfirmationMethod, LabelFormat, ShipmentStatus
from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
    ProviderCapabilityError,
    ProviderNotFoundError,
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
from sendparcel.types import (
    CreateLabelOutcome,
    CreateShipmentOutcome,
    ShipmentUpdateOutcome,
)

__all__ = [
    "BaseProvider",
    "CancellableProvider",
    "CommunicationError",
    "ConfirmationMethod",
    "CreateLabelOutcome",
    "CreateShipmentOutcome",
    "DummyProvider",
    "InvalidCallbackError",
    "InvalidTransitionError",
    "LabelFormat",
    "LabelProvider",
    "ProviderCapabilityError",
    "ProviderNotFoundError",
    "PullStatusProvider",
    "PushCallbackProvider",
    "SendParcelException",
    "ShipmentFlow",
    "ShipmentNotFoundError",
    "ShipmentStatus",
    "ShipmentUpdateOutcome",
    "__version__",
    "registry",
]
