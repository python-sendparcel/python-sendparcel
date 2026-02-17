# python-sendparcel documentation

**Framework-agnostic parcel shipping core for Python.**

python-sendparcel provides a provider plugin system, shipment lifecycle management,
and async orchestration for integrating with parcel carriers. You bring your own
models and persistence — the library handles state transitions, provider
communication, and plugin discovery.

```{admonition} Alpha notice
:class: warning
This project is at version **0.1.0**. The public API may change between minor
releases until 1.0 is reached. Pin your dependency accordingly.
```

## Highlights

- **Provider plugin system** — register carriers via entry points or manually; auto-discovered at first use.
- **Shipment domain types** — strict TypedDicts (`AddressInfo`, `ParcelInfo`, `LabelInfo`, and more).
- **9-state finite state machine** — `NEW` through `DELIVERED`, plus `CANCELLED`, `FAILED`, and `RETURNED`, with guarded transitions.
- **ShipmentFlow orchestrator** — async workflow for creating shipments, fetching labels, handling callbacks, polling status, and cancelling.
- **Runtime protocols** — `Shipment` and `ShipmentRepository` are `@runtime_checkable`; bring your own models and persistence.
- **Built-in DummyProvider** — deterministic reference provider for testing and local development.
- **Async-first** — the entire runtime is async, powered by [anyio](https://anyio.readthedocs.io/).

## Ecosystem

python-sendparcel is the core library. Framework-specific adapters provide
native models, views/routes, and repository implementations:

| Package | Framework |
|---|---|
| [django-sendparcel](https://github.com/python-sendparcel/django-sendparcel) | Django |
| [fastapi-sendparcel](https://github.com/python-sendparcel/fastapi-sendparcel) | FastAPI |
| [litestar-sendparcel](https://github.com/python-sendparcel/litestar-sendparcel) | Litestar |

Install adapters via extras: `pip install python-sendparcel[django]`,
`[fastapi]`, `[litestar]`, `[frameworks]`, or `[all]`.

```{toctree}
:maxdepth: 2
:caption: Contents

getting-started
provider-authoring
installation-matrix
compatibility-matrix
release-policy
```
