# Ecosystem compatibility matrix

| Package | Type | Depends on `python-sendparcel` |
|---|---|---|
| python-sendparcel-inpost | Provider | >=0.1.0 |
| django-sendparcel | Framework adapter | >=0.1.0 |
| fastapi-sendparcel | Framework adapter | >=0.1.0 |
| litestar-sendparcel | Framework adapter | >=0.1.0 |

## Plugin discovery

The ecosystem entry point group is: `sendparcel.providers`.

The reference `dummy` provider is built into `python-sendparcel`.

### Available provider plugins

| Entry point | Provider class | Package |
|---|---|---|
| `dummy` | `sendparcel.providers.dummy:DummyProvider` | `python-sendparcel` (built-in) |
| `inpost_locker` | `sendparcel_inpost.providers:InPostLockerProvider` | `python-sendparcel-inpost` |
| `inpost_courier` | `sendparcel_inpost.providers:InPostCourierProvider` | `python-sendparcel-inpost` |
