# Ecosystem compatibility matrix

| Package | Type | Depends on `python-sendparcel` |
|---|---|---|
| python-sendparcel-inpost | Provider | >=0.1.1 |
| python-sendparcel-dpdpl | Provider | >=0.1.1 |
| django-sendparcel | Framework adapter | >=0.1.1 |
| fastapi-sendparcel | Framework adapter | >=0.1.1 |
| litestar-sendparcel | Framework adapter | >=0.1.1 |

## Plugin discovery

The ecosystem entry point group is: `sendparcel.providers`.

The reference `dummy` provider is built into `python-sendparcel`.

### Available provider plugins

| Entry point | Provider class | Package |
|---|---|---|
| `dummy` | `sendparcel.providers.dummy:DummyProvider` | `python-sendparcel` (built-in) |
| `inpost_locker` | `sendparcel_inpost.providers:InPostLockerProvider` | `python-sendparcel-inpost` |
| `inpost_courier` | `sendparcel_inpost.providers:InPostCourierProvider` | `python-sendparcel-inpost` |
| `dpd_standard` | `sendparcel_dpdpl.providers.standard:DPDStandardProvider` | `python-sendparcel-dpdpl` |
| `dpd_pickup` | `sendparcel_dpdpl.providers.pickup:DPDPickupProvider` | `python-sendparcel-dpdpl` |
