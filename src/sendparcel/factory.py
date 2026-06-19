"""Provider factory — wires providers with their transports."""

from __future__ import annotations

from typing import Any

from sendparcel.protocols import Shipment
from sendparcel.provider import BaseProvider


def create_provider(
    shipment: Shipment,
    provider_class: type[BaseProvider],
    config: dict[str, Any],
) -> BaseProvider:
    """Wire a provider with its transport from config.

    Uses ``provider_class.transport_factory`` to build the transport.
    No provider-specific logic — fully generic.

    Args:
        shipment: The shipment the provider will operate on.
        provider_class: The provider class to instantiate.
        config: Provider configuration dict (from framework settings).

    Returns:
        A provider instance with transport injected.
    """
    factory = getattr(provider_class, "transport_factory", None)
    if factory is not None:
        transport = factory(**config)
        return provider_class(shipment, config, transport=transport)
    return provider_class(shipment, config)
