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

### Required

- `create_shipment(sender_address, receiver_address, parcels, **kwargs) -> ShipmentCreateResult`

### Optional traits

| Capability | Trait | Return value |
|---|---|---|
| Labels | `LabelProvider` | `LabelInfo` |
| Webhooks | `PushCallbackProvider` | `ShipmentUpdateResult` |
| Polling | `PullStatusProvider` | `ShipmentUpdateResult` |
| Cancellation | `CancellableProvider` | `bool` |

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
- `PUSH` - the provider must implement `PushCallbackProvider`.
- `PULL` - the provider must implement `PullStatusProvider`.

Do not declare `PUSH` or `PULL` unless the provider actually implements the
matching capability trait.

## Minimal example

```python
from typing import Any, ClassVar

from sendparcel.provider import BaseProvider, LabelProvider
from sendparcel.types import (
    AddressInfo,
    LabelInfo,
    ParcelInfo,
    ShipmentCreateResult,
)


class MyCarrierProvider(BaseProvider, LabelProvider):
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
            format="PDF",
            url="https://carrier.example/labels/TRACK-123.pdf",
        )
```

## Callback and polling example

```python
from sendparcel.provider import PullStatusProvider, PushCallbackProvider
from sendparcel.types import ShipmentUpdateResult


class StatusProvider(BaseProvider, PushCallbackProvider, PullStatusProvider):
    async def verify_callback(self, data, headers, **kwargs) -> None:
        return None

    async def handle_callback(
        self, data, headers, **kwargs
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
