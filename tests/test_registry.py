"""Plugin registry tests."""

import importlib

from typing import Any

import pytest

from sendparcel.provider import BaseProvider
from sendparcel.providers.dummy import DummyProvider
from sendparcel.registry import PluginRegistry
from sendparcel.types import ShipmentCreateResult


class ProviderA(BaseProvider):
    slug = "a"
    display_name = "Provider A"

    async def create_shipment(self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="a-1")


class ProviderB(BaseProvider):
    slug = "a"
    display_name = "Provider B"

    async def create_shipment(self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="b-1")


class ProviderC(BaseProvider):
    slug = "c"
    display_name = "Provider C"

    async def create_shipment(self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="c-1")


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
        def __init__(self, loaded: Any) -> None:
            self._loaded = loaded

        def load(self) -> Any:
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


def test_ensure_discovered_triggers_on_get_by_slug() -> None:
    reg = PluginRegistry()

    assert reg._discovered is False

    result = reg.get_by_slug("dummy")

    assert result is DummyProvider
    assert reg._discovered is True


def test_ensure_discovered_triggers_on_get_choices() -> None:
    reg = PluginRegistry()

    assert reg._discovered is False

    choices = reg.get_choices()

    assert ("dummy", "Dummy") in choices
    assert reg._discovered is True


def test_entry_point_skips_non_baseprovider_class(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EP:
        def __init__(self, loaded: Any) -> None:
            self._loaded = loaded

        def load(self) -> Any:
            return self._loaded

    class NotAProvider:
        slug = "bad"

    registry_module = importlib.import_module("sendparcel.registry")
    monkeypatch.setattr(
        registry_module, "entry_points", lambda group: [EP(NotAProvider)]
    )

    reg = PluginRegistry()
    reg.discover()

    with pytest.raises(KeyError):
        reg.get_by_slug("bad")


def test_entry_point_skips_non_class_objects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EP:
        def __init__(self, loaded: Any) -> None:
            self._loaded = loaded

        def load(self) -> Any:
            return self._loaded

    registry_module = importlib.import_module("sendparcel.registry")
    monkeypatch.setattr(
        registry_module,
        "entry_points",
        lambda group: [EP("not-a-class"), EP(42), EP(lambda: None)],
    )

    reg = PluginRegistry()
    reg.discover()

    # Only builtins should be registered, none of the bad entry points
    choices = reg.get_choices()
    slugs = [slug for slug, _ in choices]
    assert "not-a-class" not in slugs


def test_get_choices_preserves_insertion_order() -> None:
    reg = PluginRegistry()
    reg._discovered = True

    reg.register(ProviderA)
    reg.register(ProviderC)

    choices = reg.get_choices()

    assert choices == [("a", "Provider A"), ("c", "Provider C")]


def test_unregister_nonexistent_slug_is_silent() -> None:
    reg = PluginRegistry()

    reg.unregister("nonexistent")


def test_reregister_same_class_is_idempotent() -> None:
    reg = PluginRegistry()

    reg.register(ProviderA)
    reg.register(ProviderA)

    assert reg.get_by_slug("a") is ProviderA


class HiddenProvider(BaseProvider):
    slug = "hidden"
    display_name = "Hidden Provider"
    user_selectable = False

    async def create_shipment(self, *, sender_address: Any, receiver_address: Any, parcels: Any, **kwargs: Any) -> ShipmentCreateResult:
        return ShipmentCreateResult(external_id="hidden-1")


def test_non_selectable_provider_excluded_from_get_choices() -> None:
    reg = PluginRegistry()
    reg._discovered = True

    reg.register(ProviderA)
    reg.register(HiddenProvider)

    choices = reg.get_choices()
    slugs = [slug for slug, _ in choices]

    assert "a" in slugs
    assert "hidden" not in slugs


def test_selectable_provider_included_in_get_choices() -> None:
    reg = PluginRegistry()
    reg._discovered = True

    reg.register(ProviderA)

    choices = reg.get_choices()

    assert ("a", "Provider A") in choices


def test_non_selectable_provider_still_accessible_via_get_by_slug() -> None:
    reg = PluginRegistry()
    reg._discovered = True

    reg.register(HiddenProvider)

    assert reg.get_by_slug("hidden") is HiddenProvider
