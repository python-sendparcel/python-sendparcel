# Getting started

## Installation

Requires **Python 3.12+**.

With pip:

```bash
pip install python-sendparcel
```

With uv:

```bash
uv add python-sendparcel
```

### Framework extras

To install a framework adapter alongside the core:

```bash
pip install python-sendparcel[django]      # Django integration
pip install python-sendparcel[fastapi]     # FastAPI integration
pip install python-sendparcel[litestar]    # Litestar integration
pip install python-sendparcel[frameworks]  # all framework adapters
pip install python-sendparcel[all]         # everything
```

See the {doc}`installation-matrix` for version requirements and compatibility.

## Core concepts

python-sendparcel is built around four ideas:

Protocols
: `Shipment` and `ShipmentRepository` are `@runtime_checkable`
  protocols defined in `sendparcel.protocols`. You implement them with your own
  classes (dataclasses, Django models, SQLAlchemy models, etc.) — the library
  never forces a particular ORM or persistence layer.

Providers
: A provider is a subclass of `sendparcel.provider.BaseProvider` that
  communicates with a specific carrier API. Providers are discovered
  automatically via the `sendparcel.providers` entry-point group, or can be
  registered manually. The built-in `DummyProvider` is always available for
  testing.

ShipmentFlow
: `sendparcel.ShipmentFlow` is the async orchestrator. Given a repository and
  (optionally) provider configuration, it manages the full shipment lifecycle:
  creating shipments, fetching labels, handling carrier callbacks, polling
  status, and cancelling.

Finite state machine
: Every shipment moves through a 9-state lifecycle:

  ```
  NEW → CREATED → LABEL_READY → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED
  ```

  Plus three terminal/side states: `CANCELLED`, `FAILED`, and `RETURNED`.
  Transitions are guarded — for example, `confirm_label` requires `label_url`
  to be set, and `mark_in_transit` requires `tracking_number`.

## Minimal working example

The example below implements the two protocols and uses `ShipmentFlow` with
the built-in `DummyProvider` to create a shipment.

### 1. Implement the Shipment and ShipmentRepository protocols

```python
from dataclasses import dataclass


@dataclass
class MyShipment:
    """Satisfies the sendparcel Shipment protocol."""

    id: str
    status: str = ""
    provider: str = ""
    external_id: str = ""
    tracking_number: str = ""
    label_url: str = ""


class InMemoryRepository:
    """Minimal in-memory ShipmentRepository for demonstration."""

    def __init__(self):
        self._store: dict[str, MyShipment] = {}
        self._counter = 0

    async def get_by_id(self, shipment_id: str) -> MyShipment:
        return self._store[shipment_id]

    async def create(self, **kwargs) -> MyShipment:
        self._counter += 1
        shipment_id = str(self._counter)
        shipment = MyShipment(
            id=shipment_id,
            status=kwargs.get("status", ""),
            provider=kwargs.get("provider", ""),
        )
        self._store[shipment_id] = shipment
        return shipment

    async def save(self, shipment: MyShipment) -> MyShipment:
        self._store[shipment.id] = shipment
        return shipment

    async def update_status(
        self, shipment_id: str, status: str, **fields
    ) -> MyShipment:
        shipment = self._store[shipment_id]
        shipment.status = status
        return shipment
```

### 2. Create a shipment with ShipmentFlow

```python
import anyio
from decimal import Decimal

from sendparcel import ShipmentFlow
from sendparcel.types import AddressInfo, ParcelInfo


async def main():
    repo = InMemoryRepository()
    flow = ShipmentFlow(repository=repo)

    # Create shipment using the built-in dummy provider
    shipment = await flow.create_shipment(
        "dummy",
        sender_address=AddressInfo(
            name="Sender Co.",
            line1="ul. Marszalkowska 1",
            city="Warszawa",
            postal_code="00-001",
            country_code="PL",
        ),
        receiver_address=AddressInfo(
            name="Jan Kowalski",
            line1="ul. Dluga 10",
            city="Gdansk",
            postal_code="80-001",
            country_code="PL",
        ),
        parcels=[ParcelInfo(weight_kg=Decimal("2.5"))],
    )
    print(shipment.status)           # "created" or "label_ready"
    print(shipment.external_id)      # "dummy-1"
    print(shipment.tracking_number)  # "DUMMY-1"


anyio.run(main)
```

## Provider configuration

Pass per-provider settings when constructing `ShipmentFlow`:

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

Inside a provider, retrieve settings with `self.get_setting("api_key")`.

## Next steps

- {doc}`provider-authoring` — how to write and register a custom carrier provider.
- {doc}`installation-matrix` — version requirements and compatibility across the ecosystem.
- {doc}`compatibility-matrix` — which adapter versions work with which core version.
