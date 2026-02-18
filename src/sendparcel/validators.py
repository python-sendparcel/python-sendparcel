"""Pluggable validation system.

Validators are callables that receive a data dict, optionally
modify it, and return it. Raise an exception to reject.
"""

from collections.abc import Callable
from typing import Any


def run_validators(
    data: dict[str, Any], validators: list[Callable[..., Any]] | None = None
) -> dict[str, Any]:
    """Run a chain of validators on data.

    Each validator receives the data dict and must return it
    (possibly modified). Raise an exception to reject.
    """
    for validator in validators or []:
        data = validator(data)
    return data
