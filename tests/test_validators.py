"""Validator tests."""

from typing import Any

import pytest

from sendparcel.validators import run_validators


class TestRunValidators:
    def test_invokes_all_validators(self) -> None:
        called: list[tuple[str, int]] = []

        def one(context: dict[str, Any]) -> dict[str, Any]:
            called.append(("one", context["value"]))
            return context

        def two(context: dict[str, Any]) -> dict[str, Any]:
            called.append(("two", context["value"]))
            return context

        run_validators({"value": 123}, validators=[one, two])
        assert called == [("one", 123), ("two", 123)]

    def test_propagates_errors(self) -> None:
        def invalid(_context: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("invalid")

        with pytest.raises(ValueError, match="invalid"):
            run_validators({"value": 123}, validators=[invalid])

    def test_returns_data(self) -> None:
        def identity(context: dict[str, Any]) -> dict[str, Any]:
            return context

        result = run_validators({"key": "val"}, validators=[identity])
        assert result == {"key": "val"}

    def test_validators_can_transform_data(self) -> None:
        def enrich(context: dict[str, Any]) -> dict[str, Any]:
            context["enriched"] = True
            return context

        result = run_validators({"key": "val"}, validators=[enrich])
        assert result == {"key": "val", "enriched": True}

    def test_pipeline_passes_through_transformations(self) -> None:
        def add_a(context: dict[str, Any]) -> dict[str, Any]:
            context["a"] = 1
            return context

        def add_b(context: dict[str, Any]) -> dict[str, Any]:
            context["b"] = context["a"] + 1
            return context

        result = run_validators({}, validators=[add_a, add_b])
        assert result == {"a": 1, "b": 2}
        assert result == {"a": 1, "b": 2}

    def test_empty_validators_returns_data(self) -> None:
        result = run_validators({"key": "val"}, validators=[])
        assert result == {"key": "val"}

    def test_none_validators_returns_data(self) -> None:
        result = run_validators({"key": "val"}, validators=None)
        assert result == {"key": "val"}
