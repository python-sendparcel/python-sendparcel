# Provider Authoring Guide

## Package naming

- Distribution: `python-sendparcel-<provider>`
- Import package: `sendparcel_<provider>`

## Entry point

Register providers in `pyproject.toml`:

```toml
[project.entry-points."sendparcel.providers"]
mycarrier = "sendparcel_mycarrier.provider:MyCarrierProvider"
```

## Provider contract

Every provider must subclass `sendparcel.provider.BaseProvider`.
There are no capability trait classes — `BaseProvider` declares every
capability method, and the unsupported ones raise
`ProviderCapabilityError` by default. Override only what the carrier
actually supports.

### Required

- `create_shipment(sender_address, receiver_address, parcels, **kwargs) -> ShipmentCreateResult`

### Optional capability overrides

| Capability | Method to override | Return value |
|---|---|---|
| Labels | `create_label(**kwargs)` | `LabelInfo` |
| Webhooks | `verify_callback(ctx)` + `handle_callback(ctx)` | `None` / `ShipmentUpdateResult` |
| Polling | `fetch_shipment_status(**kwargs)` | `ShipmentUpdateResult` |
| Cancellation | `cancel_shipment(**kwargs)` | `bool` |

Webhook methods receive a `sendparcel.types.CallbackContext` carrying
`shipment_id`, `payload`, `headers`, `source_ip`, and `raw_body`.

### Transport

Providers that talk HTTP declare a `transport_factory` classvar
(`transport_factory(**config) -> transport`). The factory is called by
`sendparcel.factory.create_provider`, and the built transport is
available inside the provider via `self._get_client()`. Configuration
fields are declared in `config_schema`; required fields are validated
automatically at construction time.

## Important rule

Providers do not mutate shipment state directly.

The core flow owns state transitions. Providers return normalized results:

- `ShipmentCreateResult` for creation
- `LabelInfo` for labels
- `ShipmentUpdateResult` for callbacks and polling

That means callback and polling implementations should translate carrier payloads into normalized status updates instead of calling model methods.

## Confirmation method

`BaseProvider.confirmation_method` defaults to `ConfirmationMethod.NONE`.

- `NONE` - the provider does not expose shipment updates.
- `PUSH` - the provider must override `verify_callback` and
  `handle_callback`.
- `PULL` - the provider must override `fetch_shipment_status`.

Do not declare `PUSH` or `PULL` unless the provider actually overrides the
matching capability methods.

## Minimal example

```python
from typing import Any, ClassVar

from sendparcel.enums import LabelFormat
from sendparcel.provider import BaseProvider
from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
)


class MyCarrierProvider(BaseProvider):
    slug: ClassVar[str] = "mycarrier"
    display_name: ClassVar[str] = "My Carrier"

    async def create_shipment(
        self,
        *,
        sender_address: AddressInfo,
        receiver_address: AddressInfo,
        parcels: list[ParcelInfo],
        **kwargs: Any,
    ) -> ShipmentCreateResult:
        return ShipmentCreateResult(
            external_id="carrier-123",
            tracking_number="TRACK-123",
        )

    async def create_label(self, **kwargs: Any) -> LabelInfo:
        return LabelInfo(
            format=LabelFormat.PDF,
            url="https://carrier.example/labels/TRACK-123.pdf",
        )
```

## Callback and polling example

```python
from sendparcel.enums import ConfirmationMethod
from sendparcel.types import CallbackContext, ShipmentUpdateResult


class StatusProvider(MyCarrierProvider):
    confirmation_method = ConfirmationMethod.PUSH

    async def verify_callback(self, ctx: CallbackContext) -> None:
        return None

    async def handle_callback(
        self, ctx: CallbackContext
    ) -> ShipmentUpdateResult:
        return ShipmentUpdateResult(status="in_transit")

    async def fetch_shipment_status(self, **kwargs) -> ShipmentUpdateResult:
        return ShipmentUpdateResult(status="delivered")
```

## Quality checks

```bash
uv sync --extra dev
uv run ruff check src tests
uv run pytest -q
```
