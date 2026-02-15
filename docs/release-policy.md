# Release policy

## Versioning

- The ecosystem uses semantic versioning (`MAJOR.MINOR.PATCH`).
- `python-sendparcel` defines contract compatibility for providers and adapters.

## Compatibility rules

- Breaking protocol or flow changes require a major release.
- New optional features should be minor releases.
- Bugfixes and docs/tooling updates should be patch releases.

## Cross-package alignment

- Provider plugins and adapters should declare compatible core ranges.
- Before release, run lint/test checks in every package and smoke-check provider registration.
- All packages must remain async-first and keep `anyio`-based async primitives.
