"""Public API tests."""

import sendparcel


def test_public_api_exports_exact_set() -> None:
    """Verify __all__ contains exactly the expected symbols."""
    expected = {
        "BaseProvider",
        "BatchCreateResult",
        "BatchResult",
        "CancellableProvider",
        "CallbackContext",
        "CommunicationError",
        "ConfirmationMethod",
        "CreateLabelOutcome",
        "CreateShipmentOutcome",
        "DummyProvider",
        "configure_logging",
        "get_logger",
        "InvalidCallbackError",
        "InvalidTransitionError",
        "LabelFormat",
        "LabelProvider",
        "ProviderNotFoundError",
        "ProviderCapabilityError",
        "PullStatusProvider",
        "PushCallbackProvider",
        "SendParcelException",
        "ShipmentBatch",
        "ShipmentFlow",
        "ShipmentNotFoundError",
        "ShipmentStatus",
        "ShipmentUpdateOutcome",
        "ShipmentUpdateResult",
        "__version__",
        "registry",
    }
    assert set(sendparcel.__all__) == expected


def test_all_exports_are_importable() -> None:
    """Every name in __all__ can be accessed as an attribute."""
    for name in sendparcel.__all__:
        assert hasattr(sendparcel, name), (
            f"{name} listed in __all__ but not importable"
        )
