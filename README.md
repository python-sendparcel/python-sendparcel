# python-sendparcel

[![PyPI](https://img.shields.io/pypi/v/python-sendparcel.svg)](https://pypi.org/project/python-sendparcel/)
[![Python Version](https://img.shields.io/pypi/pyversions/python-sendparcel.svg)](https://pypi.org/project/python-sendparcel/)
[![License](https://img.shields.io/pypi/l/python-sendparcel.svg)](https://pypi.org/project/python-sendparcel/)

Framework-agnostic parcel shipping core for Python.

---

> **Alpha notice** — This project is at version **0.1.0**. The public API
> may change between minor releases until 1.0 is reached. Pin your
> dependency accordingly.

## Features

- **Provider plugin system** — register providers via entry points or manually; auto-discovery at first use.
- **Shipment domain types** — `AddressInfo`, `ParcelInfo`, `LabelInfo`, `ShipmentCreateResult`, `ShipmentStatusResponse`, and `TrackingEvent` as strict TypedDicts.
- **Finite state machine** — 9-state `ShipmentStatus` enum (`NEW` → `CREATED` → `LABEL_READY` → `IN_TRANSIT` → `OUT_FOR_DELIVERY` → `DELIVERED`, plus `CANCELLED`, `FAILED`, `RETURNED`) with guarded transitions powered by [transitions](https://github.com/pytransitions/transitions).
- **ShipmentFlow orchestrator** — framework-agnostic async workflow for creating shipments, fetching labels, handling callbacks, polling status, and cancelling.
- **BaseProvider ABC** — define your own provider by subclassing a single class with well-defined async methods.
- **Built-in DummyProvider** — deterministic reference provider for testing and local development.
- **Pluggable validators** — attach validator callables to `ShipmentFlow` for global or per-operation validation.
- **Runtime protocols** — `Order`, `Shipment`, and `ShipmentRepository` are `@runtime_checkable` protocols; bring your own models and persistence.
- **Async-first** — the entire runtime is async, powered by [anyio](https://anyio.readthedocs.io/).

## Installation

### With pip

```bash
pip install python-sendparcel
```

### With uv

```bash
uv add python-sendparcel
```

### Provider plugins

Install provider packages for real carrier APIs:

```bash
pip install python-sendparcel[inpost]    # InPost ShipX (locker & courier)
```

### Framework adapters

Install the adapter for your web framework:

```bash
pip install python-sendparcel[django]    # Django integration
pip install python-sendparcel[fastapi]   # FastAPI integration
pip install python-sendparcel[litestar]  # Litestar integration
pip install python-sendparcel[frameworks]  # all framework adapters
pip install python-sendparcel[all]       # everything
```

### Extras reference

| Extra | Installs |
|---|---|
| `dummy` | Built-in dummy provider (no extra package) |
| `inpost` | `python-sendparcel-inpost` — InPost ShipX provider |
| `django` | `django-sendparcel` |
| `fastapi` | `fastapi-sendparcel` |
| `litestar` | `litestar-sendparcel` |
| `providers` | Built-in providers (currently `dummy`) |
| `frameworks` | All framework adapters |
| `all` | Framework adapters |

## Quick Start

python-sendparcel is framework-agnostic. You provide implementations of three
protocols — `Order`, `Shipment`, and `ShipmentRepository` — and the library
handles orchestration, state transitions, and provider communication.

### 1. Implement the Order protocol

```python
from decimal import Decimal
from dataclasses import dataclass, field

from sendparcel.types import AddressInfo, ParcelInfo


@dataclass
class MyOrder:
    """Satisfies the sendparcel Order protocol."""

    sender: AddressInfo
    receiver: AddressInfo
    parcels: list[ParcelInfo] = field(default_factory=list)

    def get_total_weight(self) -> Decimal:
        return sum(p["weight_kg"] for p in self.parcels)

    def get_parcels(self) -> list[ParcelInfo]:
        return self.parcels

    def get_sender_address(self) -> AddressInfo:
        return self.sender

    def get_receiver_address(self) -> AddressInfo:
        return self.receiver
```

### 2. Implement the Shipment and ShipmentRepository protocols

```python
from dataclasses import dataclass


@dataclass
class MyShipment:
    """Satisfies the sendparcel Shipment protocol."""

    id: str
    order: MyOrder
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
            order=kwargs["order"],
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

### 3. Create a shipment with ShipmentFlow

```python
import anyio

from sendparcel import ShipmentFlow, ShipmentStatus
from sendparcel.types import AddressInfo, ParcelInfo


async def main():
    repo = InMemoryRepository()
    flow = ShipmentFlow(repository=repo)

    order = MyOrder(
        sender=AddressInfo(
            name="Sender Co.",
            line1="ul. Marszalkowska 1",
            city="Warszawa",
            postal_code="00-001",
            country_code="PL",
        ),
        receiver=AddressInfo(
            name="Jan Kowalski",
            line1="ul. Dluga 10",
            city="Gdansk",
            postal_code="80-001",
            country_code="PL",
        ),
        parcels=[ParcelInfo(weight_kg=Decimal("2.5"))],
    )

    # Create shipment using the built-in dummy provider
    shipment = await flow.create_shipment(order, provider_slug="dummy")
    print(shipment.status)           # "created" or "label_ready"
    print(shipment.external_id)      # "dummy-1"
    print(shipment.tracking_number)  # "DUMMY-1"


anyio.run(main)
```

## Architecture

python-sendparcel is organized into focused modules:

```
sendparcel/
├── __init__.py          # Public API surface
├── enums.py             # ShipmentStatus, ConfirmationMethod
├── types.py             # TypedDict definitions (AddressInfo, ParcelInfo, …)
├── protocols.py         # Order, Shipment, ShipmentRepository protocols
├── provider.py          # BaseProvider ABC
├── registry.py          # PluginRegistry with entry-point discovery
├── flow.py              # ShipmentFlow orchestrator
├── fsm.py               # State machine transitions (pytransitions)
├── validators.py        # Pluggable validation chain
├── exceptions.py        # Exception hierarchy
└── providers/
    ├── __init__.py      # Built-in provider list
    └── dummy.py         # DummyProvider reference implementation
```

### Key components

| Component | Module | Description |
|---|---|---|
| `ShipmentFlow` | `flow.py` | Async orchestrator — creates shipments, fetches labels, handles callbacks, polls status, cancels. |
| `BaseProvider` | `provider.py` | Abstract base class that all shipping providers must subclass. |
| `PluginRegistry` | `registry.py` | Discovers providers from `sendparcel.providers` entry points and built-ins. Global `registry` singleton. |
| `ShipmentStatus` | `enums.py` | 9-state `StrEnum` representing the shipment lifecycle. |
| Domain types | `types.py` | `AddressInfo`, `ParcelInfo`, `LabelInfo`, `ShipmentCreateResult`, `ShipmentStatusResponse`, `TrackingEvent`. |
| Protocols | `protocols.py` | `Order`, `Shipment`, `ShipmentRepository` — all `@runtime_checkable`. |
| FSM | `fsm.py` | Transition definitions with guards (e.g. `label_url` required before `confirm_label`). |
| Validators | `validators.py` | Chain of callables invoked before provider operations. |

### Shipment state machine

```
                                                    mark_in_transit
                                              ┌────────────────────┐
                                              │                    ▼
NEW ──confirm_created──▸ CREATED ──confirm_label──▸ LABEL_READY   IN_TRANSIT ──mark_out_for_delivery──▸ OUT_FOR_DELIVERY
 │                         │                          │            │  │                                    │  │
 │                         │                          │            │  ├── mark_delivered ─────────────────▸│  │
 │                         │                          │            │  │                                    │  │
 │                         │                          │            │  │       mark_delivered               │  │
 │                         │                          │            │  │  ┌────────────────────────────────-─┘  │
 │                         │                          │            │  │  ▼                                    │
 │                         │                          │            │  │ DELIVERED                              │
 │                         │                          │            │  │  │                                    │
 │                         │                          │            │  │  └── mark_returned ──▸ RETURNED ◂─────┤
 │                         │                          │            │  │                          ▴            │
 │                         │                          │            │  └── mark_returned ─────────┘            │
 │                         │                          │            │                                          │
 └──────── cancel ─────────┴────── cancel ────────────┴──▸ CANCELLED                                         │
                                                                                                             │
 Any of {NEW, CREATED, LABEL_READY, IN_TRANSIT, OUT_FOR_DELIVERY} ──fail──▸ FAILED                           │
```

Guards enforce data integrity:
- `confirm_label` requires `label_url` to be set on the shipment.
- `mark_in_transit` requires `tracking_number` to be set on the shipment.

## Provider Authoring

Create a provider by subclassing `BaseProvider` and implementing `create_shipment`:

```python
from typing import ClassVar

from sendparcel.provider import BaseProvider
from sendparcel.types import ShipmentCreateResult


class MyCarrierProvider(BaseProvider):
    slug: ClassVar[str] = "mycarrier"
    display_name: ClassVar[str] = "My Carrier"
    supported_countries: ClassVar[list[str]] = ["PL", "DE"]
    supported_services: ClassVar[list[str]] = ["standard"]

    async def create_shipment(self, **kwargs) -> ShipmentCreateResult:
        # Call your carrier's API here
        api_key = self.get_setting("api_key")
        sender = self.shipment.order.get_sender_address()
        receiver = self.shipment.order.get_receiver_address()
        # ... HTTP call to carrier API ...
        return ShipmentCreateResult(
            external_id="carrier-12345",
            tracking_number="TRACK-12345",
        )
```

### Entry-point registration

Declare your provider in `pyproject.toml` so it is auto-discovered:

```toml
[project.entry-points."sendparcel.providers"]
mycarrier = "mycarrier_sendparcel.provider:MyCarrierProvider"
```

### Manual registration

```python
from sendparcel import registry

registry.register(MyCarrierProvider)
```

### Provider configuration

Pass per-provider settings through `ShipmentFlow`:

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

Settings are accessible inside the provider via `self.get_setting("api_key")`.

### Optional methods

Beyond the required `create_shipment`, providers can override:

| Method | Purpose |
|---|---|
| `create_label(**kwargs)` | Generate or fetch a shipping label. |
| `verify_callback(data, headers, **kwargs)` | Validate webhook authenticity. |
| `handle_callback(data, headers, **kwargs)` | Apply webhook status updates. |
| `fetch_shipment_status(**kwargs)` | Poll current shipment status. |
| `cancel_shipment(**kwargs)` | Cancel a shipment. |

### Class-level attributes

| Attribute | Type | Description |
|---|---|---|
| `slug` | `str` | Unique provider identifier. |
| `display_name` | `str` | Human-readable name. |
| `supported_countries` | `list[str]` | ISO country codes. |
| `supported_services` | `list[str]` | Service level identifiers. |
| `confirmation_method` | `ConfirmationMethod` | `PUSH` (webhook) or `PULL` (polling). Default: `PUSH`. |
| `user_selectable` | `bool` | Whether this provider appears in `registry.get_choices()`. Default: `True`. |

## Ecosystem

python-sendparcel is the core library. Framework-specific integrations are
provided by separate packages:

| Package | Type | Repository |
|---|---|---|
| [python-sendparcel-inpost](https://github.com/sendparcel/python-sendparcel-inpost) | Provider — InPost ShipX (locker & courier) | `sendparcel/python-sendparcel-inpost` |
| [django-sendparcel](https://github.com/sendparcel/django-sendparcel) | Framework adapter — Django | `sendparcel/django-sendparcel` |
| [fastapi-sendparcel](https://github.com/sendparcel/fastapi-sendparcel) | Framework adapter — FastAPI | `sendparcel/fastapi-sendparcel` |
| [litestar-sendparcel](https://github.com/sendparcel/litestar-sendparcel) | Framework adapter — Litestar | `sendparcel/litestar-sendparcel` |

Each framework wrapper provides framework-native models, views/routes, and
repository implementations so you don't have to write the boilerplate shown in
the Quick Start above.

Provider packages (like `python-sendparcel-inpost`) supply carrier-specific
`BaseProvider` subclasses that integrate with real shipping APIs.

## Supported Versions

| Python | Status |
|---|---|
| 3.12+ | Supported |
| 3.13 | Supported |
| < 3.12 | Not supported |

### Core dependencies

| Package | Minimum version |
|---|---|
| `transitions` | 0.9.0 |
| `httpx` | 0.27.0 |
| `anyio` | 4.0 |

## Running Tests

The test suite uses **pytest** with **pytest-asyncio**.

```bash
# Install dev dependencies
uv sync --extra dev

# Run the full test suite
uv run pytest

# With coverage
uv run pytest --cov=sendparcel --cov-report=term-missing
```

## Credits

- **Author:** Dominik Kozaczko ([dominik@kozaczko.info](mailto:dominik@kozaczko.info))
- Inspired by the [django-getpaid](https://github.com/django-getpaid/django-getpaid) architecture and plugin model.

## License

[MIT](https://opensource.org/licenses/MIT)
