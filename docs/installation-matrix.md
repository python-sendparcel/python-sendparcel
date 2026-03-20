# Installation matrix

## Compatibility policy

- Ecosystem packages follow semantic versioning.
- `python-sendparcel` is the compatibility anchor.
- Provider plugins and adapters should depend on `python-sendparcel>=0.1.1`.
- All ecosystem packages are async-first and use `anyio`.

## Current matrix

| Package | Version | Requires |
|---|---:|---|
| python-sendparcel | 0.1.1 | Python 3.12+, anyio>=4.0 |
| python-sendparcel-inpost | 0.1.1 | python-sendparcel>=0.1.1, httpx>=0.27.0, anyio>=4.0 |
| python-sendparcel-dpdpl | 0.1.1 | python-sendparcel>=0.1.1, httpx>=0.27.0, anyio>=4.0 |
| django-sendparcel | 0.1.0 | python-sendparcel>=0.1.1, Django>=5.2, anyio>=4.0 |
| fastapi-sendparcel | 0.1.0 | python-sendparcel>=0.1.1, FastAPI>=0.115, anyio>=4.0 |
| litestar-sendparcel | 0.1.0 | python-sendparcel>=0.1.1, Litestar>=2.0, anyio>=4.0 |

## Recommended bundles

- `python-sendparcel` already includes the built-in `dummy` provider.
- `python-sendparcel[inpost]` for the InPost ShipX provider.
- `python-sendparcel[dpdpl]` for the DPD Poland provider.
- `python-sendparcel[providers]` for bundled provider extras.
- `python-sendparcel[frameworks]` for all framework adapters.
- `python-sendparcel[all]` for core + all framework adapters.
