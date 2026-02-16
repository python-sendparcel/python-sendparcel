# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

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
