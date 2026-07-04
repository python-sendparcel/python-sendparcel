# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [0.3.0] - 2026-07-04

### Changed (breaking)

- Unified the five capability trait ABCs (`LabelProvider`,
  `PushCallbackProvider`, `PullStatusProvider`, `CancellableProvider`)
  into a single `BaseProvider`; unsupported capabilities raise
  `ProviderCapabilityError` by default
- Removed the validator framework; required config fields declared in
  `config_schema` are now validated automatically at provider
  construction
- Callbacks are handled through `CallbackContext`
  (`verify_callback(ctx)` / `handle_callback(ctx)`)
- Providers receive their HTTP transport via `transport_factory`
  injection (`create_provider` wires it)

### Fixed

- Missing `Any` import in `sendparcel.types` made
  `CallbackContext` annotations unresolvable at runtime
  (`typing.get_type_hints` raised `NameError`)
- `ShipmentBatch` created without an explicit registry now uses the
  global registry singleton, consistent with `ShipmentFlow`
- `ConcurrentExecutor` now uses anyio primitives and works under the
  trio backend (previously hardcoded asyncio)
- Lint and type-check regressions; `ruff check`, `ruff format --check`,
  `ty check`, and `mypy --strict src` all pass again
- README quick-start example was missing the `update_fields` repository
  method required by `create_label`
- Provider-authoring guide rewritten for the unified `BaseProvider`
  API (previous examples raised `ImportError`)

### Added

- `PluginRegistry.slugs()` — public, thread-safe accessor for all
  registered provider slugs

### Removed

- `fastapi` and `litestar` extras from the README (not published)
- Dead code: `ShipmentStatusResponse` alias, logging compat aliases

## [0.2.0] - 2025-06-05

### Added

- `CallbackContext` for webhook callback handling
- Transport injection via factory pattern
- `ConcurrentExecutor` generic concurrency primitive
- Structured JSON logging helpers

## [0.1.0] - 2025-02-16

### Added

- Provider protocol and plugin registry with entry-point discovery
- Shipment domain types (`AddressInfo`, `ParcelInfo`, `ShipmentCreateResult`, `LabelInfo`)
- Finite state machine for shipment lifecycle (`ShipmentStatus` enum with 9 states)
- Framework-agnostic `ShipmentFlow` orchestrator
- `BaseProvider` abstract class for provider plugins
- Built-in `DummyProvider` for testing and development
- Global and per-provider validator support
- Async-first runtime powered by `anyio`
- Full test suite (157 tests)
