# Getting started

## Installation

Requires Python 3.12+.

```bash
pip install python-sendparcel
```

With `uv`:

```bash
uv add python-sendparcel
```

## Core ideas

- `Shipment` and `ShipmentRepository` are protocols. Bring your own models.
- Providers translate carrier APIs into normalized core results.
- `ShipmentFlow` owns orchestration and status transitions.
- Labels are returned from operations and are not persisted by the core contract.
- Callback and polling paths share the same normalized update shape.

## Minimal example

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

    label = await flow.create_label(created.shipment)
    print(label.label.get("url"))


anyio.run(main)
```

## Provider configuration

```python
flow = ShipmentFlow(
    repository=repo,
    config={
        "mycarrier": {
            "api_key": "sk_live_...",
            "sandbox": True,
        },
    },
)
```

Providers access settings with `self.get_setting("api_key")`.
