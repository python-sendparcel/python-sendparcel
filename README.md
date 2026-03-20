# python-sendparcel

Framework-agnostic parcel shipping core for Python.

> Alpha notice: `0.1.1` is still unstable. The API can change fast because the
> ecosystem is still being cleaned up.

## What it is

- Provider-agnostic shipment orchestration with a single core flow.
- Explicit shipment metadata persistence: `id`, `status`, `provider`, `external_id`, `tracking_number`.
- Label payloads are operation results, not persisted shipment fields.
- One normalized provider update contract for both callbacks and polling.
- Runtime-checkable `Shipment` and `ShipmentRepository` protocols so adapters can use their own models.

## Core contract

- `ShipmentFlow.create_shipment(...) -> CreateShipmentOutcome`
- `ShipmentFlow.create_label(...) -> CreateLabelOutcome`
- `ShipmentFlow.handle_callback(...) -> ShipmentUpdateOutcome`
- `ShipmentFlow.fetch_and_update_status(...) -> ShipmentUpdateOutcome`
- `ShipmentFlow.cancel_shipment(...) -> bool`

`CreateShipmentOutcome` and `CreateLabelOutcome` return label payloads when available.
The shipment object never stores label bytes or a persisted `label_url` in the core contract.

## Quick start

```python
from dataclasses import dataclass
from decimal import Decimal

import anyio

from sendparcel import ShipmentFlow
from sendparcel.types import AddressInfo, ParcelInfo


@dataclass
class MyShipment:
    id: str
    status: str = "new"
    provider: str = ""
    external_id: str = ""
    tracking_number: str = ""


class InMemoryRepository:
    def __init__(self) -> None:
        self._store: dict[str, MyShipment] = {}
        self._counter = 0

    async def get_by_id(self, shipment_id: str) -> MyShipment:
        return self._store[shipment_id]

    async def create(self, **kwargs) -> MyShipment:
        self._counter += 1
        shipment = MyShipment(
            id=str(self._counter),
            status=str(kwargs.get("status", "new")),
            provider=str(kwargs.get("provider", "")),
        )
        self._store[shipment.id] = shipment
        return shipment

    async def save(self, shipment: MyShipment) -> MyShipment:
        self._store[shipment.id] = shipment
        return shipment


async def main() -> None:
    flow = ShipmentFlow(repository=InMemoryRepository())

    created = await flow.create_shipment(
        "dummy",
        sender_address=AddressInfo(
            name="Sender Co.",
            line1="Marszalkowska 1",
            city="Warsaw",
            postal_code="00-001",
            country_code="PL",
        ),
        receiver_address=AddressInfo(
            name="Jan Kowalski",
            line1="Dluga 10",
            city="Gdansk",
            postal_code="80-001",
            country_code="PL",
        ),
        parcels=[ParcelInfo(weight_kg=Decimal("2.5"))],
    )

    print(created.shipment.status)
    print(created.shipment.external_id)
    print(created.shipment.tracking_number)

    labelled = await flow.create_label(created.shipment)
    print(labelled.label.get("url"))


anyio.run(main)
```

## Provider model

- `BaseProvider.create_shipment(...)` returns `ShipmentCreateResult`.
- `BaseProvider.confirmation_method` defaults to `ConfirmationMethod.NONE`.
- `LabelProvider.create_label(...)` returns `LabelInfo`.
- `PushCallbackProvider.handle_callback(...)` returns `ShipmentUpdateResult`.
- `PullStatusProvider.fetch_shipment_status(...)` returns `ShipmentUpdateResult`.
- `CancellableProvider.cancel_shipment(...)` returns `bool`.

Use `ConfirmationMethod.PUSH` only with `PushCallbackProvider` and
`ConfirmationMethod.PULL` only with `PullStatusProvider`.

The core owns shipment state transitions. Providers translate carrier responses
into normalized results.

## Installation

```bash
pip install python-sendparcel
```

With `uv`:

```bash
uv add python-sendparcel
```

## Extras

- `django`
- `fastapi`
- `litestar`
- `inpost`
- `dpdpl`
- `cli`
- `frameworks`
- `providers`
- `all`

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy src tests
```
