"""Exception hierarchy tests."""

from sendparcel.exceptions import (
    CommunicationError,
    InvalidCallbackError,
    InvalidTransitionError,
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
