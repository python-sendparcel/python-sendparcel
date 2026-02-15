"""Plugin registry tests."""

import importlib

import pytest

from sendparcel.provider import BaseProvider
from sendparcel.providers.dummy import DummyProvider
from sendparcel.registry import PluginRegistry


class ProviderA(BaseProvider):
    slug = "a"
    display_name = "Provider A"

    async def create_shipment(self, **kwargs):
        return {}


class ProviderB(BaseProvider):
    slug = "a"
    display_name = "Provider B"

    async def create_shipment(self, **kwargs):
        return {}


class ProviderC(BaseProvider):
    slug = "c"
    display_name = "Provider C"

    async def create_shipment(self, **kwargs):
        return {}


def test_register_get_unregister_cycle() -> None:
    reg = PluginRegistry()

    reg.register(ProviderA)

    assert reg.get_by_slug("a") is ProviderA
    assert ("a", "Provider A") in reg.get_choices()

    reg.unregister("a")

    with pytest.raises(KeyError):
        reg.get_by_slug("a")


def test_register_duplicate_slug_raises() -> None:
    reg = PluginRegistry()
    reg.register(ProviderA)

    with pytest.raises(ValueError, match="Duplicate provider slug"):
        reg.register(ProviderB)


def test_discover_uses_entry_points(monkeypatch: pytest.MonkeyPatch) -> None:
    class EP:
        def __init__(self, loaded) -> None:
            self._loaded = loaded

        def load(self):
            return self._loaded

    registry_module = importlib.import_module("sendparcel.registry")
    monkeypatch.setattr(
        registry_module, "entry_points", lambda group: [EP(ProviderC)]
    )

    reg = PluginRegistry()
    reg.discover()

    assert reg.get_by_slug("c") is ProviderC


def test_builtin_dummy_provider_is_discoverable() -> None:
    reg = PluginRegistry()

    assert reg.get_by_slug("dummy") is DummyProvider
