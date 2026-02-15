# python-sendparcel

Core runtime package for the sendparcel ecosystem.

## Scope

- Provider protocol and plugin registry
- Shipment domain types and state machine
- Framework-agnostic shipment flow orchestration
- Async-first runtime powered by `anyio`

## Installation

Install core only:

```bash
pip install python-sendparcel
```

The reference dummy provider is built in:

```bash
python -c "from sendparcel.providers.dummy import DummyProvider; print(DummyProvider.slug)"
```

Install framework adapters:

```bash
pip install python-sendparcel[django]
pip install python-sendparcel[fastapi]
pip install python-sendparcel[litestar]
pip install python-sendparcel[frameworks]
```

Install everything:

```bash
pip install python-sendparcel[all]
```

## Extras reference

| Extra | Installs |
|---|---|
| `dummy` | Built-in dummy provider (no extra package) |
| `django` | `django-sendparcel` |
| `fastapi` | `fastapi-sendparcel` |
| `litestar` | `litestar-sendparcel` |
| `providers` | Built-in providers (currently `dummy`) |
| `frameworks` | All framework adapters |
| `all` | Framework adapters |

See `docs/installation-matrix.md` for compatibility details and `docs/release-policy.md` for semantic-versioning rules.
