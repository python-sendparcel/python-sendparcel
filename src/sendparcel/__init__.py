"""sendparcel core package."""

__version__ = "0.3.0"

from sendparcel.batch import BatchCreateResult, BatchResult, ShipmentBatch
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
from sendparcel.factory import create_provider
from sendparcel.flow import ShipmentFlow
from sendparcel.logging import configure_logging, get_logger
from sendparcel.provider import BaseProvider
from sendparcel.providers.dummy import DummyProvider
from sendparcel.registry import registry
from sendparcel.types import (
    CallbackContext,
    CancelOutcome,
    CancelReason,
    CreateLabelOutcome,
    CreateShipmentOutcome,
    GeoPoint,
    PickupPoint,
    ShipmentUpdateOutcome,
    ShipmentUpdateResult,
)

__all__ = [
    "BaseProvider",
    "BatchCreateResult",
    "BatchResult",
    "CallbackContext",
    "CancelOutcome",
    "CancelReason",
    "CommunicationError",
    "ConfirmationMethod",
    "CreateLabelOutcome",
    "CreateShipmentOutcome",
    "DummyProvider",
    "GeoPoint",
    "InvalidCallbackError",
    "InvalidTransitionError",
    "LabelFormat",
    "PickupPoint",
    "ProviderCapabilityError",
    "ProviderNotFoundError",
    "SendParcelException",
    "ShipmentBatch",
    "ShipmentFlow",
    "ShipmentNotFoundError",
    "ShipmentStatus",
    "ShipmentUpdateOutcome",
    "ShipmentUpdateResult",
    "__version__",
    "configure_logging",
    "create_provider",
    "get_logger",
    "registry",
]
