# Development and Verification

Reference: local dependency installation, gate commands, test tiers, and the live smoke test.

## Installing Dependencies

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Install the Redis extra as well to run the Redis adapter tests:

```bash
.venv/bin/pip install -e ".[dev,redis]"
```

With uv:

```bash
uv sync --all-extras
uv run pytest -q
```

## Gate Commands

```bash
.venv/bin/ruff format --check .   # must print nothing
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
```

The `ruff` configuration lives in `pyproject.toml`: `line-length = 100`, `target-version = "py310"`, with the rule set `E F I UP B SIM RUF N` enabled.

`mypy` runs in strict mode and only checks `src/qwx` (`files = ["src/qwx"]`), with Python 3.10 as the target version.

## Test Tiers

Run only the smallest test set directly related to the change.

| Tier | Change | What to run |
| --- | --- | --- |
| 1 | A single endpoint family / a single file | The module's `tests/test_*.py` + `ruff format --check .` + `mypy` |
| 2 | Cross-module (`client.py`, `auth.py`, `cache.py`, `location.py`) | The affected modules and the tests of their direct dependencies |
| 3 | Core refactoring (cache keys, location parsing, request execution) | Full `.venv/bin/python -m pytest tests/ -q` |

## Live Smoke Test

Under `live/` there are four test files and one shared fixture module. They carry the `live` marker and do not take part in `pytest tests/` by default (the test path only includes `tests/`). Real credentials are required; if any is missing the module is skipped, so CI does not fail for lack of credentials.

| File | Covers |
| --- | --- |
| `live/conftest.py` | Shared fixtures: read environment variables, build clients, skip marker when credentials are missing |
| `live/test_live_v1.py` | New generation: weather, air quality, weather alerts, solar radiation |
| `live/test_live_v7.py` | Old generation: astronomy, historical weather, life indices, minutely precipitation, tropical cyclones, tide |
| `live/test_live_geo.py` | GeoAPI: city lookup, POI lookup, POI range, top cities |
| `live/test_live_console.py` | Console: finance summary, request volume statistics |

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_API_KEY=YOUR_API_KEY \
.venv/bin/python -m pytest live/ -q -m live
```

Alternatively use JWT, where the private key is PEM content; a form with literal `\n` escapes is also accepted:

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)" \
QWX_KEY_ID=YOUR_KEY_ID \
QWX_PROJECT_ID=YOUR_PROJECT_ID \
QWX_DEVELOPER_ID=YOUR_DEVELOPER_ID \
.venv/bin/python -m pytest live/ -q -m live
```

Environment variables:

| Variable | Description |
| --- | --- |
| `QWX_API_HOST` | The dedicated API Host assigned in the console, required |
| `QWX_API_KEY` | API KEY, an alternative to JWT |
| `QWX_JWT_PRIVATE_KEY` | Ed25519 private key PEM content |
| `QWX_KEY_ID` | Key ID |
| `QWX_PROJECT_ID` | Project ID |
| `QWX_DEVELOPER_ID` | Developer ID |

With complete JWT credentials it uses JWT, otherwise it falls back to API KEY. When neither is fully configured, the whole module is skipped.

Run it after changing upstream behavior, endpoint fields, or request parameters, to verify real responses.

## Definition of Done

- `ruff format --check .` produces no output, `ruff check .` reports no warnings, `mypy` passes.
- Tests of the affected modules pass, including coverage of the error branches.
- When endpoint behavior changes, the corresponding sections of [Endpoint Contracts](endpoints.md), [Supported Endpoints](endpoints.md#supported-endpoints), and [Caching and TTL](cache.md) are updated.
- `.venv/bin/python -m pytest tests/ -q` is all green.
