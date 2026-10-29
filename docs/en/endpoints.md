# Endpoint Contracts

Reference: location forms, default TTLs, cache key prefixes, and the parameters and return types of all 26 endpoints.

## Supported Endpoints

26 endpoints covering twelve resource families. Three things to check before calling: location form, default TTL, cache key prefix.

| Package | Method | Endpoint constant | Upstream path | Location form | Default TTL | Cache key prefix |
| --- | --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `qwx.console.EndpointFinance` | `/finance/v1/summary` | None | 1 hour | `qwx:console:` |
| `qwx.console` | `stats` | `qwx.console.EndpointStats` | `/metrics/v1/stats` | None | 1 hour | `qwx:console:` |
| `qwx.geo` | `lookup_city` | `qwx.geo.EndpointCity` | `/geo/v2/city/lookup` | Coordinates / LocationID / Place name | 24 hours | `qwx:geo:` |
| `qwx.geo` | `lookup_poi` | `qwx.geo.EndpointPOI` | `/geo/v2/poi/lookup` | Coordinates / LocationID / Place name | 24 hours | `qwx:geo:` |
| `qwx.geo` | `poi_range` | `qwx.geo.EndpointPOIRange` | `/geo/v2/poi/range` | Coordinates | 24 hours | `qwx:geo:` |
| `qwx.geo` | `top_cities` | `qwx.geo.EndpointTopCities` | `/geo/v2/city/top` | None | 24 hours | `qwx:geo:` |
| `qwx.v1.airquality` | `current` | `qwx.v1.airquality.EndpointCurrent` | `/airquality/v1/current/{lat}/{lon}` | Coordinates | 30 minutes | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `daily` | `qwx.v1.airquality.EndpointDaily` | `/airquality/v1/daily/{lat}/{lon}` | Coordinates | 1 hour | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `hourly` | `qwx.v1.airquality.EndpointHourly` | `/airquality/v1/hourly/{lat}/{lon}` | Coordinates | 1 hour | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `station` | `qwx.v1.airquality.EndpointStation` | `/airquality/v1/stations/{stationID}` | Station ID | 30 minutes | `qwx:aq:v1:` |
| `qwx.v1.alert` | `current` | `qwx.v1.alert.Endpoint` | `/weatheralert/v1/current/{lat}/{lon}` | Coordinates | 5 minutes | `qwx:alert:v1:` |
| `qwx.v1.solarradiation` | `forecast` | `qwx.v1.solarradiation.Endpoint` | `/solarradiation/v1/forecast/{lat}/{lon}` | Coordinates | 1 hour | `qwx:solarradiation:v1:` |
| `qwx.v1.weather` | `current` | `qwx.v1.weather.EndpointCurrent` | `/weather/v1/current/{lat}/{lon}` | Coordinates | 10 minutes | `qwx:v1:` |
| `qwx.v1.weather` | `hourly` | `qwx.v1.weather.EndpointHourly` | `/weather/v1/hourly/{lat}/{lon}` | Coordinates | 1 hour | `qwx:v1:` |
| `qwx.v1.weather` | `daily` | `qwx.v1.weather.EndpointDaily` | `/weather/v1/daily/{lat}/{lon}` | Coordinates | 1 hour | `qwx:v1:` |
| `qwx.v7.astronomy` | `sun` | `qwx.v7.astronomy.EndpointSun` | `/v7/astronomy/sun` | Coordinates / LocationID | 24 hours | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `moon` | `qwx.v7.astronomy.EndpointMoon` | `/v7/astronomy/moon` | Coordinates / LocationID | 24 hours | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx.v7.astronomy.EndpointAngle` | `/v7/astronomy/solar-elevation-angle` | Coordinates | 24 hours | `qwx:astronomy:` |
| `qwx.v7.historical` | `weather` | `qwx.v7.historical.Endpoint` | `/v7/historical/weather` | LocationID | 24 hours | `qwx:historical:` |
| `qwx.v7.indices` | `indices` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | Coordinates | 1 hour | `qwx:indices:` |
| `qwx.v7.indices` | `indices_multi` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | Coordinates | 1 hour | `qwx:indices:` |
| `qwx.v7.minutely` | `minutely` | `qwx.v7.minutely.Endpoint` | `/v7/minutely/5m` | Coordinates | 5 minutes | `qwx:minutely:` |
| `qwx.v7.ocean` | `tide` | `qwx.v7.ocean.Endpoint` | `/v7/ocean/tide` | Station ID | 1 hour | `qwx:tide:` |
| `qwx.v7.storm` | `list` | `qwx.v7.storm.EndpointList` | `/v7/tropical/storm-list` | None | 24 hours | `qwx:storm:` |
| `qwx.v7.storm` | `forecast` | `qwx.v7.storm.EndpointForecast` | `/v7/tropical/storm-forecast` | None | 1 hour | `qwx:storm:` |
| `qwx.v7.storm` | `track` | `qwx.v7.storm.EndpointTrack` | `/v7/tropical/storm-track` | None | 1 hour | `qwx:storm:` |

Full cache key templates are in [Caching and TTL](cache.md), which also covers which parameters enter the key.

Upstream endpoints that qwx does not cover are listed in [Upstream Behavior and Limitations](upstream.md).

The **value** of an endpoint constant never changes after release: `qwx.TTLPolicy` matches by value, so changing a value silently breaks users' TTL configuration.

### Module Layout

| Module | Covers |
| --- | --- |
| `qwx` | Base client, auth, caching, `Location`, error hierarchy, request structures shared by both generations, `Refer`, `Metadata` |
| `qwx.v1` | Base types shared across new-generation endpoint families (`Metadata`, `Value`, `Options`) |
| `qwx.v1.weather` | New-generation weather `/weather/v1/*` |
| `qwx.v1.airquality` | New-generation air quality `/airquality/v1/*` |
| `qwx.v1.alert` | Weather alerts `/weatheralert/v1/*` |
| `qwx.v1.solarradiation` | New-generation solar radiation forecast `/solarradiation/v1/*` |
| `qwx.v7.ocean` | Old-generation tide `/v7/ocean/tide` |
| `qwx.v7.indices` | Old-generation life indices `/v7/indices/*` |
| `qwx.v7.minutely` | Old-generation minutely precipitation `/v7/minutely/*` |
| `qwx.v7.storm` | Tropical cyclones `/v7/tropical/*` |
| `qwx.v7.astronomy` | Astronomy `/v7/astronomy/*` |
| `qwx.v7.historical` | Old-generation historical weather `/v7/historical/weather` |
| `qwx.geo` | GeoAPI `/geo/v2/*` |
| `qwx.console` | Console `/finance/v1/*`, `/metrics/v1/stats` |
| `qwx.redis_cache` | Redis cache implementation (optional dependency `qwx[redis]`) |

One module = one upstream resource family. Two exceptions: the four lookup endpoints of `geo` share the `Place` type, and the two endpoints of `console` are documented on the same upstream page and share one response skeleton.

## Endpoint Contracts

Look here before writing call code: what an endpoint takes, what it returns, and where the boundaries are.

### Service Clients

Endpoints live in different modules depending on the upstream generation, and the methods hang off their own service clients:

| Module | Service client (sync / async) | Covers |
| --- | --- | --- |
| `qwx.v1` | None | Base types shared across new-generation endpoint families (`Metadata`, `Value`, `Options`) |
| `qwx.v1.weather` | `WeatherService` / `AsyncWeatherService` | New-generation weather |
| `qwx.v1.airquality` | `AirQualityService` / `AsyncAirQualityService` | New-generation air quality |
| `qwx.v1.alert` | `AlertService` / `AsyncAlertService` | Weather alerts |
| `qwx.v1.solarradiation` | `SolarRadiationService` / `AsyncSolarRadiationService` | New-generation solar radiation forecast |
| `qwx.v7.indices` | `IndicesService` / `AsyncIndicesService` | Old-generation life indices |
| `qwx.v7.minutely` | `MinutelyService` / `AsyncMinutelyService` | Old-generation minutely precipitation |
| `qwx.v7.storm` | `StormService` / `AsyncStormService` | Tropical cyclones |
| `qwx.v7.astronomy` | `AstronomyService` / `AsyncAstronomyService` | Astronomy |
| `qwx.v7.historical` | `HistoricalService` / `AsyncHistoricalService` | Old-generation historical weather |
| `qwx.v7.ocean` | `OceanService` / `AsyncOceanService` | Old-generation tide |
| `qwx.geo` | `GeoService` / `AsyncGeoService` | GeoAPI |
| `qwx.console` | `ConsoleService` / `AsyncConsoleService` | Console (finance summary, request volume statistics) |

`qwx.geo` is the only exception: its four lookup endpoints share one place type, and splitting them would leave that type without an owner.

Service clients are constructed with the base client, hold no state, and can be shared concurrently:

```python
import qwx
from qwx.v1.weather import WeatherService

auth = qwx.APIKeyAuth("YOUR_API_KEY")
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    weather = WeatherService(client)
    current = weather.current(qwx.Location(lat=39.92, lon=116.41))
```

The async version is symmetric, with the methods turning into coroutines:

```python
import qwx
from qwx.v1.weather import AsyncWeatherService

async with qwx.AsyncClient(auth, "abcxyz.qweatherapi.com") as client:
    weather = AsyncWeatherService(client)
    current = await weather.current(qwx.Location(lat=39.92, lon=116.41))
```

All modules share the same base client `qwx.Client(auth, api_host, ...)`. `api_host` is the dedicated API Host from the console "Settings" page and is required; the path prefix depends on the host, and GeoAPI is `/geo/v2/*` under a dedicated host.

Endpoint constants are used to set the cache duration per endpoint, see [Custom TTL](cache.md#custom-ttl).

### New Generation (Coordinates Only)

| Module | Method | Upstream path | Parameters | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.v1.weather` | `current` | `GET /weather/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `CurrentWeather` | `EndpointCurrent` |
| `qwx.v1.weather` | `hourly` | `GET /weather/v1/hourly/{lat}/{lon}` | `hours` 1..240; `opts` | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.weather` | `daily` | `GET /weather/v1/daily/{lat}/{lon}` | `days` 1..10; `opts` | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `current` | `GET /airquality/v1/current/{lat}/{lon}` | `opts: Options(lang)` | `Current` | `EndpointCurrent` |
| `qwx.v1.airquality` | `daily` | `GET /airquality/v1/daily/{lat}/{lon}` | Same as above | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `hourly` | `GET /airquality/v1/hourly/{lat}/{lon}` | Same as above | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.airquality` | `station` | `GET /airquality/v1/stations/{location_id}` | Station ID (e.g. `P51762`) non-empty | `StationData` | `EndpointStation` |
| `qwx.v1.alert` | `current` | `GET /weatheralert/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `Result` | `Endpoint` |
| `qwx.v1.solarradiation` | `forecast` | `GET /solarradiation/v1/forecast/{lat}/{lon}` | `hours` 1..72; `opts: Options(local_time, interval, tilt, azimuth, extra)` | `Result` | `Endpoint` |

Out-of-range parameters are intercepted client-side: `hours`/`days` raise `qwx.InvalidParameterError`, missing coordinates raise `qwx.InvalidLocationError`; neither case reaches upstream.

Allowed values for the `Options` fields of the solar radiation forecast: `interval` can only be 15, 30, 60 (0 means do not send it, and the upstream default of 60 applies); `tilt` 0~90; `azimuth` 0~359; `extra` accepts only `"weather"` and `"poa"`, multiple values are comma-separated, and duplicates or unknown values are rejected. When `extra` contains `"poa"`, upstream requires both `tilt` and `azimuth`.

### GeoAPI (Coordinates / LocationID / Place Name)

| Module | Method | Upstream path | Parameters | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.geo` | `lookup_city` | `GET /geo/v2/city/lookup` | `loc` in any of the three forms; `opts: Options(lang, number, adm, range)` | `CityResult` | `EndpointCity` |
| `qwx.geo` | `lookup_poi` | `GET /geo/v2/poi/lookup` | `loc` in any of the three forms; `typ` ∈ `POIType.SCENIC` / `POIType.CSTA` / `POIType.TSTA`; `opts: Options(lang, number, city)` | `POIResult` | `EndpointPOI` |
| `qwx.geo` | `poi_range` | `GET /geo/v2/poi/range` | `loc` accepts coordinates only; `typ`; `opts: POIRangeOptions(lang, number, radius)` | `RangeResult` | `EndpointPOIRange` |
| `qwx.geo` | `top_cities` | `GET /geo/v2/city/top` | `opts: Options(lang, number, range)` | `TopCityResult` | `EndpointTopCities` |

`number` 0 means the upstream default (10); `radius` 0 means the default (5).

`adm`, `range`, `city` are optional parameters on `Options`, and each endpoint only reports the ones it accepts: `adm` and `range` are only accepted by city lookup, `city` only by POI lookup, and `range` also by top cities. `adm` takes the LocationID of the parent administrative division (e.g. `101010100`), `range` takes an ISO 3166 country code (e.g. `cn`, `world`), and `city` takes a city name or a LocationID. All three affect the result, and all three enter the cache key.

`typ` is required and its value set is closed; a type outside the set raises `qwx.InvalidParameterError` without reaching upstream.

### Old Generation v7

The old-generation endpoints still have no new-generation counterpart. The old-generation alert `/v7/warning/now` has been removed; use `qwx.v1.alert` instead.

| Module | Method | Upstream path | Parameters | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.v7.ocean` | `tide` | `GET /v7/ocean/tide` | `station_id` tide station ID (`P2352`); `date` as local `YYYYMMDD` at the station | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices` | `GET /v7/indices/{days}d` | `loc` accepts coordinates only; `typ` 0..16; `days` ∈ {1, 3}; `lang` | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices_multi` | `GET /v7/indices/{days}d` | Same as above, `typ` may take multiple values (`[3, 5]`) | `Result` | `Endpoint` |
| `qwx.v7.minutely` | `minutely` | `GET /v7/minutely/5m` | `loc` accepts coordinates only; `lang` | `Result` | `Endpoint` |
| `qwx.v7.storm` | `list` | `GET /v7/tropical/storm-list` | `basin` accepts `NP` only; `year` positive integer | `ListResult` | `EndpointList` |
| `qwx.v7.storm` | `forecast` | `GET /v7/tropical/storm-forecast` | `storm_id` non-empty | `ForecastResult` | `EndpointForecast` |
| `qwx.v7.storm` | `track` | `GET /v7/tropical/storm-track` | `storm_id` non-empty | `TrackResult` | `EndpointTrack` |
| `qwx.v7.astronomy` | `sun` | `GET /v7/astronomy/sun` | `loc` accepts coordinates or LocationID; `date` as `YYYYMMDD` | `SunResult` | `EndpointSun` |
| `qwx.v7.astronomy` | `moon` | `GET /v7/astronomy/moon` | Same as above; `opts: Options(lang)` | `MoonResult` | `EndpointMoon` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `GET /v7/astronomy/solar-elevation-angle` | `loc` accepts coordinates only; `date`, `time_str` (`HHmm`), `tz` (e.g. `0800`), `alt` (altitude in meters, non-negative) | `AngleResult` | `EndpointAngle` |
| `qwx.v7.historical` | `weather` | `GET /v7/historical/weather` | `loc` accepts LocationID only; `date` as `YYYYMMDD`; `opts: Options(lang)` | `Result` | `Endpoint` |

`typ` for `qwx.v7.indices` ranges from 0 to 16, where 0 means all (`TYPE_ALL`); when `indices_multi` takes multiple types it must not include 0. `days` supports only 1 and 3.

`tide`, `indices`, and `minutely` still exist only in v7: in testing, all "new generation" variant paths (`/weather/v1/indices/*`, `/v1/indices/*`, `/ocean/v1/tide/*`) return 404.

Results of old-generation endpoints all carry a top-level `refer` object (data sources and license), the same shape as GeoAPI; read it from `Result.refer`. New-generation endpoints have no `refer`; the same information lives in `Metadata.attributions`.

### Console

The console API reports your own account's billing and request volume, not weather data. Credentials have no access by default: the account owner must enable console access under "Project Management - Credentials - Console Permissions" in the console, otherwise upstream returns 403 (`qwx.UnauthorizedError`).

| Module | Method | Upstream path | Parameters | Returns | Endpoint constant |
| --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `GET /finance/v1/summary` | None | `FinanceResult` | `EndpointFinance` |
| `qwx.console` | `stats` | `GET /metrics/v1/stats` | `opts: StatsOptions(project, credential)` | `StatsResult` | `EndpointStats` |

`project` and `credential` are mutually exclusive; setting both is rejected client-side (`qwx.InvalidParameterError`) without reaching upstream. Leaving both empty aggregates all projects and credentials under the account. Deleted projects or credentials cannot be queried individually, but their request volume still counts toward the summary.

The returned data is current up to the previous hour or earlier, which may lag the console web page by an hour or more; trust `as_of` in the response.

Field shapes:

- `balance` negative means outstanding balance; `currency` is the currency code (`CNY`, `USD`).
- The three numbers in `accrued_charges` are the accrued charges in total: for the previous day, for the current month, and since the last billing.
- `pending_bills[].type` and `status`, and the `status` of each resource plan, are enums; upstream adds new ones, so the SDK passes them through without enumerating a complete list.
- `available_resource_plans[].requests` comes back as a string in the upstream sample (`"1000000"`), while the official field table marks it as a number. The SDK accepts the union type `int | float | str` and parses both shapes.
- `as_of`, `pending_bills[].date`, `due_date`, and `effective_time` are UTC time strings, passed through as-is.
- The `hours` entry of each item in `success` / `errors` is the hourly request volume of the last 24 hours; upstream may return fewer than 24 entries, do not assume the length.

### Field Semantics

The same concept takes different shapes in the two generations; confirm which generation a value belongs to before using it.

| Concept | New generation | v7 |
| --- | --- | --- |
| Value and unit | Separate: `Value(value, unit)` | Concatenated into a single string |
| Precipitation probability | 0~1, present in hourly and daily forecasts, absent from current weather (`None` distinguishes "absent" from 0) | No such field |
| Precipitation intensity | `Precipitation.intensity` may be `None`: present in current weather and hourly forecasts, absent from daily forecasts (`None` distinguishes "absent" from 0) | No such field |
| Tide height | None | `Tide.height` stays a string, preserving upstream precision |
| Minutely precipitation | None | `Minutely.precip` stays a string: an empty string means "no data", `"0.00"` means "really no rain" |
| Data sources and license | `Metadata.attributions` | `Refer.sources` / `Refer.license`, same shape |
| Relative humidity | A percentage (0~100) in the solar radiation forecast | No such field |

Unified rules, do not assume otherwise:

- Optional fields always use `None`, so absence and a zero value stay distinguishable: `Metadata.zero_result`, `Astro`, `Alert.urgency` / `severity` / `certainty`, `Precipitation.probability`, `Precipitation.intensity`.
- The gust key name depends on the endpoint: current weather and hourly forecasts use `wind_gust`, the day/night periods of the daily forecast use `wind_gust_max` (`DayNight.wind_gust_max`).
- Do not assume list lengths: upstream may return fewer items for `HourlyForecast.hours` and `DailyForecast.days`.
- Enums grow; pass them through without enumerating a complete set: `Condition.code`, `Alert.event_type.code`, `DailyIndex.type`.
- Time strings are passed through as-is: a trailing `Z` means UTC, and local time requires `local_time=True`.
- `Place.display_name()` joins "city + district" (upstream `name` is the district and `adm2` is the city), so city-level entries do not repeat the city name.
