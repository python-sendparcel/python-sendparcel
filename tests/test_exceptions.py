"""Exception hierarchy tests."""

from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
    ProviderNotFoundError,
    SendParcelException,
)


def test_base_exception_keeps_context() -> None:
    exc = SendParcelException("boom", context={"shipment_id": "s1"})

    assert str(exc) == "boom"
    assert exc.context == {"shipment_id": "s1"}


def test_specialized_exceptions_inherit_base() -> None:
    assert issubclass(CommunicationError, SendParcelException)
    assert issubclass(InvalidCallbackError, SendParcelException)
    assert issubclass(InvalidTransitionError, SendParcelException)
    assert issubclass(ProviderNotFoundError, SendParcelException)


def test_provider_not_found_error_keeps_slug() -> None:
    exc = ProviderNotFoundError("ghost")

    assert exc.provider_slug == "ghost"
    assert str(exc) == "Provider 'ghost' is not registered"
