"""Validator tests."""

import pytest

from sendparcel.validators import run_validators


def test_run_validators_invokes_all() -> None:
    called = []

    def one(context):
        called.append(("one", context["value"]))

    def two(context):
        called.append(("two", context["value"]))

    run_validators({"value": 123}, validators=[one, two])

    assert called == [("one", 123), ("two", 123)]


def test_run_validators_propagates_errors() -> None:
    def invalid(_context):
        raise ValueError("invalid")

    with pytest.raises(ValueError, match="invalid"):
        run_validators({"value": 123}, validators=[invalid])
