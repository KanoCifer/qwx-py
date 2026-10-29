# Upstream Behavior and Limitations

Reference: the shutdown status of upstream endpoints and their replacements, plus the quirks measured for each endpoint.

## Shutdowns and Replacements

Upstream still has these endpoints; this library does not implement them. They fall into two groups: those with a fixed shutdown date should not be coded against, those still alive can be added on demand.

| Upstream path | Status | Notes |
| --- | --- | --- |
| `/v7/warning/now` | Shut down 2026-09-01 | Use `qwx.v1.alert` |
| `/v7/air/now` | Shut down 2026-06-01 | Use `qwx.v1.airquality` |
| `/v7/air/5d` | Shut down 2026-06-01 | Use `qwx.v1.airquality` |
| `/v7/solar-radiation/{hours}` | Shut down 2026-12-31 | Use `qwx.v1.solarradiation` |
| `/v7/grid-weather/now` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/grid-weather/{days}` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/grid-weather/{hours}` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/weather/now` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/weather/{days}` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/weather/{hours}` | Shut down 2027-02-01 | Use `qwx.v1.weather` |
| `/v7/historical/air` | Deprecated | No replacement |

The `/v7/minutely/5m`, `/v7/indices/{days}`, `/v7/ocean/tide`, and `/v7/historical/weather` endpoints supported by this library are not on the shutdown list and can keep being used.

The public domains `devapi.qweather.com`, `api.qweather.com`, `geoapi.qweather.com` have been shut down one after another since 2026-01 and 2026-06. The SDK ships no default Host; you must use the dedicated Host assigned in the console.

## Upstream Quirks and Limitations

One point per line, stating the symptom and the root cause.

- The public domains were shut down in 2026-01 and 2026-06; `/v7/warning/now` was shut down on 2026-09-01 (use `qwx.v1.alert`); `/v7/grid-weather/*` and `/v7/weather/*` are shut down on 2027-02-01 (use `qwx.v1.weather`).
- API KEY authentication is subject to a daily request quota starting 2027-01-01 and is no longer supported in SDK 5+. Use JWT for new projects.
- Console endpoints require the account owner to enable access separately under "Project Management - Credentials - Console Permissions" in the console, otherwise they return 403.
- `tide`, `indices`, and `minutely` still only have a v7 version; in testing every "new generation" variant path returns 404.
- `days` supports only 1 and 3 on life indices.
- Tropical cyclone `basin` supports only `NP`.
- The `humidity` of the solar radiation forecast is a percentage (0~100), while other new-generation endpoints give a 0~1 ratio.
- The solar radiation forecast family has no `lang` parameter; passing one is rejected.
- The monitoring station path is plural: `/airquality/v1/stations/{id}`.
- The new generation returns UTC times by default (values like `2026-10-21T05:00Z`); local time requires `local_time=True`.
- Humidity and cloud cover in the new generation are 0~1 ratios, not percentages. The day/night periods of the daily forecast have no `intensity` field.
- The precipitation intensity of the daily forecast is always 0 because upstream does not give `intensity`, not because there is genuinely no rain. Check that `Precipitation.intensity` is not `None` before reading it.
- The `date` of the tide endpoint must be the local date at the station. Between 00:00 and 08:00 Beijing time it falls on "yesterday"; a UTC date always returns 400.
- POI lookup returns 400 `No Such Location` (not an empty list): there really is no POI of that type nearby. Querying TSTA / CSTA in an inland city always returns 400; only coastal cities have them.
- The `loc` of life indices accepts a coordinate pair only; a bare longitude (e.g. `121.47`) is rejected.
- Minutely precipitation covers China only; upstream has no data for coordinates outside China.
- The `date` of the astronomy endpoints accepts at most 60 days into the future (today included).
- Sunrise and sunset are null at high latitudes and in polar day/night regions; test with `is None`, do not treat them as empty strings.
- Querying the forecast of a finished typhoon returns an empty list, not an error. Check the storm status with `storm.list` first.
- Weather alerts accept coordinates only; upstream rejects a LocationID or a place name outright.
- Historical weather only gives the last 10 days and does not include today, and `loc` accepts LocationID only. The fields are `weatherDaily` / `weatherHourly`, not `daily` / `hourly`.
- City lookup searches a limited range by default; for cities outside China, pass `Options.range` with an ISO 3166 country code (e.g. `world`).
- Different AQI standards use different scales (QAQI is 0~1, US EPA is 0~500); do not compare values across standards.
- Console data is current only up to the previous hour or later, while the web page is real-time; trust `as_of` in the response.
- For the console, `available_resource_plans[].requests` is given as a string in the upstream sample while the official field table marks it as a number; the SDK accepts `int | float | str`.

When upstream behavior conflicts with the official documentation, the live smoke test takes precedence; record measured conclusions in this file and mirror them into the docstring of the corresponding method.
