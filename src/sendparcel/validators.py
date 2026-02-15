"""Validation hook runner."""

from collections.abc import Callable


def run_validators(
    context: dict, validators: list[Callable] | None = None
) -> None:
    """Run configured validators sequentially."""
    for validator in validators or []:
        validator(context)
