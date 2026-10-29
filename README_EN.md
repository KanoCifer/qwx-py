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

qwx is a community-maintained Python SDK covering the core endpoint families in the upstream QWeather (和风天气) documentation, and it returns pydantic v2 models.

The Python version is semantically equivalent to the Go version ([KanoCifer/qwx](https://github.com/KanoCifer/qwx)): the same endpoint set, the same cache key bytes, the same endpoint constant values, the same error classification and the same TTL precedence. Cached values are stored as raw JSON bytes, so keys and values are interchangeable between the two versions when they share one Redis.

---

<details>
<summary><b>📖 Table of Contents</b></summary>

- [✨ Features](#features)
- [📦 Installation](#installation)
- [🚀 Quick start](#quick-start)
- [📖 Usage guide](#guide)
  - [🔑 Authentication](#authentication)
  - [⚙️ Client options](#client-options)
  - [📍 Location](#location)
  - [🌐 Language](#lang)
  - [🗄️ Caching & TTL](#caching)
  - [📝 Logging](#logging)
  - [🚨 Error handling](#errors)
  - [⏱️ Concurrency & timeout](#concurrency)
  - [🧪 Testing & verification](#verification)
- [🔌 Supported endpoints](#endpoints)
- [📋 Endpoint contract](#contract)
- [🔗 Official documentation](#upstream-docs)
- [⚖️ License](#license)

</details>

---

<a id="features"></a>
## ✨ Features

- **26 endpoints** across twelve resource families: weather, air quality, weather alerts, solar radiation, GeoAPI, console, astronomy, historical weather, life indices, minute-level precipitation, typhoons and tides.
- **Sync and async** on top of httpx. The endpoint method bodies are written once, the sync client returns models and the async client returns coroutines.
- **pydantic v2 models.** Fields newly added upstream are not dropped, unknown fields stay in `model_extra`.
- **Cache keys byte-for-byte identical to the Go version.** The literals are a published fact, changing them invalidates every cache entry already written.
- **The client validates first.** Out-of-range parameters and illegal location forms raise locally, without hitting the upstream.
- **Layered errors.** Classification is by exception type, never by parsing the error string.

---

<a id="installation"></a>
## 📦 Installation

```bash
pip install qwx
```

Requires Python 3.10 or newer. It depends on `httpx`, `pydantic` and `cryptography` (JWT signing).

Install the optional extra when you need the Redis cache:

```bash
pip install "qwx[redis]"
```

From source:

```bash
git clone https://github.com/KanoCifer/qwx-py.git
cd qwx-py
pip install -e ".[dev]"
```

---

<a id="quick-start"></a>
## 🚀 Quick start

Three steps: create the authentication, create the base client, create the service client for an endpoint family.

### Sync

```python
import qwx
from qwx.v1.weather import WeatherService

# 1. Authentication. JWTAuth uses the credentials assigned in the console,
#    API KEY uses qwx.APIKeyAuth.
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
<a id="guide"></a>
## 📖 Usage guide

<a id="authentication"></a>
### 🔑 Authentication

Pick one of the two. Sending both at once gets the request rejected upstream, and new projects should default to JWT.

| Method | Constructor | Request header | Use it for |
| --- | --- | --- | --- |
| `qwx.JWTAuth` | `qwx.JWTAuth(private_key_pem=..., key_id=..., project_id=..., developer_id=...)` | `Authorization: Bearer <JWT>` | New projects |
| `qwx.APIKeyAuth` | `qwx.APIKeyAuth(key)` | `X-QW-Api-Key: <key>` | Existing projects |

The vendor has already announced that API KEY authentication gets a daily request limit from January 1, 2027, and that SDK 5+ no longer supports it.

#### JWT

The console generates three credential values: Key ID (goes into the JWT header as `kid`), Project ID (payload `sub`) and Developer ID (payload `iss`). The private key is an Ed25519 PKCS#8 PEM, and the public key goes to the console.

Developer ID is required. `qwx.JWTAuth` raises `qwx.InvalidConfigError` when it is missing. Officially `iss` is the issuer, and the upstream uses it to check which account the credential belongs to; the value is on the console "Settings" page (10 alphanumeric characters starting with Q). The SDK only checks that it is non-empty, not its format.

```bash
openssl genpkey -algorithm ED25519 -out ed25519-private.pem
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
```

`qwx.JWTAuth` takes keyword arguments only, and raises `qwx.InvalidConfigError` when any of the four credentials is missing:

| Argument | Required | Notes |
| --- | --- | --- |
| `private_key_pem` | yes | Ed25519 PKCS#8 PEM text |
| `key_id` | yes | The console Key ID, goes into the JWT header as `kid` |
| `project_id` | yes | The console Project ID, goes into the payload as `sub` |
| `developer_id` | yes | The console Developer ID, goes into the payload as `iss` |
| `token_ttl` | no | Token lifetime, `timedelta(minutes=15)` by default |

How the token is signed, implemented in `src/qwx/auth.py`:

- The header carries `alg=EdDSA` and `kid=key_id`; the payload carries `iss=developer_id`, `sub=project_id`, `iat` and `exp=iat+token_ttl` (15 minutes by default).
- `iat` falls back 30 seconds to tolerate clock skew.
- The token is re-signed one minute before it expires, so callers never notice. Signing is locked and safe under concurrency.
- The PEM may contain literal `\n` escapes (a common way to pass it through an environment variable). Anything that is not PKCS#8 or not Ed25519 raises `qwx.InvalidConfigError`.


```python
auth = qwx.JWTAuth(
    private_key_pem=pem,
    key_id="your Key ID",
    project_id="your Project ID",
    developer_id="your Developer ID",
)
```

#### API KEY

```python
import qwx

auth = qwx.APIKeyAuth("your API KEY")
```

An empty key raises `qwx.InvalidConfigError`.

#### Dedicated API Host

The console "Settings" page assigns a dedicated API Host (something like `abcxyz.qweatherapi.com`), and it is a required argument: `qwx.Client(auth, host)`. The public domains `devapi.qweather.com`, `api.qweather.com` and `geoapi.qweather.com` have been retired one after another since 2026, so the SDK ships no default host.

A bare host gets `https://` prepended; a host that already carries a scheme is used as it is. The host is part of the identity: the upstream rejects a credential that does not match the host.

#### When authentication fails

401 and 403 both arrive as `qwx.UnauthorizedError`, see [Error handling](#errors). Check in this order:

1. `kid` matches the Key ID on the console.
2. `sub` is the Project ID, not the Developer ID.
3. `iss` is the Developer ID from the console "Settings" page, not the credential ID.
4. The private key and the public key uploaded to the console are one pair.
5. The credential, the Developer ID and the API Host belong to the same developer account.

<a id="client-options"></a>
### ⚙️ Client options

```python
client = qwx.Client(
    auth,
    "abcxyz.qweatherapi.com",
    timeout=30.0,  # per-request timeout in seconds
    cache=cache,  # cache implementation, None by default
    ttl_policy=policy,  # decides the cache duration per endpoint
    logger=logger,  # a logger from the standard library logging
    http_client=httpx.Client(...),  # custom httpx client
)
```

`api_host` has no default. The public domains are gone, so you have to use the dedicated host assigned on the console "Settings" page.

<a id="location"></a>
### 📍 Location

`Location` has three forms, and each endpoint accepts only a subset of them. The forms are not interchangeable, and the upstream rejects the wrong one.

| Form | Construction | Accepted by |
| --- | --- | --- |
| Coordinate pair | `qwx.Location(lat=39.92, lon=116.41)` or `qwx.parse_location("116.41,39.92")` | Every endpoint except console, typhoons and top cities |
| LocationID | `qwx.Location(id="101010100")` | GeoAPI; astronomy sun and moon; historical weather. Administrative divisions are 9 to 10 digits, POIs are digits with a letter suffix, tide stations are `P` plus digits |
| Place name | `qwx.Location(name="Hangzhou")` | `GeoService.lookup_city` and `GeoService.lookup_poi` only |

Coordinates keep two decimals inside the SDK, and `-0` is normalised to `0.00`. `qwx.parse_location` rejects empty strings, non-numbers, NaN/Inf and out-of-range coordinates, and raises `qwx.InvalidLocationError`.

One known edge: coordinates that are exactly `(0, 0)` make `has_coordinates()` return false, so the SDK treats them as "no coordinates".

**New-generation endpoints (`/weather/v1/*` and friends) take path parameters with latitude first**, while **v7 and GeoAPI take query parameters with longitude first**. Swap them and the upstream answers 400:

```python
qwx.Location(lat=39.92, lon=116.41)  # coordinate pair
qwx.Location(id="101010100")  # LocationID
qwx.Location(name="Hangzhou")  # place name, only GeoAPI accepts it
qwx.parse_location("116.41,39.92")  # parse from a string: longitude first
```

The table in [Supported endpoints](#endpoints) lists the accepted form per endpoint.

<a id="lang"></a>
### 🌐 Language

The upstream switches the response language through the `lang` query parameter. The language argument is a `qwx.Lang` everywhere (`qwx.v7.indices` and `qwx.v7.minutely` take it directly, the others carry it in `Options`).

- The codes come from the official "multi-language" page, and the SDK ships 31 of them: `qwx.Lang.ZH`, `qwx.Lang.ZH_HANT`, `qwx.Lang.EN` and so on. The full list is `qwx.LANGS`.
- Leaving it empty (`qwx.Lang.UNSPECIFIED`) sends no `lang`, and the upstream uses the official language of the country or region, falling back to English when there is none. When the official data does not support the requested language, the order is requested language, then official language, then English.
- Equivalent codes that the vendor publishes (for example `zh-hans` for Simplified Chinese) are found with `qwx.lookup_lang`, and what goes on the wire is still the preferred code `zh`.
- A malformed code returns `qwx.InvalidParameterError` without hitting the upstream.
- Endpoints that accept a language: new-generation weather (`current`/`hourly`/`daily`), air quality (`current`/`daily`/`hourly`/`station`), weather alerts (`current`), the four GeoAPI search endpoints, legacy life indices and minute-level precipitation, the moon (`moon`) and historical weather. The station data has its own documentation page (`/docs/api/air-quality/air-station/`) and states that it takes `lang`.
- Endpoints that do not: the solar radiation forecast, tides, the three typhoon endpoints, sun and moon times plus the solar elevation angle, and the two console endpoints. The upstream has no such parameter, passing it gets rejected, and the SDK does not expose it.
- The cache key carries the API code (`:lang=zh`), not the language name, which is the `api` field of `qwx.Lang`. A different language is a different payload, so the key has to change with it.

---
<a id="caching"></a>
### 🗄️ Caching & TTL

Without a `cache` argument every request goes to the upstream. The cache interface has two methods, so writing your own is easy:

```python
from datetime import timedelta
from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, data: bytes, ttl: timedelta) -> None: ...
```

- A hit returns `bytes`, a miss returns `None`.
- Read and write failures raise. The SDK swallows cache errors and falls back to a direct upstream call, so your implementation is free to raise.
- `ttl` is a relative duration.

The built-in `qwx.MemoryCache` lives in the process and is locked, but **it is not meant for production**. It has no background cleanup: an expired entry is removed only when a later `get` happens to hit it, entries that are never read again stay in the dict forever, and the memory of a long-running process only grows. It fits test doubles and single-instance scratch use. Production needs a shared cache such as Redis, and multi-instance deployments need one too, otherwise the hit rate is spread thin.

```python
import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=qwx.MemoryCache())
```

#### Redis implementation

The Redis adapter is an optional dependency, install the extra:

```bash
pip install "qwx[redis]"
```

```python
import qwx
from qwx.redis_cache import RedisCache

# Build it from a URL
cache = RedisCache.from_url("redis://127.0.0.1:6379/0")

# Or reuse an existing redis-py client, the pool, timeouts and TLS stay
# under your control
import redis

cache = RedisCache(redis.Redis(host="127.0.0.1", port=6379, db=0))

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

What to keep in mind:

- The constructor **does not connect to Redis**, the connection is established on the first read or write. A wrong address only shows up then.
- `from_url` needs redis-py installed and raises `ImportError` without it. `RedisCache(client)` accepts any object with `get` / `set` methods.
- The `ttl` of `set` is a relative duration, converted to the Redis `ex=` (whole seconds, rounded up, anything below one second counts as one second). A non-positive ttl raises `qwx.InvalidParameterError` and nothing is written, since weather data without an expiry stays stale forever.
- Cached values are the **raw JSON bytes**, so keys and values are interchangeable with the Go version when both share one Redis: entries written by Python are readable by the Go version and the other way round.
- Do not turn on `decode_responses=True`. The values are stored and read as bytes, and decoding breaks the interoperability with the Go version.
- Cache errors are swallowed as usual and the request falls back to the upstream, so a Redis outage does not take the API down.

#### Cache keys

The SDK generates the keys. They carry a generation prefix, the two generations do not share keys, and an old cache entry is never read by the new parser.

| Module | Method | Key |
| --- | --- | --- |
| `qwx.v1.weather` | `current` | `qwx:v1:current:<lat>,<lon>` + suffix |
| `qwx.v1.weather` | `hourly` | `qwx:v1:hourly:<lat>,<lon>:h<hours>` + suffix |
| `qwx.v1.weather` | `daily` | `qwx:v1:daily:<lat>,<lon>:d<days>` + suffix |
| `qwx.v1.airquality` | `current` | `qwx:aq:v1:current:<lat>,<lon>` + suffix |
| `qwx.v1.airquality` | `daily` | `qwx:aq:v1:daily:<lat>,<lon>` + suffix |
| `qwx.v1.airquality` | `hourly` | `qwx:aq:v1:hourly:<lat>,<lon>` + suffix |
| `qwx.v1.airquality` | `station` | `qwx:aq:v1:station:<station_id>` + suffix |
| `qwx.v1.alert` | `current` | `qwx:alert:v1:<lat>,<lon>` + suffix |
| `qwx.v1.solarradiation` | `forecast` | `qwx:solarradiation:v1:forecast:<lat>,<lon>:h<hours>` + suffix |
| `qwx.geo` | `lookup_city` | `qwx:geo:city:<location>` + suffix |
| `qwx.geo` | `lookup_poi` | `qwx:geo:poi:<typ>:<location>` + suffix |
| `qwx.geo` | `poi_range` | `qwx:geo:poirange:<typ>:<location>` + suffix (with the radius `:r=<radius>`) |
| `qwx.geo` | `top_cities` | `qwx:geo:topcity` + suffix |
| `qwx.console` | `finance` | `qwx:console:finance` |
| `qwx.console` | `stats` | `qwx:console:stats` + suffix |
| `qwx.v7.ocean` | `tide` | `qwx:tide:<station_id>:<date>` |
| `qwx.v7.indices` | `indices` | `qwx:indices:<location>:t<type>:d<days>` + suffix |
| `qwx.v7.indices` | `indices_multi` | `qwx:indices:<location>:t<types>:d<days>` + suffix |
| `qwx.v7.minutely` | `minutely` | `qwx:minutely:<location>` + suffix |
| `qwx.v7.storm` | `list` | `qwx:storm:list:<basin>:<year>` |
| `qwx.v7.storm` | `forecast` | `qwx:storm:forecast:<storm_id>` |
| `qwx.v7.storm` | `track` | `qwx:storm:track:<storm_id>` |
| `qwx.v7.astronomy` | `sun` | `qwx:astronomy:sun:<location>:<date>` |
| `qwx.v7.astronomy` | `moon` | `qwx:astronomy:moon:<location>:<date>` + suffix |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx:astronomy:angle:<location>:<date>:<time>:<tz>:<alt>` |
| `qwx.v7.historical` | `weather` | `qwx:historical:weather:<id>:<date>` + suffix |

The key literals are frozen in the released versions, changing them invalidates every cache entry already written. The prefix of `qwx.v7.ocean` is `qwx:tide:` and not `qwx:ocean:`; the mismatch with the module name is deliberate, do not "fix" it.

The suffix carries the query parameters that change the result: language `:lang=<lang>`, new-generation local time `:localTime=1`, count `:n=<number>`, radius `:r=<radius>`, administrative division `:adm=<adm>`, search range `:range=<range>`, city `:city=<city>`, interval `:interval=<n>`, tilt `:tilt=<n>`, azimuth `:azimuth=<n>`, extra `:extra=<extra>`, project `:project=<project>` and credential `:credential=<credential>`. Coordinates keep two decimals, and `-0` is normalised to `0.00`.

The language segment carries the API code (`:lang=zh`), not the language name. That is the `api` field of `qwx.Lang`.

The suffix order is fixed: language, local time, count, radius, administrative division, search range, city, interval, tilt, azimuth, extra, project, credential. New parameters are appended at the end, so callers that do not set them keep the exact key bytes of the release.

The key does not contain the API Host. Different hosts belong to different developer accounts, so do not share one cache instance across accounts.

##### How a key is assembled

The assembly lives in one place: `src/qwx/_cachekey.py`. An endpoint module never concatenates strings, it only declares two things, which family it belongs to and which parameters change the result.

| Family constant | Prefix root | Module |
| --- | --- | --- |
| `Family.WEATHER` | `qwx:v1:` | `qwx.v1.weather` |
| `Family.AIR_QUALITY` | `qwx:aq:v1:` | `qwx.v1.airquality` |
| `Family.ALERT` | `qwx:alert:v1:` | `qwx.v1.alert` |
| `Family.GEO` | `qwx:geo:` | `qwx.geo` |
| `Family.TIDE` | `qwx:tide:` | `qwx.v7.ocean` |
| `Family.INDICES` | `qwx:indices:` | `qwx.v7.indices` |
| `Family.MINUTELY` | `qwx:minutely:` | `qwx.v7.minutely` |
| `Family.SOLAR_RADIATION` | `qwx:solarradiation:v1:` | `qwx.v1.solarradiation` |
| `Family.STORM` | `qwx:storm:` | `qwx.v7.storm` |
| `Family.ASTRONOMY` | `qwx:astronomy:` | `qwx.v7.astronomy` |
| `Family.HISTORICAL` | `qwx:historical:` | `qwx.v7.historical` |
| `Family.CONSOLE` | `qwx:console:` | `qwx.console` |

The shape is fixed: family prefix + location segment + parameter segment.

- The location segment is concatenated in call order: endpoint name, coordinates, station ID, place ID, count segment (`:h24`).
- The coordinate segment is formatted by `_cachekey`: two decimals, `-0` normalised to `0.00`. The new generation puts latitude first (`path_coord`), the legacy generation and GeoAPI use `Location.query()` with longitude first.
- The parameter segment always comes last, in the order language, local time, count, radius, administrative division, search range, city, interval, tilt, azimuth, extra, project, credential.

The query parameters that change the result are declared with the same `qwx._cachekey.Params`, which produces the upstream query string and the key suffix at the same time. Adding a parameter means changing that one place, so a parameter cannot slip out of the key.

```python
# src/qwx/v1/weather/client.py
def _params(opts: Options) -> Params:
    return Params(lang=opts.lang.api, local_time=opts.local_time)
```

A radius of `None` means "this endpoint has no radius parameter". A radius of 0 goes into the key but not to the upstream, which then applies its own default.

Tilt and azimuth use `None` for "not sent" as well, and 0 is a legal value that is passed on whenever it is not `None`.

#### TTL

| Endpoint | Endpoint constant | Default TTL | Reason |
| --- | --- | --- | --- |
| Current weather | `qwx.v1.weather.EndpointCurrent` | 10 minutes | Upstream update rhythm |
| Hourly / daily forecast | `qwx.v1.weather.EndpointHourly` / `EndpointDaily` | 1 hour | Same |
| Current air quality | `qwx.v1.airquality.EndpointCurrent` | 30 minutes | The upstream updates hourly |
| Air quality forecast | `qwx.v1.airquality.EndpointDaily` / `EndpointHourly` | 1 hour | Same |
| Air quality station | `qwx.v1.airquality.EndpointStation` | 30 minutes | Same |
| Weather alerts | `qwx.v1.alert.Endpoint` | 5 minutes | The upstream updates every 5 minutes |
| Minute-level precipitation | `qwx.v7.minutely.Endpoint` | 5 minutes | The upstream updates every 5 minutes |
| Tides / life indices | `qwx.v7.ocean.Endpoint` / `qwx.v7.indices.Endpoint` | 1 hour | Update rhythm of the data |
| Solar radiation forecast | `qwx.v1.solarradiation.Endpoint` | 1 hour | The upstream refreshes the forecast every 15 minutes |
| Typhoon list | `qwx.v7.storm.EndpointList` | 24 hours | The list hardly changes within a day |
| Typhoon forecast / track | `qwx.v7.storm.EndpointForecast` / `EndpointTrack` | 1 hour | The upstream updates every few hours |
| Astronomy | `qwx.v7.astronomy.EndpointSun` and two more | 24 hours | The data is fixed per date |
| Historical weather | `qwx.v7.historical.Endpoint` | 24 hours | The data is fixed per date and does not change afterwards |
| GeoAPI | `qwx.geo.EndpointCity` and three more | 24 hours | Geographic data hardly ever changes |
| Console | `qwx.console.EndpointFinance` / `EndpointStats` | 1 hour | The upstream data stops at the previous hour or earlier |

##### Custom TTL

The endpoint module decides the default duration. Pass a `ttl_policy` to change it:

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
            AQCurrent: timedelta(0),  # this endpoint is not cached
        }
    ),
)
```

`qwx.TTLMap` is the form most projects use: the keys are endpoint constants, the values are durations. A key that is absent keeps the default duration of the endpoint, and a value of 0 means the endpoint is not cached.

Use `qwx.TTLPolicyFunc` when the duration has to follow the time of day or the load:

```python
policy = qwx.TTLPolicyFunc(
    lambda endpoint, default: timedelta(seconds=10) if endpoint == EndpointCurrent else default
)
```

`default` is the duration built into the endpoint module, return it unchanged when the policy has no opinion. The policy is evaluated on every request, so the implementation has to be safe under concurrency.

To bypass the cache for a single call, use the context override. No endpoint signature changes:

```python
with client.override_ttl(timedelta(0)):  # neither read nor write the cache this time
    weather.current(loc)
```

The override wins over the policy and over the default duration of the endpoint. It is implemented with `contextvars`, it works for the sync and the async client, and async tasks do not leak into each other.

The duration is resolved in this order: per-call override, then `TTLPolicy`, then the duration built into the endpoint module.

A request without an endpoint (external code that builds a `qwx.Request` and leaves `endpoint` empty) does not take part in policy matching. The policy is never called for it, and only `Request.ttl` decides the duration.

##### TTL and cache keys

Changing the TTL does not change the cache key. Entries that are already written expire according to the TTL they were written with, and shortening the policy does not make them expire earlier. Swap the cache instance or delete the keys by hand to take effect at once.

---
<a id="logging"></a>
### 📝 Logging

The SDK uses the standard library `logging`. It ships no logger of its own and adds no third-party dependency.

#### Turning it on

Nothing is logged unless you inject a logger:

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

`logger=None` is the same as injecting nothing: the SDK attaches a `NullHandler` and turns `propagate` off, so the output is dropped.

The handler decides the level, the SDK does not filter any more. A handler that lets DEBUG through also receives the details such as cache hits.

#### What gets logged

| Level | Message | When |
| --- | --- | --- |
| DEBUG | `cache hit` | The cache answered, the upstream was not called |
| DEBUG | `cache miss` | The cache missed, the request went to the upstream |
| WARNING | `cache read failed` | The cache read failed, the request fell back to the upstream |
| WARNING | `cache write failed` | The cache write failed, the response was already in hand |
| INFO | `upstream request` | The upstream answered 2xx |
| WARNING | `upstream rejected` | The upstream answered 4xx, the request itself is invalid |
| ERROR | `upstream rejected` | The upstream answered 5xx, the upstream is broken |
| WARNING | `upstream retry` | A 5xx, a 429 or a network error triggered a retry |
| ERROR | `decode response failed` | The response is not valid JSON, or its shape does not match the model |
| ERROR | `sign request failed` | Writing the authentication failed |

One request produces at most one `upstream request` or `upstream rejected` record, plus the occasional retry and cache records. A request served from the cache has no upstream record, only `cache hit`.

#### Fields

The field names are constants in `src/qwx/logger.py`, so your own handler can filter on them.

| Field | Meaning |
| --- | --- |
| `endpoint` | Endpoint identifier such as `weather/v1/current`. A request without an endpoint has no such field |
| `method` | HTTP method, an empty value is treated as GET |
| `path` | Request path without the query string |
| `status` | HTTP status code |
| `duration_ms` | Duration in milliseconds |
| `cache_key` | Cache key |
| `attempt` | Which attempt this is, starting at 1 |
| `error` | Error text |
| `upstream_code` | Business status code from the upstream |
| `upstream_title` | One-line reason from the upstream |

The fields arrive through the standard `LogRecord` `extra`, and you read them by name:

```python
class FieldFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # The fields are optional, a request without an endpoint has no
        # endpoint field, so read it with getattr.
        return getattr(record, "endpoint", "") != "weather/v1/current"
```

#### What never gets logged

- **Credentials**: JWT and API KEY both travel in headers, and headers are not logged.
- **Response bodies**: only the status code and the reason from the upstream are logged. The body lives on the error object `qwx.UpstreamError.body`, truncated to 2KB.
- **Query parameters**: they are not logged on purpose. Transport level error texts embed the full URL, so the query string is stripped before the record is written and only the path and the reason remain (`qwx.logger.sanitize_error_text`).

Paths and cache keys can carry the coordinates of the request (the new generation uses `latitude,longitude` in the path), so how much of the log you expose is your call.

The SDK does not mask coordinates, they are the subject of the call and you need them to debug a hit or a location. Wrap your own handler if you want them redacted.

#### Custom redaction

The SDK has no redaction switch. The logger is the handler you inject, so wrap it before injecting:

```python
import logging


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Rewrite the path / cache_key of the record, then let it through.
        if hasattr(record, "path"):
            record.path = "<redacted>"
        if hasattr(record, "cache_key"):
            record.cache_key = "<redacted>"
        return True


logger = logging.getLogger("qwx")
logger.addFilter(RedactFilter())
client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logger)
```

#### Examples

JSON on stdout:

```python
import logging
import sys

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s %(endpoint)s"))

logger = logging.getLogger("qwx")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logger)
```

To see only failures and warnings, move the level to WARNING:

```python
logger.setLevel(logging.WARNING)
```

#### Cost

Without an injected logger the SDK sits on a `NullHandler`: no formatting, no field construction, and the only overhead per request is one `isEnabledFor` call. With logging on, a request to the upstream writes one INFO record and a cache hit writes one DEBUG record. The fields are built as a dict, not as a concatenated string. Making the handler safe under concurrency is up to you.

<a id="errors"></a>
### 🚨 Error handling

Every SDK exception inherits `qwx.QwxError`. Classify with `isinstance` / `except`, never by parsing the error string.

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

| Exception | Raised when | What to do |
| --- | --- | --- |
| `InvalidConfigError` | The constructor arguments are wrong: missing authentication, empty private key, empty API KEY, empty API Host | Fix the code, do not retry |
| `InvalidLocationError` | The location form is invalid or the upstream does not accept it: empty string, non-numeric, NaN/Inf, out-of-range coordinates, no coordinates | Fix the request, do not retry |
| `InvalidParameterError` | A parameter is out of range: a value outside `hours`, `days`, `type`, `radius`, a malformed date, a malformed language code | Fix the request, do not retry |
| `InvalidResponseError` | The upstream answered with something that is not valid JSON, or with a shape that does not match the model | Look at `UpstreamError.body`, a retry may help |
| `UpstreamRejectedError` | Upstream 4xx | Fix the request, retrying is pointless |
| `QuotaExceededError` | Upstream 429 | Back off and retry |
| `UnauthorizedError` | Upstream 401/403 | Check the credentials, see [Authentication](#authentication) |
| `UpstreamUnavailableError` | Upstream 5xx or a network error, including a timeout | Retry with exponential backoff |

The first four are raised locally and never reach the upstream.

```python
import qwx

try:
    result = weather.current(loc)
except qwx.UnauthorizedError:
    ...  # check the credentials
except qwx.QuotaExceededError:
    ...  # back off and retry
except qwx.InvalidParameterError:
    ...  # fix the request
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params)
except qwx.QwxError:
    ...  # the remaining SDK exceptions
```

#### Reading the upstream details

`UpstreamError` carries the details the upstream returned:

```python
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params, exc.body)
```

The fields are `status_code` (HTTP status code), `code` (business code), `title` (one-line reason), `invalid_params` (the offending parameter names, new generation only) and `body` (the raw response body, truncated to 2KB).

Both generations of error body are parsed:

- New generation: `{"error":{"status":400,"title":"Invalid Parameters","invalidParams":["longitude","latitude"]}}`
- Legacy generation: `{"code":"400","error":"Invalid Parameters"}`

A network error without a response is also an `UpstreamUnavailableError`, and its `status_code` is 0.

#### When to retry

The client already retries with backoff: on an upstream 5xx, a 429 or a network error it tries up to 3 more times (`qwx.client.MAX_RETRY`), waits at most `qwx.client.MAX_RETRY_DELAY` (30 seconds) per attempt, and follows the upstream when it sends a larger `Retry-After`. A 4xx is never retried.

| Symptom | Class | Action |
| --- | --- | --- |
| 429 | `QuotaExceededError` | The client already backed off; if it still fails, back off against the quota and add jitter |
| 5xx / connection failure / timeout | `UpstreamUnavailableError` | The client already backed off exponentially; if it still fails, retry in the business layer |
| 400 / 404 | `UpstreamRejectedError` | Fix the request, a retry only burns quota |
| 401 / 403 | `UnauthorizedError` | Check the credentials |
| JSON decoding failed | `InvalidResponseError` | Look at the body to tell a gateway error page from an upstream error |

A cache failure never turns into a business error: when `get` or `set` raises, the SDK calls the upstream directly. The logic is in `do` in `src/qwx/client.py`.

<a id="concurrency"></a>
### ⏱️ Concurrency & timeout

`Client` and `AsyncClient` are stateless and can be shared across concurrent tasks. The default per-request timeout is 30 seconds. Inject your own httpx client when you need a proxy, a connection pool or custom certificates:

```python
import httpx

import qwx

http = httpx.Client(
    timeout=httpx.Timeout(10.0, connect=3.0), limits=httpx.Limits(max_connections=50)
)
client = qwx.Client(auth, "abcxyz.qweatherapi.com", http_client=http)
```

The async version works the same way, inject an `httpx.AsyncClient`.

---
<a id="verification"></a>
### 🧪 Testing & verification

#### Install the dependencies

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

Add the Redis extra to run the tests of the Redis adapter:

```bash
.venv/bin/pip install -e ".[dev,redis]"
```

With uv:

```bash
uv sync --all-extras
uv run pytest -q
```

#### Gate commands

```bash
.venv/bin/ruff format --check .   # must print nothing
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
```

The `ruff` configuration lives in `pyproject.toml`: `line-length = 100`, `target-version = "py310"`, with the rule set `E F I UP B SIM RUF N`.

`mypy` runs in strict mode and only checks `src/qwx` (`files = ["src/qwx"]`), with Python 3.10 as the target version.

#### Test tiers

Run the smallest set that covers your change.

| Tier | Change | What to run |
| --- | --- | --- |
| 1 | A single endpoint family or file | The matching `tests/test_*.py` plus `ruff format --check .` and `mypy` |
| 2 | Across modules (`client.py`, `auth.py`, `cache.py`, `location.py`) | The tests of the involved modules and of their direct dependencies |
| 3 | A core rework (cache keys, location parsing, request execution) | The full `.venv/bin/python -m pytest tests/ -q` |

#### Live smoke test

The four files under `live/` carry the `live` marker and do not take part in `pytest tests/` (the test path only contains `tests/`). They need real credentials and skip entirely when one is missing, so CI does not fail over missing credentials.

| File | Coverage |
| --- | --- |
| `live/conftest.py` | Shared fixtures: reading the environment, building the client, the skip marker |
| `live/test_live_v1.py` | New generation: weather, air quality, alerts, solar radiation |
| `live/test_live_v7.py` | Legacy generation: astronomy, historical weather, life indices, minute-level precipitation, typhoons, tides |
| `live/test_live_geo.py` | GeoAPI: city search, POI search, POI range, top cities |
| `live/test_live_console.py` | Console: finance summary, request statistics |

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_API_KEY=YOUR_API_KEY \
.venv/bin/python -m pytest live/ -q -m live
```

Or with JWT, where the private key is PEM content and may contain literal `\n` escapes:

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)" \
QWX_KEY_ID=YOUR_KEY_ID \
QWX_PROJECT_ID=YOUR_PROJECT_ID \
QWX_DEVELOPER_ID=YOUR_DEVELOPER_ID \
.venv/bin/python -m pytest live/ -q -m live
```

The environment variables:

| Variable | Meaning |
| --- | --- |
| `QWX_API_HOST` | The dedicated API Host from the console, required |
| `QWX_API_KEY` | API KEY, either this or JWT |
| `QWX_JWT_PRIVATE_KEY` | Ed25519 private key PEM content |
| `QWX_KEY_ID` | Key ID |
| `QWX_PROJECT_ID` | Project ID |
| `QWX_DEVELOPER_ID` | Developer ID |

With a complete set of JWT credentials the test uses JWT, otherwise it falls back to the API KEY. With neither configured the whole module skips.

Run it after changing upstream behaviour, endpoint fields or request parameters, to check the real responses.

#### Done means

- `ruff format --check .` prints nothing, `ruff check .` reports no warning, `mypy` passes.
- The tests of the changed modules pass, error branches included.
- When endpoint behaviour changes, the matching paragraphs in [Endpoint contract](#contract), [Supported endpoints](#endpoints) and [Caching & TTL](#caching) are updated in the same change.
- `.venv/bin/python -m pytest tests/ -q` is green.

---

<a id="endpoints"></a>
## 🔌 Supported endpoints

26 endpoints across twelve resource families. The location form, the default TTL and the cache key prefix are the three things to check before you call.

| Package | Method | Endpoint constant | Upstream path | Location form | Default TTL | Cache key prefix |
| --- | --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `qwx.console.EndpointFinance` | `/finance/v1/summary` | none | 1 hour | `qwx:console:` |
| `qwx.console` | `stats` | `qwx.console.EndpointStats` | `/metrics/v1/stats` | none | 1 hour | `qwx:console:` |
| `qwx.geo` | `lookup_city` | `qwx.geo.EndpointCity` | `/geo/v2/city/lookup` | coordinates / LocationID / place name | 24 hours | `qwx:geo:` |
| `qwx.geo` | `lookup_poi` | `qwx.geo.EndpointPOI` | `/geo/v2/poi/lookup` | coordinates / LocationID / place name | 24 hours | `qwx:geo:` |
| `qwx.geo` | `poi_range` | `qwx.geo.EndpointPOIRange` | `/geo/v2/poi/range` | coordinates | 24 hours | `qwx:geo:` |
| `qwx.geo` | `top_cities` | `qwx.geo.EndpointTopCities` | `/geo/v2/city/top` | none | 24 hours | `qwx:geo:` |
| `qwx.v1.airquality` | `current` | `qwx.v1.airquality.EndpointCurrent` | `/airquality/v1/current/{lat}/{lon}` | coordinates | 30 minutes | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `daily` | `qwx.v1.airquality.EndpointDaily` | `/airquality/v1/daily/{lat}/{lon}` | coordinates | 1 hour | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `hourly` | `qwx.v1.airquality.EndpointHourly` | `/airquality/v1/hourly/{lat}/{lon}` | coordinates | 1 hour | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `station` | `qwx.v1.airquality.EndpointStation` | `/airquality/v1/stations/{stationID}` | station ID | 30 minutes | `qwx:aq:v1:` |
| `qwx.v1.alert` | `current` | `qwx.v1.alert.Endpoint` | `/weatheralert/v1/current/{lat}/{lon}` | coordinates | 5 minutes | `qwx:alert:v1:` |
| `qwx.v1.solarradiation` | `forecast` | `qwx.v1.solarradiation.Endpoint` | `/solarradiation/v1/forecast/{lat}/{lon}` | coordinates | 1 hour | `qwx:solarradiation:v1:` |
| `qwx.v1.weather` | `current` | `qwx.v1.weather.EndpointCurrent` | `/weather/v1/current/{lat}/{lon}` | coordinates | 10 minutes | `qwx:v1:` |
| `qwx.v1.weather` | `hourly` | `qwx.v1.weather.EndpointHourly` | `/weather/v1/hourly/{lat}/{lon}` | coordinates | 1 hour | `qwx:v1:` |
| `qwx.v1.weather` | `daily` | `qwx.v1.weather.EndpointDaily` | `/weather/v1/daily/{lat}/{lon}` | coordinates | 1 hour | `qwx:v1:` |
| `qwx.v7.astronomy` | `sun` | `qwx.v7.astronomy.EndpointSun` | `/v7/astronomy/sun` | coordinates / LocationID | 24 hours | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `moon` | `qwx.v7.astronomy.EndpointMoon` | `/v7/astronomy/moon` | coordinates / LocationID | 24 hours | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx.v7.astronomy.EndpointAngle` | `/v7/astronomy/solar-elevation-angle` | coordinates | 24 hours | `qwx:astronomy:` |
| `qwx.v7.historical` | `weather` | `qwx.v7.historical.Endpoint` | `/v7/historical/weather` | LocationID | 24 hours | `qwx:historical:` |
| `qwx.v7.indices` | `indices` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | coordinates | 1 hour | `qwx:indices:` |
| `qwx.v7.indices` | `indices_multi` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | coordinates | 1 hour | `qwx:indices:` |
| `qwx.v7.minutely` | `minutely` | `qwx.v7.minutely.Endpoint` | `/v7/minutely/5m` | coordinates | 5 minutes | `qwx:minutely:` |
| `qwx.v7.ocean` | `tide` | `qwx.v7.ocean.Endpoint` | `/v7/ocean/tide` | station ID | 1 hour | `qwx:tide:` |
| `qwx.v7.storm` | `list` | `qwx.v7.storm.EndpointList` | `/v7/tropical/storm-list` | none | 24 hours | `qwx:storm:` |
| `qwx.v7.storm` | `forecast` | `qwx.v7.storm.EndpointForecast` | `/v7/tropical/storm-forecast` | none | 1 hour | `qwx:storm:` |
| `qwx.v7.storm` | `track` | `qwx.v7.storm.EndpointTrack` | `/v7/tropical/storm-track` | none | 1 hour | `qwx:storm:` |

The full key templates are in [Caching & TTL](#caching), together with the rules for which parameters enter the key.

The **values** of the endpoint constants do not change after publication: `qwx.TTLPolicy` matches by value, so a new value silently breaks the TTL configuration of the users.

### Module layout

| Module | Contents |
| --- | --- |
| `qwx` | Base clients, authentication, cache, `Location`, error hierarchy, request structures shared by both generations, `Refer`, `Metadata` |
| `qwx.v1` | Base types shared across the new-generation endpoint families (`Metadata`, `Value`, `Options`) |
| `qwx.v1.weather` | New-generation weather `/weather/v1/*` |
| `qwx.v1.airquality` | New-generation air quality `/airquality/v1/*` |
| `qwx.v1.alert` | Weather alerts `/weatheralert/v1/*` |
| `qwx.v1.solarradiation` | New-generation solar radiation forecast `/solarradiation/v1/*` |
| `qwx.v7.ocean` | Legacy tides `/v7/ocean/tide` |
| `qwx.v7.indices` | Legacy life indices `/v7/indices/*` |
| `qwx.v7.minutely` | Legacy minute-level precipitation `/v7/minutely/*` |
| `qwx.v7.storm` | Typhoons `/v7/tropical/*` |
| `qwx.v7.astronomy` | Astronomy `/v7/astronomy/*` |
| `qwx.v7.historical` | Legacy historical weather `/v7/historical/weather` |
| `qwx.geo` | GeoAPI `/geo/v2/*` |
| `qwx.console` | Console `/finance/v1/*`, `/metrics/v1/stats` |
| `qwx.redis_cache` | Redis cache implementation (optional dependency `qwx[redis]`) |

One module is one upstream resource family. There are two exceptions: the four GeoAPI search endpoints share the `Place` type, and the two console endpoints live under one upstream documentation page and share one response skeleton.

---
<a id="contract"></a>
## 📋 Endpoint contract

Look here before writing the call: what an endpoint takes, what it returns and where the edges are.

### Service clients

The endpoints live in modules per upstream generation, and the methods hang off the service client of their module:

| Module | Service client (sync / async) | Covers |
| --- | --- | --- |
| `qwx.v1` | none | Base types shared across the new-generation endpoint families (`Metadata`, `Value`, `Options`) |
| `qwx.v1.weather` | `WeatherService` / `AsyncWeatherService` | New-generation weather |
| `qwx.v1.airquality` | `AirQualityService` / `AsyncAirQualityService` | New-generation air quality |
| `qwx.v1.alert` | `AlertService` / `AsyncAlertService` | Weather alerts |
| `qwx.v1.solarradiation` | `SolarRadiationService` / `AsyncSolarRadiationService` | New-generation solar radiation forecast |
| `qwx.v7.indices` | `IndicesService` / `AsyncIndicesService` | Legacy life indices |
| `qwx.v7.minutely` | `MinutelyService` / `AsyncMinutelyService` | Legacy minute-level precipitation |
| `qwx.v7.storm` | `StormService` / `AsyncStormService` | Typhoons |
| `qwx.v7.astronomy` | `AstronomyService` / `AsyncAstronomyService` | Astronomy |
| `qwx.v7.historical` | `HistoricalService` / `AsyncHistoricalService` | Legacy historical weather |
| `qwx.v7.ocean` | `OceanService` / `AsyncOceanService` | Legacy tides |
| `qwx.geo` | `GeoService` / `AsyncGeoService` | GeoAPI |
| `qwx.console` | `ConsoleService` / `AsyncConsoleService` | Console (finance summary, request statistics) |

`qwx.geo` is the only exception: its four search endpoints share one place type, and splitting them would leave that type without a home.

A service client is built on the base client, holds no state and can be shared:

```python
import qwx
from qwx.v1.weather import WeatherService

auth = qwx.APIKeyAuth("your API KEY")
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    weather = WeatherService(client)
    current = weather.current(qwx.Location(lat=39.92, lon=116.41))
```

The async version is symmetric, the methods become coroutines:

```python
import qwx
from qwx.v1.weather import AsyncWeatherService

async with qwx.AsyncClient(auth, "abcxyz.qweatherapi.com") as client:
    weather = AsyncWeatherService(client)
    current = await weather.current(qwx.Location(lat=39.92, lon=116.41))
```

Every module shares the same base client `qwx.Client(auth, api_host, ...)`. `api_host` is the dedicated API Host from the console "Settings" page and it is required. The path prefix depends on the host, and GeoAPI is `/geo/v2/*` under a dedicated host.

The endpoint constants are the keys of the cache duration, see [Custom TTL](#caching).

### New generation (coordinates only)

| Module | Method | Upstream path | Arguments | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.v1.weather` | `current` | `GET /weather/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `CurrentWeather` | `EndpointCurrent` |
| `qwx.v1.weather` | `hourly` | `GET /weather/v1/hourly/{lat}/{lon}` | `hours` 1..240; `opts` | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.weather` | `daily` | `GET /weather/v1/daily/{lat}/{lon}` | `days` 1..10; `opts` | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `current` | `GET /airquality/v1/current/{lat}/{lon}` | `opts: Options(lang)` | `Current` | `EndpointCurrent` |
| `qwx.v1.airquality` | `daily` | `GET /airquality/v1/daily/{lat}/{lon}` | same | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `hourly` | `GET /airquality/v1/hourly/{lat}/{lon}` | same | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.airquality` | `station` | `GET /airquality/v1/stations/{location_id}` | station ID such as `P51762`, not empty | `StationData` | `EndpointStation` |
| `qwx.v1.alert` | `current` | `GET /weatheralert/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `Result` | `Endpoint` |
| `qwx.v1.solarradiation` | `forecast` | `GET /solarradiation/v1/forecast/{lat}/{lon}` | `hours` 1..72; `opts: Options(local_time, interval, tilt, azimuth, extra)` | `Result` | `Endpoint` |

Out-of-range arguments are caught in the client: `hours` and `days` raise `qwx.InvalidParameterError`, a missing coordinate raises `qwx.InvalidLocationError`, and neither reaches the upstream.

The values of the solar radiation `Options`: `interval` is 15, 30 or 60 (0 means not sent, the upstream defaults to 60); `tilt` is 0 to 90; `azimuth` is 0 to 359; `extra` accepts `"weather"` and `"poa"` only, several values are comma separated, and duplicates or unknown values are rejected. When `extra` contains `"poa"` the upstream requires both `tilt` and `azimuth`.

### GeoAPI (coordinates / LocationID / place name)

| Module | Method | Upstream path | Arguments | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.geo` | `lookup_city` | `GET /geo/v2/city/lookup` | `loc` in all three forms; `opts: Options(lang, number, adm, range)` | `CityResult` | `EndpointCity` |
| `qwx.geo` | `lookup_poi` | `GET /geo/v2/poi/lookup` | `loc` in all three forms; `typ` ∈ `POIType.SCENIC` / `POIType.CSTA` / `POIType.TSTA`; `opts: Options(lang, number, city)` | `POIResult` | `EndpointPOI` |
| `qwx.geo` | `poi_range` | `GET /geo/v2/poi/range` | `loc` coordinates only; `typ`; `opts: POIRangeOptions(lang, number, radius)` | `RangeResult` | `EndpointPOIRange` |
| `qwx.geo` | `top_cities` | `GET /geo/v2/city/top` | `opts: Options(lang, number, range)` | `TopCityResult` | `EndpointTopCities` |

A `number` of 0 lets the upstream decide (10), and a `radius` of 0 falls back to the default (5).

`adm`, `range` and `city` are optional arguments on `Options`, and each endpoint reports only the ones it knows: `adm` and `range` are for the city search, `city` is for the POI search, and `top_cities` knows `range` too. `adm` takes the LocationID of the parent administrative division (such as `101010100`), `range` takes an ISO 3166 country code (such as `cn` or `world`), and `city` takes a city name or a LocationID. All three change the result, so all three enter the cache key.

`typ` is required and its value set is closed. A type outside the set raises `qwx.InvalidParameterError` without hitting the upstream.

### Legacy generation v7

The legacy endpoints still have no counterpart in the new generation. The legacy warning endpoint `/v7/warning/now` is gone, use `qwx.v1.alert` instead.

| Module | Method | Upstream path | Arguments | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.v7.ocean` | `tide` | `GET /v7/ocean/tide` | `station_id` tide station ID (`P2352`); `date` is the local `YYYYMMDD` of the station | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices` | `GET /v7/indices/{days}d` | `loc` coordinates only; `typ` 0..16; `days` ∈ {1, 3}; `lang` | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices_multi` | `GET /v7/indices/{days}d` | same, `typ` takes several values (`[3, 5]`) | `Result` | `Endpoint` |
| `qwx.v7.minutely` | `minutely` | `GET /v7/minutely/5m` | `loc` coordinates only; `lang` | `Result` | `Endpoint` |
| `qwx.v7.storm` | `list` | `GET /v7/tropical/storm-list` | `basin` is `NP` only; `year` a positive integer | `ListResult` | `EndpointList` |
| `qwx.v7.storm` | `forecast` | `GET /v7/tropical/storm-forecast` | `storm_id` not empty | `ForecastResult` | `EndpointForecast` |
| `qwx.v7.storm` | `track` | `GET /v7/tropical/storm-track` | `storm_id` not empty | `TrackResult` | `EndpointTrack` |
| `qwx.v7.astronomy` | `sun` | `GET /v7/astronomy/sun` | `loc` coordinates or LocationID; `date` as `YYYYMMDD` | `SunResult` | `EndpointSun` |
| `qwx.v7.astronomy` | `moon` | `GET /v7/astronomy/moon` | same; `opts: Options(lang)` | `MoonResult` | `EndpointMoon` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `GET /v7/astronomy/solar-elevation-angle` | `loc` coordinates only; `date`, `time_str` (`HHmm`), `tz` (such as `0800`), `alt` (altitude in metres, not negative) | `AngleResult` | `EndpointAngle` |
| `qwx.v7.historical` | `weather` | `GET /v7/historical/weather` | `loc` LocationID only; `date` as `YYYYMMDD`; `opts: Options(lang)` | `Result` | `Endpoint` |

The `typ` of `qwx.v7.indices` is 0 to 16, where 0 means all of them (`TYPE_ALL`), and `indices_multi` cannot carry 0 together with other types. `days` supports 1 and 3 only.

`tide`, `indices` and `minutely` still exist only in v7: every "new generation" variant of those paths (`/weather/v1/indices/*`, `/v1/indices/*`, `/ocean/v1/tide/*`) answers 404 in practice.

The results of the legacy endpoints carry a top level `refer` object with the data sources and the license, shaped like the GeoAPI one, read it from `Result.refer`. The new generation has no `refer`, the same information sits in `Metadata.attributions`.

### Console

The console API reports the financial summary and the request volume of your own account, not weather data. A credential has no access by default: the account owner has to enable the console permission under "Project management - Credentials - Console permission" in the console, otherwise the upstream answers 403 (`qwx.UnauthorizedError`).

| Module | Method | Upstream path | Arguments | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `GET /finance/v1/summary` | none | `FinanceResult` | `EndpointFinance` |
| `qwx.console` | `stats` | `GET /metrics/v1/stats` | `opts: StatsOptions(project, credential)` | `StatsResult` | `EndpointStats` |

`project` and `credential` are mutually exclusive, and setting both is blocked in the client (`qwx.InvalidParameterError`) without hitting the upstream. Leaving both empty reports all projects and credentials of the account. A deleted project or credential cannot be queried on its own, but its requests still count towards the summary.

The data stops at the previous hour or earlier, which can be an hour or more behind what the console page shows. The `as_of` field of the response is the reference.

Field shapes:

- A negative `balance` means an outstanding amount, `currency` is the currency code (`CNY`, `USD`).
- The three numbers of `accrued_charges` are the accrued charges for the previous day, for the current month and since the last invoice.
- `pending_bills[].type`, `pending_bills[].status` and the `status` of the resource plans are enums. The vendor adds values, so the SDK passes them through instead of enumerating them.
- `available_resource_plans[].requests` comes as a string in the upstream samples (`"1000000"`) while the official field table says a number. The SDK takes `int | float | str` and parses both.
- `as_of`, `pending_bills[].date`, `due_date` and `effective_time` are UTC time strings, passed through as they are.
- The `hours` of each item in `success` and `errors` is the hourly request volume of the last 24 hours. The upstream may return fewer than 24 entries, do not assume the length.

### Upstream endpoints that qwx does not cover

The upstream has these endpoints and this library does not implement them. Two groups: the ones with a retirement date are gone for good, the ones still alive can be added on demand.

| Upstream path | Status | Use instead |
| --- | --- | --- |
| `/v7/warning/now` | retired 2026-09-01 | `qwx.v1.alert` |
| `/v7/air/now` | retired 2026-06-01 | `qwx.v1.airquality` |
| `/v7/air/5d` | retired 2026-06-01 | `qwx.v1.airquality` |
| `/v7/solar-radiation/{hours}` | retired 2026-12-31 | `qwx.v1.solarradiation` |
| `/v7/grid-weather/now` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/grid-weather/{days}` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/grid-weather/{hours}` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/weather/now` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/weather/{days}` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/weather/{hours}` | retired 2027-02-01 | `qwx.v1.weather` |
| `/v7/historical/air` | deprecated | no replacement |

The `/v7/minutely/5m`, `/v7/indices/{days}`, `/v7/ocean/tide` and `/v7/historical/weather` endpoints this library supports are not on the retirement list and keep working.

### Field semantics

The same concept has a different shape in the two generations, so check which generation you are in before reading a value.

| Concept | New generation | v7 |
| --- | --- | --- |
| Value and unit | separated: `Value(value, unit)` | joined into one string |
| Precipitation probability | 0 to 1, present in the hourly and daily forecast, absent from the current weather (`None` tells "not reported" from 0) | no such field |
| Precipitation intensity | `Precipitation.intensity` can be `None`: the current weather and the hourly forecast have it, the daily forecast does not (`None` tells "not reported" from 0) | no such field |
| Tide height | none | `Tide.height` stays a string and keeps the precision of the upstream |
| Minute-level precipitation | none | `Minutely.precip` stays a string: an empty string means "no data", `"0.00"` means "it really did not rain" |
| Data sources and license | `Metadata.attributions` | `Refer.sources` / `Refer.license`, same shape |
| Relative humidity | the solar radiation forecast uses a percentage (0 to 100) | no such field |

Rules that hold everywhere, do not assume otherwise:

- Optional fields are `None`, so a missing value and a zero stay apart: `Metadata.zero_result`, `Astro`, `Alert.urgency` / `severity` / `certainty`, `Precipitation.probability`, `Precipitation.intensity`.
- The gust key depends on the endpoint: the current weather and the hourly forecast use `wind_gust`, the day and night parts of the daily forecast use `wind_gust_max` (`DayNight.wind_gust_max`).
- Do not assume the length of a list: the upstream may return fewer `HourlyForecast.hours` and `DailyForecast.days` entries than you asked for.
- Enums grow, the SDK passes them through instead of enumerating them: `Condition.code`, `Alert.event_type.code`, `DailyIndex.type`.
- Time strings are passed through as they are: the `Z` suffix means UTC, and `local_time=True` is what asks for the local time.
- `Place.display_name()` joins the city and the district (the upstream `name` is the district, `adm2` is the city), and a city level entry does not repeat the city name.

---

<a id="upstream-docs"></a>
## 🔗 Official documentation

<https://dev.qweather.com/docs/>

---

<a id="license"></a>
## ⚖️ License

This package is released under the MIT license.

This package is not an official QWeather product. Using upstream data is subject to the [QWeather Developer EULA](https://www.qweather.com/terms/developers-eula/), and the attribution returned by the upstream must be kept when displaying weather data.





