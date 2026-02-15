# Contributing to python-sendparcel

## Development setup

```bash
uv sync --extra dev
```

## Quality checks

```bash
uv run ruff check src tests
uv run pytest -q
uv run --extra dev ty check
```

## Ecosystem rules

- Keep APIs async-first.
- Use `anyio` for async primitives and async/sync bridging points.
- Preserve plugin compatibility with `python-sendparcel` core contracts.
