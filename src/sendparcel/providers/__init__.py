"""Built-in providers shipped with sendparcel."""

from sendparcel.providers.dummy import DummyProvider

BUILTIN_PROVIDERS = (DummyProvider,)

__all__ = ["BUILTIN_PROVIDERS", "DummyProvider"]
