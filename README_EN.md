<p align="center">
  <img src="https://raw.githubusercontent.com/KanoCifer/qwx-py/main/assets/banner_en.png" width="100%" alt="qwx" />
</p>

<p align="center">
  <a href="https://github.com/KanoCifer/qwx-py/actions/workflows/ci.yml" target="_blank" rel="noopener"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/KanoCifer/qwx-py/ci.yml?branch=main" height="20"></a>
  <a href="https://pypi.org/project/qwx/" target="_blank" rel="noopener"><img alt="PyPI" src="https://img.shields.io/pypi/v/qwx" height="20"></a>
  <a href="https://pypi.org/project/qwx/" target="_blank" rel="noopener"><img alt="Python" src="https://img.shields.io/pypi/pyversions/qwx" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py/blob/main/LICENSE" target="_blank" rel="noopener"><img alt="License" src="https://img.shields.io/github/license/KanoCifer/qwx-py" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py#endpoints" target="_blank" rel="noopener"><img alt="Endpoints" src="https://img.shields.io/badge/endpoints-26-blue" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py#endpoints" target="_blank" rel="noopener"><img alt="Models" src="https://img.shields.io/badge/models-pydantic%20v2-success" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx" target="_blank" rel="noopener"><img alt="Go version" src="https://img.shields.io/badge/Go-reference-00ADD8?logo=go&logoColor=white" height="20"></a>
</p>

<p align="center">
  <a href="README.md"><b>简体中文</b></a> · <a href="README_EN.md">English</a>
</p>

qwx is a Python SDK for QWeather (和风天气). It covers 26 endpoints in 12 resource families, returns pydantic v2 models, and offers both a sync and an async client.

---

<a id="features"></a>
## ✨ Features

- **26 endpoints**: weather, air quality, alerts, solar radiation, GeoAPI, console, astronomy, historical weather, lifestyle indices, minutely precipitation, tropical cyclones and tides.
- **Sync and async clients** (httpx) share one implementation of every endpoint method; the async client returns coroutines.
- **pydantic v2 models** keep unknown upstream fields in `model_extra` instead of dropping them.
- **Local parameter validation**: out-of-range values and unsupported location shapes raise before any request is sent.
- **Layered errors**, classified by exception type rather than by parsing error strings.

---

<a id="installation"></a>
## 📦 Installation

```bash
pip install qwx
```

Requires Python 3.10 or later. Dependencies: `httpx`, `pydantic`, `cryptography` (JWT signing).

Install the optional extra for Redis caching:

```bash
pip install "qwx[redis]"
uv add "qwx[redis]"
```

---

<a id="quick-start"></a>
## 🚀 Quick start

Three steps: create the auth object, create the base client, create the service client for the endpoint family.

### Sync

```python
import qwx
from qwx.v1.weather import WeatherService

# 1. Auth. Use the console credentials with JWT, or qwx.APIKeyAuth for an API key.
auth = qwx.JWTAuth(
    private_key_pem=open("ed25519-private.pem", encoding="utf-8").read(),
    key_id="YOUR_KEY_ID",
    project_id="YOUR_PROJECT_ID",
    developer_id="YOUR_DEVELOPER_ID",  # required, from the console "Settings" page
)

# 2. Base client. api_host is the dedicated host assigned in the console, and is required.
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    # 3. Service client for the endpoint family.
    weather = WeatherService(client)
    result = weather.current(qwx.Location(lat=39.92, lon=116.41))
    print(result.condition.text, result.temperature.value, result.temperature.unit)
```

`Client` is a context manager and closes the underlying HTTP connections on exit. Without `with`, call `client.close()` yourself.

### Async

The async methods have the same names and return coroutines:

```python
import asyncio

import qwx
from qwx.v1.weather import AsyncWeatherService


async def main() -> None:
    auth = qwx.APIKeyAuth("YOUR_API_KEY")
    async with qwx.AsyncClient(auth, "abcxyz.qweatherapi.com") as client:
        weather = AsyncWeatherService(client)
        result = await weather.current(qwx.Location(lat=39.92, lon=116.41))
        print(result.condition.text)


asyncio.run(main())
```

### Runnable examples

Four scripts under `examples/` read their configuration from environment variables:

| Script | Content |
| --- | --- |
| `examples/basic_sync.py` | API key auth, current weather |
| `examples/basic_async.py` | The async version |
| `examples/jwt_auth.py` | JWT auth |
| `examples/cache_redis.py` | Redis cache |

```bash
QWX_API_KEY=YOUR_API_KEY QWX_API_HOST=your-host.qweatherapi.com python examples/basic_sync.py
```

---

<a id="guide"></a>
## 📖 Usage guide

<a id="authentication"></a>
### 🔑 Authentication

Pick one of the two mechanisms; they cannot be combined. New projects should use JWT.

| Mechanism | Constructor | Request header | Use for |
| --- | --- | --- | --- |
| `qwx.JWTAuth` | `qwx.JWTAuth(private_key_pem=..., key_id=..., project_id=..., developer_id=...)` | `Authorization: Bearer <JWT>` | New projects (default) |
| `qwx.APIKeyAuth` | `qwx.APIKeyAuth(key)` | `X-QW-Api-Key: <key>` | Existing projects |

The upstream has announced an API key quota limit starting 2027-01-01. The SDK no longer supports API keys from version 5 on.

JWT needs three console credentials and an Ed25519 key pair:

```bash
openssl genpkey -algorithm ED25519 -out ed25519-private.pem
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
```

| Parameter | Required | Description |
| --- | --- | --- |
| `private_key_pem` | Yes | Ed25519 PKCS#8 PEM text |
| `key_id` | Yes | Console Key ID, goes into the JWT header as `kid` |
| `project_id` | Yes | Console Project ID, goes into the payload as `sub` |
| `developer_id` | Yes | Console Developer ID, goes into the payload as `iss` |
| `token_ttl` | No | Token lifetime, defaults to `timedelta(minutes=15)` |

Missing any of the four required credentials raises `qwx.InvalidConfigError`. Tokens are re-signed one minute before expiry, with no impact on callers.

The dedicated API host is required as well: it is assigned on the console "Settings" page and looks like `abcxyz.qweatherapi.com`. The public domains are being retired and the SDK ships no default. A bare host gets `https://` prepended; a host with a scheme is used as given. Upstream rejects requests when the credentials and the host do not belong to the same developer account.

When authentication fails (401 / 403, raised as `qwx.UnauthorizedError`), check in this order:

1. `kid` matches the console Key ID.
2. `sub` is the Project ID, not the Developer ID.
3. `iss` is the Developer ID from the console "Settings" page, not a credential ID.
4. The private key and the public key uploaded to the console are one pair.
5. The credentials, the Developer ID and the API host belong to the same developer account.

<a id="client-options"></a>
### ⚙️ Client options

```python
client = qwx.Client(
    auth,
    "abcxyz.qweatherapi.com",
    timeout=30.0,  # per-request timeout in seconds
    cache=cache,  # cache implementation, None by default
    ttl_policy=policy,  # per-endpoint cache duration
    logger=logger,  # a standard library logging logger
    http_client=httpx.Client(...),  # custom httpx client
)
```

`api_host` has no default value; use the dedicated host assigned in the console.

<a id="location"></a>
### 📍 Location

`Location` has three forms, and each endpoint accepts only a subset of them. The forms are not interchangeable, and upstream rejects the wrong one.

| Form | Constructor | Accepted by |
| --- | --- | --- |
| Coordinate pair | `qwx.Location(lat=39.92, lon=116.41)` or `qwx.parse_location("116.41,39.92")` | Every endpoint except console, cyclones and top cities |
| LocationID | `qwx.Location(id="101010100")` | GeoAPI; astronomy sunrise/sunset and moon phase; historical weather. Administrative divisions are 9–10 digits, POIs are digits with a letter suffix, tide stations and monitoring stations are `P` plus digits |
| Place name | `qwx.Location(name="杭州")` | `GeoService.lookup_city` / `GeoService.lookup_poi` only |

```python
qwx.Location(lat=39.92, lon=116.41)  # coordinate pair
qwx.Location(id="101010100")  # LocationID
qwx.Location(name="杭州")  # place name, GeoAPI only
qwx.parse_location("116.41,39.92")  # parse a string: longitude first
```

Coordinates keep two decimals inside the SDK, and `-0` is normalized to `0.00`. `qwx.parse_location` rejects empty strings, non-numbers, NaN/Inf and out-of-range coordinates with `qwx.InvalidLocationError`. A coordinate of exactly `(0, 0)` makes `has_coordinates()` false, so it is treated as "no coordinates".

**New-generation endpoints (`/weather/v1/*` and friends) take the latitude first in the path**, while **v7 and GeoAPI take the longitude first in the query string**. Swapping them gets a 400 from upstream.

The table under [Supported endpoints](#endpoints) lists the form each endpoint accepts.

<a id="lang"></a>
### 🌐 Language

Upstream switches the response language with the `lang` query parameter. The language parameter is `qwx.Lang`; most endpoints take it inside `Options`, while `qwx.v7.indices` and `qwx.v7.minutely` take it as an argument.

- 31 languages are built in: `qwx.Lang.ZH`, `qwx.Lang.ZH_HANT`, `qwx.Lang.EN`, … the full list is in `qwx.LANGS`.
- Leaving it unset (`qwx.Lang.UNSPECIFIED`) omits `lang` and uses the upstream default: the official language of the country or region, falling back to English.
- Equivalent upstream codes (`zh-hans` for Simplified Chinese) resolve through `qwx.lookup_lang`; the request still sends the preferred code `zh`.
- A malformed language code raises `qwx.InvalidParameterError` without hitting upstream.
- Solar radiation, tides, cyclones, sunrise/sunset and solar elevation angle, and the console endpoints do not accept a language parameter, and the SDK does not expose one.

<a id="caching"></a>
### 🗄️ Caching

Without a `cache`, every request goes upstream. The cache interface has two methods; implement them yourself:

```python
from datetime import timedelta
from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, data: bytes, ttl: timedelta) -> None: ...
```

- A hit returns `bytes`, a miss returns `None`.
- Read and write failures may raise. The SDK swallows cache errors and falls back to a direct upstream call, so implementations are free to raise.
- `ttl` is a relative duration.

The built-in `qwx.MemoryCache` is in-process and locked, and is **not recommended for production**: it has no background cleanup, so expired entries that are never accessed again stay in the dictionary. It suits test doubles and single-instance scratch caches; multi-instance deployments need a shared cache.

The Redis adapter is an optional dependency (`pip install "qwx[redis]"`):

```python
import qwx
from qwx.redis_cache import RedisCache

# Build from a URL
cache = RedisCache.from_url("redis://127.0.0.1:6379/0")

# Or reuse an existing redis-py client
import redis

cache = RedisCache(redis.Redis(host="127.0.0.1", port=6379, db=0))

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

Cached values are raw JSON bytes, so keys and values are interchangeable with the Go version when both use one Redis. Do not enable `decode_responses=True` on the Redis client.

Default durations come from the endpoint module. Pass a `ttl_policy` to change them:

```python
from datetime import timedelta

import qwx
from qwx.v1.airquality import EndpointCurrent as AQCurrent
from qwx.v1.weather import EndpointCurrent

client = qwx.Client(
    auth,
    "abcxyz.qweatherapi.com",
    cache=cache,
    ttl_policy=qwx.TTLMap(
        {
            EndpointCurrent: timedelta(minutes=5),
            AQCurrent: timedelta(0),  # do not cache this endpoint
        }
    ),
)
```

To bypass the cache for a single call, use the context override:

```python
with client.override_ttl(timedelta(0)):  # neither read nor write the cache
    weather.current(loc)
```

Duration resolution order: per-call override > `TTLPolicy` > the endpoint module default.

Cache key templates, the default TTL of every endpoint and the key layout rules are documented in [docs/en/cache.md](docs/en/cache.md).

<a id="logging"></a>
### 📝 Logging

The SDK uses the standard library `logging` and ships no logging implementation of its own. Nothing is emitted until you inject a logger:

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

Without a logger the SDK attaches a `NullHandler` and drops everything. The handler decides the level: DEBUG shows cache hits and misses, INFO shows upstream requests, WARNING covers cache failures and upstream 4xx, ERROR covers upstream 5xx and response decoding failures.

Logs never contain credentials or response bodies. Field names, redaction and performance notes are in [docs/en/logging.md](docs/en/logging.md).

<a id="errors"></a>
### 🚨 Error handling

Every SDK exception inherits `qwx.QwxError`. Classify with `isinstance` / `except`, never by parsing error strings.

```
QwxError
├── InvalidConfigError
├── InvalidLocationError
├── InvalidParameterError
├── InvalidResponseError
└── UpstreamError
    ├── UpstreamRejectedError     upstream 4xx
    ├── QuotaExceededError        upstream 429
    ├── UnauthorizedError         upstream 401 / 403
    └── UpstreamUnavailableError  upstream 5xx or network error
```

| Exception | Raised when | Action |
| --- | --- | --- |
| `InvalidConfigError` | Constructor arguments are wrong: missing auth, empty private key, empty API key, empty API host | Fix the code, do not retry |
| `InvalidLocationError` | The location form is invalid or unsupported upstream | Fix the request, do not retry |
| `InvalidParameterError` | A parameter is out of range: `hours`, `days`, `type`, values other than `radius`, date formats, malformed language codes | Fix the request, do not retry |
| `InvalidResponseError` | The response is not valid JSON, or its shape does not match the model | Inspect `UpstreamError.body`; a retry may help |
| `UpstreamRejectedError` | Upstream 4xx | Fix the request, retrying is pointless |
| `QuotaExceededError` | Upstream 429 | Back off and retry |
| `UnauthorizedError` | Upstream 401 / 403 | Check the credentials |
| `UpstreamUnavailableError` | Upstream 5xx or a network error, including timeouts | Retry with exponential backoff |

The first four are raised locally and never reach upstream.

```python
import qwx

try:
    result = weather.current(loc)
except qwx.UnauthorizedError:
    ...  # check credentials
except qwx.QuotaExceededError:
    ...  # back off and retry
except qwx.InvalidParameterError:
    ...  # fix the request
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params)
except qwx.QwxError:
    ...  # every other SDK exception
```

`UpstreamError` carries the upstream details: `status_code` (HTTP status), `code` (upstream business code), `title` (one-line reason), `invalid_params` (names of invalid parameters, new-generation endpoints only) and `body` (raw response body, truncated to 2 KB).

The client retries with backoff on its own: upstream 5xx, 429 or network errors are retried up to 3 more times (`qwx.client.MAX_RETRY`). 4xx is not retried.

Cache failures never turn into business errors: when `get` or `set` raises, the SDK calls upstream directly.

<a id="concurrency"></a>
### ⏱️ Concurrency & timeout

`Client` and `AsyncClient` are stateless and can be shared across concurrent calls. The default per-request timeout is 30 seconds. Inject your own httpx client for proxies, connection pools or custom certificates:

```python
import httpx

import qwx

http = httpx.Client(
    timeout=httpx.Timeout(10.0, connect=3.0), limits=httpx.Limits(max_connections=50)
)
client = qwx.Client(auth, "abcxyz.qweatherapi.com", http_client=http)
```

The async version is the same, with an `httpx.AsyncClient`.

---

<a id="endpoints"></a>
## 🔌 Supported endpoints

26 endpoints across 12 resource families. The location form column is the one to check before calling.

| Package | Method | Upstream path | Location form |
| --- | --- | --- | --- |
| `qwx.console` | `finance` | `/finance/v1/summary` | None |
| `qwx.console` | `stats` | `/metrics/v1/stats` | None |
| `qwx.geo` | `lookup_city` | `/geo/v2/city/lookup` | Coordinates / LocationID / place name |
| `qwx.geo` | `lookup_poi` | `/geo/v2/poi/lookup` | Coordinates / LocationID / place name |
| `qwx.geo` | `poi_range` | `/geo/v2/poi/range` | Coordinates |
| `qwx.geo` | `top_cities` | `/geo/v2/city/top` | None |
| `qwx.v1.airquality` | `current` | `/airquality/v1/current/{lat}/{lon}` | Coordinates |
| `qwx.v1.airquality` | `daily` | `/airquality/v1/daily/{lat}/{lon}` | Coordinates |
| `qwx.v1.airquality` | `hourly` | `/airquality/v1/hourly/{lat}/{lon}` | Coordinates |
| `qwx.v1.airquality` | `station` | `/airquality/v1/stations/{stationID}` | Station ID |
| `qwx.v1.alert` | `current` | `/weatheralert/v1/current/{lat}/{lon}` | Coordinates |
| `qwx.v1.solarradiation` | `forecast` | `/solarradiation/v1/forecast/{lat}/{lon}` | Coordinates |
| `qwx.v1.weather` | `current` | `/weather/v1/current/{lat}/{lon}` | Coordinates |
| `qwx.v1.weather` | `hourly` | `/weather/v1/hourly/{lat}/{lon}` | Coordinates |
| `qwx.v1.weather` | `daily` | `/weather/v1/daily/{lat}/{lon}` | Coordinates |
| `qwx.v7.astronomy` | `sun` | `/v7/astronomy/sun` | Coordinates / LocationID |
| `qwx.v7.astronomy` | `moon` | `/v7/astronomy/moon` | Coordinates / LocationID |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `/v7/astronomy/solar-elevation-angle` | Coordinates |
| `qwx.v7.historical` | `weather` | `/v7/historical/weather` | LocationID |
| `qwx.v7.indices` | `indices` | `/v7/indices/{days}d` | Coordinates |
| `qwx.v7.indices` | `indices_multi` | `/v7/indices/{days}d` | Coordinates |
| `qwx.v7.minutely` | `minutely` | `/v7/minutely/5m` | Coordinates |
| `qwx.v7.ocean` | `tide` | `/v7/ocean/tide` | Station ID |
| `qwx.v7.storm` | `list` | `/v7/tropical/storm-list` | None |
| `qwx.v7.storm` | `forecast` | `/v7/tropical/storm-forecast` | None |
| `qwx.v7.storm` | `track` | `/v7/tropical/storm-track` | None |

Parameters, return types and value ranges of each endpoint are documented in [docs/en/endpoints.md](docs/en/endpoints.md).

---

<a id="reference"></a>
## 📚 Reference

| Document | Content |
| --- | --- |
| [docs/en/endpoints.md](docs/en/endpoints.md) | Endpoint contract: parameters, return types, value ranges, field semantics |
| [docs/en/cache.md](docs/en/cache.md) | Cache key templates, default TTL per endpoint, custom TTL |
| [docs/en/upstream.md](docs/en/upstream.md) | Retired upstream endpoints and their replacements, upstream quirks and limits |
| [docs/en/logging.md](docs/en/logging.md) | Log levels and fields, redaction |
| [docs/en/development.md](docs/en/development.md) | Environment, gate commands, test tiers, live smoke tests |

Chinese versions: [docs/zh/](docs/zh/).

Official documentation: <https://dev.qweather.com/docs/>

---

<a id="license"></a>
## ⚖️ License

This package is released under the MIT license.

This package is not an official QWeather product. Using upstream data requires compliance with the [QWeather Developer License Agreement](https://www.qweather.com/terms/developers-eula/), and the attribution returned by upstream must be preserved when displaying weather data.
