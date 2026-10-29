<p align="center">
  <a href="README.md"><b>简体中文</b></a> · <a href="README_EN.md">English</a>
</p>

# qwx

A Python client for the QWeather (和风天气) developer service.

qwx covers the core endpoint families in the upstream documentation and returns pydantic models; all 26 endpoints are implemented. The Python version is semantically equivalent to the Go version ([KanoCifer/qwx](https://github.com/KanoCifer/qwx)): same endpoint set, same cache key bytes, same endpoint constant values, same error classification, same TTL precedence.

---

## Installation

```bash
pip install qwx
```

Requires Python 3.10 or newer. Depends on `httpx`, `pydantic`, `cryptography`.

Install the optional extra for Redis caching:

```bash
pip install "qwx[redis]"
```

---

## Quick start

Three steps: create the authentication, create the base client, create the service client for an endpoint family.

### Sync

```python
import qwx
from qwx.v1.weather import WeatherService

# 1. Authentication. Use JWTAuth with the credentials from the console,
#    or APIKeyAuth.
auth = qwx.JWTAuth(
    private_key_pem=open("ed25519-private.pem", encoding="utf-8").read(),
    key_id="YOUR_KEY_ID",
    project_id="YOUR_PROJECT_ID",
    developer_id="YOUR_DEVELOPER_ID",  # required, console "Settings" page
)

# 2. Base client. api_host is the dedicated host assigned on the console
#    "Settings" page, and it is required.
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    # 3. Service client for the endpoint family.
    weather = WeatherService(client)
    result = weather.current(qwx.Location(lat=39.92, lon=116.41))
    print(result.condition.text, result.temperature.value, result.temperature.unit)
```

`Client` is a context manager: leaving the `with` block closes the underlying HTTP connection. Call `client.close()` yourself when you do not use the block.

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

### Locations

```python
qwx.Location(lat=39.92, lon=116.41)  # coordinate pair
qwx.Location(id="101010100")  # LocationID
qwx.Location(name="Hangzhou")  # place name, GeoAPI only
qwx.parse_location("116.41,39.92")  # parse a string: longitude first
```

New-generation endpoints (`/weather/v1/*` and friends) take path parameters with **latitude first**; v7 and GeoAPI take query parameters with **longitude first**. Swapping them gets you a 400 from the upstream. See [docs/endpoints.md](docs/endpoints.md).

### Runnable examples

Four scripts under `examples/` read their configuration from the environment and run as they are:

| Script | Contents |
| --- | --- |
| `examples/basic_sync.py` | API KEY authentication, current weather |
| `examples/basic_async.py` | The async version |
| `examples/jwt_auth.py` | JWT authentication |
| `examples/cache_redis.py` | Redis-backed cache |

```bash
QWX_API_KEY=YOUR_API_KEY QWX_API_HOST=your-host.qweatherapi.com python examples/basic_sync.py
```

---

## Supported endpoints

26 endpoints, one to one with [docs/endpoints.md](docs/endpoints.md) (which also lists the location form, default TTL and cache key template).

| Module | Method | Upstream endpoint | Endpoint constant |
| --- | --- | --- | --- |
| `qwx.console` | `finance` | `GET /finance/v1/summary` | `qwx.console.EndpointFinance` |
| `qwx.console` | `stats` | `GET /metrics/v1/stats` | `qwx.console.EndpointStats` |
| `qwx.geo` | `lookup_city` | `GET /geo/v2/city/lookup` | `qwx.geo.EndpointCity` |
| `qwx.geo` | `lookup_poi` | `GET /geo/v2/poi/lookup` | `qwx.geo.EndpointPOI` |
| `qwx.geo` | `poi_range` | `GET /geo/v2/poi/range` | `qwx.geo.EndpointPOIRange` |
| `qwx.geo` | `top_cities` | `GET /geo/v2/city/top` | `qwx.geo.EndpointTopCities` |
| `qwx.v1.airquality` | `current` | `GET /airquality/v1/current/{lat}/{lon}` | `qwx.v1.airquality.EndpointCurrent` |
| `qwx.v1.airquality` | `daily` | `GET /airquality/v1/daily/{lat}/{lon}` | `qwx.v1.airquality.EndpointDaily` |
| `qwx.v1.airquality` | `hourly` | `GET /airquality/v1/hourly/{lat}/{lon}` | `qwx.v1.airquality.EndpointHourly` |
| `qwx.v1.airquality` | `station` | `GET /airquality/v1/stations/{stationID}` | `qwx.v1.airquality.EndpointStation` |
| `qwx.v1.alert` | `current` | `GET /weatheralert/v1/current/{lat}/{lon}` | `qwx.v1.alert.Endpoint` |
| `qwx.v1.solarradiation` | `forecast` | `GET /solarradiation/v1/forecast/{lat}/{lon}` | `qwx.v1.solarradiation.Endpoint` |
| `qwx.v1.weather` | `current` | `GET /weather/v1/current/{lat}/{lon}` | `qwx.v1.weather.EndpointCurrent` |
| `qwx.v1.weather` | `hourly` | `GET /weather/v1/hourly/{lat}/{lon}` | `qwx.v1.weather.EndpointHourly` |
| `qwx.v1.weather` | `daily` | `GET /weather/v1/daily/{lat}/{lon}` | `qwx.v1.weather.EndpointDaily` |
| `qwx.v7.astronomy` | `sun` | `GET /v7/astronomy/sun` | `qwx.v7.astronomy.EndpointSun` |
| `qwx.v7.astronomy` | `moon` | `GET /v7/astronomy/moon` | `qwx.v7.astronomy.EndpointMoon` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `GET /v7/astronomy/solar-elevation-angle` | `qwx.v7.astronomy.EndpointAngle` |
| `qwx.v7.historical` | `weather` | `GET /v7/historical/weather` | `qwx.v7.historical.Endpoint` |
| `qwx.v7.indices` | `indices` | `GET /v7/indices/{days}d` | `qwx.v7.indices.Endpoint` |
| `qwx.v7.indices` | `indices_multi` | `GET /v7/indices/{days}d` | `qwx.v7.indices.Endpoint` |
| `qwx.v7.minutely` | `minutely` | `GET /v7/minutely/5m` | `qwx.v7.minutely.Endpoint` |
| `qwx.v7.ocean` | `tide` | `GET /v7/ocean/tide` | `qwx.v7.ocean.Endpoint` |
| `qwx.v7.storm` | `list` | `GET /v7/tropical/storm-list` | `qwx.v7.storm.EndpointList` |
| `qwx.v7.storm` | `forecast` | `GET /v7/tropical/storm-forecast` | `qwx.v7.storm.EndpointForecast` |
| `qwx.v7.storm` | `track` | `GET /v7/tropical/storm-track` | `qwx.v7.storm.EndpointTrack` |

Module layout:

| Module | Contents |
| --- | --- |
| `qwx` | Base clients, authentication, cache, `Location`, error hierarchy, shared request structures, `Refer`, `Metadata` |
| `qwx.v1` | Types shared by the new-generation endpoint families (`Metadata`, `Value`, `Options`) |
| `qwx.v1.weather` | New-generation weather `/weather/v1/*` |
| `qwx.v1.airquality` | New-generation air quality `/airquality/v1/*` |
| `qwx.v1.alert` | Weather alerts `/weatheralert/v1/*` |
| `qwx.v1.solarradiation` | New-generation solar radiation forecast `/solarradiation/v1/*` |
| `qwx.v7.ocean` | Legacy tide `/v7/ocean/tide` |
| `qwx.v7.indices` | Legacy life indices `/v7/indices/*` |
| `qwx.v7.minutely` | Legacy minutely precipitation `/v7/minutely/*` |
| `qwx.v7.storm` | Tropical cyclones `/v7/tropical/*` |
| `qwx.v7.astronomy` | Astronomy `/v7/astronomy/*` |
| `qwx.v7.historical` | Legacy historical weather `/v7/historical/weather` |
| `qwx.geo` | GeoAPI `/geo/v2/*` |
| `qwx.console` | Console `/finance/v1/*`, `/metrics/v1/stats` |
| `qwx.redis_cache` | Redis cache implementation (optional dependency `qwx[redis]`) |

One module = one upstream resource family. There are two exceptions: the four GeoAPI search endpoints share the `Place` type, and the two console endpoints live under one upstream documentation page and share one response skeleton.

---

## Caching and TTL

Without a `cache` argument every request goes to the upstream. The cache interface has two methods, so you can implement your own:

```python
from datetime import timedelta
from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, data: bytes, ttl: timedelta) -> None: ...
```

The built-in `qwx.MemoryCache` is only suitable for tests and single-instance scratch use (it has no background cleanup, so a long-running process only grows). Use a shared cache in production:

```python
from qwx.redis_cache import RedisCache

cache = RedisCache.from_url("redis://127.0.0.1:6379/0")
client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

Cached values are the raw JSON bytes, so keys and values are interchangeable with the Go version when both share one Redis.

TTL precedence: per-call override > `TTLPolicy` > the endpoint's default duration.

```python
from datetime import timedelta

import qwx
from qwx.v1.weather import EndpointCurrent

policy = qwx.TTLMap({EndpointCurrent: timedelta(seconds=30)})  # cache current weather for 30s
client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache, ttl_policy=policy)

with client.override_ttl(timedelta(0)):  # neither read nor write the cache
    weather.current(loc)
```

Key shape, the TTL table and writing your own cache: [docs/caching.md](docs/caching.md).

---

## Error handling

Exception hierarchy:

```
QwxError
├── InvalidConfigError      bad constructor arguments
├── InvalidLocationError    invalid location form
├── InvalidParameterError   parameter out of range
├── InvalidResponseError    response is not valid JSON
└── UpstreamError
    ├── UpstreamRejectedError     upstream 4xx
    ├── QuotaExceededError        upstream 429
    ├── UnauthorizedError         upstream 401 / 403
    └── UpstreamUnavailableError  upstream 5xx or network error
```

Classify by type, never by parsing the error string:

```python
import qwx

try:
    result = weather.current(loc)
except qwx.UnauthorizedError:
    ...  # check the credentials, see docs/auth.md
except qwx.QuotaExceededError:
    ...  # back off and retry
except qwx.InvalidParameterError:
    ...  # fix the request
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params, exc.body)
```

The first four are raised locally without hitting the upstream. On upstream 5xx, 429 and network errors the client retries with backoff on its own (up to 3 times). See [docs/errors.md](docs/errors.md).

---

## Logging

Nothing is logged unless you inject a logger. Any standard library `logging` logger works:

```python
import logging

import qwx

logger = logging.getLogger("qwx")
logger.setLevel(logging.INFO)

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logger)
```

Field names: `endpoint`, `method`, `path`, `status`, `duration_ms`, `cache_key`, `attempt`, `error`, `upstream_code`, `upstream_title`. See [docs/logging.md](docs/logging.md).

---

## Documentation

| Scenario | Document |
| --- | --- |
| Set up authentication, credentials, token expiry, 401/403 | [docs/auth.md](docs/auth.md) |
| Write calling code: parameter limits, location forms, return types, field units | [docs/contract.md](docs/contract.md) |
| Upstream behaviour contradicts the docs: 400, empty results, mismatched times | [docs/gotchas.md](docs/gotchas.md) |
| Decide on retries and degradation, read upstream error details | [docs/errors.md](docs/errors.md) |
| Plug in your own cache, tune TTL, debug cache mix-ups | [docs/caching.md](docs/caching.md) |
| Wire up logging, inspect request records | [docs/logging.md](docs/logging.md) |
| Run the tests, run the live smoke test | [docs/verification.md](docs/verification.md) |
| Look up every endpoint: path, location form, default TTL, cache key template | [docs/endpoints.md](docs/endpoints.md) |

Upstream documentation: <https://dev.qweather.com/docs/>

---

## License

MIT.

This package is not an official QWeather product. Using upstream data is subject to the [QWeather Developer EULA](https://www.qweather.com/terms/developers-eula/), and the attribution returned by the upstream must be kept when displaying weather data.
