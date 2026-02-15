# Installation matrix

## Compatibility policy

- Ecosystem packages follow semantic versioning.
- `python-sendparcel` is the compatibility anchor.
- Provider plugins and adapters should depend on `python-sendparcel>=0.1.0`.
- All ecosystem packages are async-first and use `anyio`.

## Current matrix

| Package | Version | Requires |
|---|---:|---|
| python-sendparcel | 0.1.0 | Python 3.12+, anyio>=4.0 |
| django-sendparcel | 0.1.0 | python-sendparcel>=0.1.0, Django>=5.2, anyio>=4.0 |
| fastapi-sendparcel | 0.1.0 | python-sendparcel>=0.1.0, FastAPI>=0.115, anyio>=4.0 |
| litestar-sendparcel | 0.1.0 | python-sendparcel>=0.1.0, Litestar>=2.0, anyio>=4.0 |

## Recommended bundles

- `python-sendparcel` already includes the built-in `dummy` provider.
- `python-sendparcel[providers]` for built-in providers (currently no extra install required).
- `python-sendparcel[frameworks]` for all framework adapters.
- `python-sendparcel[all]` for core + all framework adapters.
