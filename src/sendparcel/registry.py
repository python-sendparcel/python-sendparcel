"""Provider plugin registry."""

from importlib.metadata import entry_points

from sendparcel.provider import BaseProvider

ENTRY_POINT_GROUP = "sendparcel.providers"


class PluginRegistry:
    """Discover and store provider classes."""

    def __init__(self) -> None:
        self._providers: dict[str, type[BaseProvider]] = {}
        self._discovered = False

    def discover(self) -> None:
        """Load providers from entry points."""
        from sendparcel.providers import BUILTIN_PROVIDERS

        for provider_class in BUILTIN_PROVIDERS:
            self._register_provider(provider_class)
        eps = entry_points(group=ENTRY_POINT_GROUP)
        for ep in eps:
            provider_class = ep.load()
            if isinstance(provider_class, type) and issubclass(
                provider_class, BaseProvider
            ):
                self._register_provider(provider_class)
        self._discovered = True

    def register(self, provider_class: type[BaseProvider]) -> None:
        """Register provider manually."""
        self._register_provider(provider_class)

    def unregister(self, slug: str) -> None:
        """Unregister provider by slug."""
        self._providers.pop(slug, None)

    def get_by_slug(self, slug: str) -> type[BaseProvider]:
        """Get provider class by slug."""
        self._ensure_discovered()
        return self._providers[slug]

    def get_choices(self) -> list[tuple[str, str]]:
        """Get provider slug/display pairs for user-facing selection."""
        self._ensure_discovered()
        return [
            (p.slug, p.display_name)
            for p in self._providers.values()
            if p.user_selectable
        ]

    def _ensure_discovered(self) -> None:
        if not self._discovered:
            self.discover()

    def _register_provider(self, provider_class: type[BaseProvider]) -> None:
        slug = provider_class.slug
        existing = self._providers.get(slug)
        if existing is not None and existing is not provider_class:
            raise ValueError(
                f"Duplicate provider slug {slug!r}: "
                f"{existing.__module__}.{existing.__name__} and "
                f"{provider_class.__module__}.{provider_class.__name__}"
            )
        self._providers[slug] = provider_class


registry = PluginRegistry()
