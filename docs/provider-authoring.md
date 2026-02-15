# Provider authoring guide

## Package naming

- Distribution: `python-sendparcel-<provider>`
- Import package: `sendparcel_<provider>`

## Required entry point

Register the provider in `pyproject.toml`:

```toml
[project.entry-points."sendparcel.providers"]
<provider> = "sendparcel_<provider>.provider:<ProviderClass>"
```

## Provider contract

Subclass `sendparcel.provider.BaseProvider` and implement:

- `create_shipment()`
- `create_label()`
- `verify_callback()`
- `handle_callback()`
- `fetch_shipment_status()`
- `cancel_shipment()`

## Async rules

- Providers must be async-first.
- Use `anyio` utilities for sleeps, timeouts, and async primitives.
- Do not block the event loop with sync HTTP clients.

## Minimal quality checks

```bash
uv sync --extra dev
uv run --extra dev ruff check src tests
uv run --extra dev pytest -q
```
