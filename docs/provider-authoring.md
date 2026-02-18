# Provider Authoring Guide

## Package Naming

- Distribution: `python-sendparcel-<provider>`
- Import package: `sendparcel_<provider>`

## Required Entry Point

Register the provider in `pyproject.toml`:

```toml
[project.entry-points."sendparcel.providers"]
<provider> = "sendparcel_<provider>.provider:<ProviderClass>"
```

## Provider Contract

The `python-sendparcel` ecosystem uses a trait-based model. Only core shipment creation is required; all other capabilities are optional and declared via mixin traits.

### Base Provider (Required)

Every provider MUST inherit from `sendparcel.provider.BaseProvider` and implement:

- `create_shipment(sender_address, receiver_address, parcels, **kwargs)` - creates a shipment in the provider API. Returns a `ShipmentCreateResult`.

Class variables:
- `slug`: Unique provider identifier (e.g., "dhl", "inpost").
- `display_name`: Human-readable name.
- `supported_countries`: List of ISO 3166-1 alpha-2 country codes.
- `supported_services`: List of provider-specific service slugs.
- `config_schema`: JSON Schema for provider settings.

### Optional Capability Traits

Providers declare additional capabilities by inheriting from trait mixins. The framework uses `isinstance()` at runtime to detect supported features.

#### Capability Matrix

| Capability | Trait Class | Required Method(s) |
|------------|-------------|--------------------|
| Labels | `LabelProvider` | `create_label()` |
| Webhooks | `PushCallbackProvider` | `verify_callback()`, `handle_callback()` |
| Status Polling | `PullStatusProvider` | `fetch_shipment_status()` |
| Cancellation | `CancellableProvider` | `cancel_shipment()` |

#### LabelProvider
Providers that generate shipping labels (e.g., PDF, ZPL).
- `create_label(**kwargs)`: Returns `LabelInfo`.

#### PushCallbackProvider
Providers that receive webhook notifications from the provider's server.
- `verify_callback(data, headers, **kwargs)`: Authenticates the webhook (raises `InvalidCallbackError` if invalid).
- `handle_callback(data, headers, **kwargs)`: Processes the webhook payload and updates shipment state.

#### PullStatusProvider
Providers that support status polling via API.
- `fetch_shipment_status(**kwargs)`: Returns `ShipmentStatusResponse`.

#### CancellableProvider
Providers that support shipment cancellation.
- `cancel_shipment(**kwargs)`: Returns a boolean indicating success.

## Provider Examples

### Minimal Provider (Create Shipment Only)

```python
from sendparcel.provider import BaseProvider
from sendparcel.types import (
    AddressInfo,
    ParcelInfo,
    ShipmentCreateResult
)

class MinimalProvider(BaseProvider):
    slug = "minimal"
    display_name = "Minimal Provider"
    
    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs
    ) -> ShipmentCreateResult:
        # Implementation calling provider API
        return ShipmentCreateResult(
            external_id="123",
            tracking_number="TRK123"
        )
```

### Full-Featured Provider

```python
from typing import Any
from sendparcel.provider import (
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider
)

class FullProvider(
    BaseProvider,
    LabelProvider,
    PushCallbackProvider,
    PullStatusProvider,
    CancellableProvider
):
    slug = "full"
    
    async def create_shipment(self, **kwargs): ...
    
    async def create_label(self, **kwargs):
        # Implementation returning LabelInfo
        ...

    async def verify_callback(self, data, headers, **kwargs):
        # Validate signatures
        ...

    async def handle_callback(self, data, headers, **kwargs):
        # Process webhook
        ...

    async def fetch_shipment_status(self, **kwargs):
        # Poll provider API
        ...

    async def cancel_shipment(self, **kwargs):
        # Cancel shipment
        ...
```

## Capability Detection

The framework detects capabilities dynamically. This allows generic UI or background tasks to gracefully handle missing features:

```python
from sendparcel.provider import LabelProvider

if isinstance(provider, LabelProvider):
    label = await provider.create_label()
else:
    # Gracefully inform the user that labels are not supported
```

## Async Rules

- Providers must be async-first.
- Use `anyio` utilities for sleeps, timeouts, and async primitives.
- Do not block the event loop with sync HTTP clients (use `httpx.AsyncClient`).

## Quality Checks

```bash
uv sync --extra dev
uv run --extra dev ruff check src tests
uv run --extra dev pytest -q
```
