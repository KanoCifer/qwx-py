# 端点契约基线

由 `tools/extract_go_contract.py` 从 Go 源码抽取，与 Go 仓库的 `docs/endpoints.md` 逐项对账通过。改 Go 源码后重跑抽取器更新本文。

端点总数：**26**。

## 端点表

| 包 | 方法 | 端点常量 | 端点值 | 上游路径 | 位置形态 | 默认 TTL | 缓存键前缀 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `console` | `Finance` | `console.EndpointFinance` | `finance/v1/summary` | `/finance/v1/summary` | 无 | 1 小时 | `qwx:console:` |
| `console` | `Stats` | `console.EndpointStats` | `metrics/v1/stats` | `/metrics/v1/stats` | 无 | 1 小时 | `qwx:console:` |
| `geo` | `LookupCity` | `geo.EndpointCity` | `geo/v2/city/lookup` | `/geo/v2/city/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` |
| `geo` | `LookupPOI` | `geo.EndpointPOI` | `geo/v2/poi/lookup` | `/geo/v2/poi/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` |
| `geo` | `POIRange` | `geo.EndpointPOIRange` | `geo/v2/poi/range` | `/geo/v2/poi/range` | 坐标 | 24 小时 | `qwx:geo:` |
| `geo` | `TopCities` | `geo.EndpointTopCities` | `geo/v2/city/top` | `/geo/v2/city/top` | 无 | 24 小时 | `qwx:geo:` |
| `v1/airquality` | `Current` | `v1/airquality.EndpointCurrent` | `airquality/v1/current` | `/airquality/v1/current/{lat}/{lon}` | 坐标 | 30 分钟 | `qwx:aq:v1:` |
| `v1/airquality` | `Daily` | `v1/airquality.EndpointDaily` | `airquality/v1/daily` | `/airquality/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` |
| `v1/airquality` | `Hourly` | `v1/airquality.EndpointHourly` | `airquality/v1/hourly` | `/airquality/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` |
| `v1/airquality` | `Station` | `v1/airquality.EndpointStation` | `airquality/v1/stations` | `/airquality/v1/stations/{stationID}` | 站点 ID | 30 分钟 | `qwx:aq:v1:` |
| `v1/alert` | `Current` | `v1/alert.Endpoint` | `weatheralert/v1/current` | `/weatheralert/v1/current/{lat}/{lon}` | 坐标 | 5 分钟 | `qwx:alert:v1:` |
| `v1/solarradiation` | `Forecast` | `v1/solarradiation.Endpoint` | `solarradiation/v1/forecast` | `/solarradiation/v1/forecast/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:solarradiation:v1:` |
| `v1/weather` | `Current` | `v1/weather.EndpointCurrent` | `weather/v1/current` | `/weather/v1/current/{lat}/{lon}` | 坐标 | 10 分钟 | `qwx:v1:` |
| `v1/weather` | `Hourly` | `v1/weather.EndpointHourly` | `weather/v1/hourly` | `/weather/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` |
| `v1/weather` | `Daily` | `v1/weather.EndpointDaily` | `weather/v1/daily` | `/weather/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` |
| `v7/astronomy` | `Sun` | `v7/astronomy.EndpointSun` | `v7/astronomy/sun` | `/v7/astronomy/sun` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` |
| `v7/astronomy` | `Moon` | `v7/astronomy.EndpointMoon` | `v7/astronomy/moon` | `/v7/astronomy/moon` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` |
| `v7/astronomy` | `SolarElevationAngle` | `v7/astronomy.EndpointAngle` | `v7/astronomy/solar-elevation-angle` | `/v7/astronomy/solar-elevation-angle` | 坐标 | 24 小时 | `qwx:astronomy:` |
| `v7/historical` | `Weather` | `v7/historical.Endpoint` | `v7/historical/weather` | `/v7/historical/weather` | LocationID | 24 小时 | `qwx:historical:` |
| `v7/indices` | `Indices` | `v7/indices.Endpoint` | `v7/indices` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` |
| `v7/indices` | `IndicesMulti` | `v7/indices.Endpoint` | `v7/indices` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` |
| `v7/minutely` | `Minutely` | `v7/minutely.Endpoint` | `v7/minutely/5m` | `/v7/minutely/5m` | 坐标 | 5 分钟 | `qwx:minutely:` |
| `v7/ocean` | `Tide` | `v7/ocean.Endpoint` | `v7/ocean/tide` | `/v7/ocean/tide` | 站点 ID | 1 小时 | `qwx:tide:` |
| `v7/storm` | `List` | `v7/storm.EndpointList` | `v7/tropical/storm-list` | `/v7/tropical/storm-list` | 无 | 24 小时 | `qwx:storm:` |
| `v7/storm` | `Forecast` | `v7/storm.EndpointForecast` | `v7/tropical/storm-forecast` | `/v7/tropical/storm-forecast` | 无 | 1 小时 | `qwx:storm:` |
| `v7/storm` | `Track` | `v7/storm.EndpointTrack` | `v7/tropical/storm-track` | `/v7/tropical/storm-track` | 无 | 1 小时 | `qwx:storm:` |

## 缓存键模板

模板里的花括号是占位符。参数后缀只在该参数有值时出现。

| 包.方法 | 模板 |
| --- | --- |
| console.Finance | `qwx:console:finance` |
| console.Stats | `qwx:console:stats:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| geo.LookupCity | `qwx:geo:city:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| geo.LookupPOI | `qwx:geo:poi:{typ}:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| geo.POIRange | `qwx:geo:poirange:{typ}:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| geo.TopCities | `qwx:geo:topcity:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/airquality.Current | `qwx:aq:v1:current:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/airquality.Daily | `qwx:aq:v1:daily:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/airquality.Hourly | `qwx:aq:v1:hourly:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/airquality.Station | `qwx:aq:v1:station:{station_id}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/alert.Current | `qwx:alert:v1:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/solarradiation.Forecast | `qwx:solarradiation:v1:forecast:{lat},{lon}:h{hours}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/weather.Current | `qwx:v1:current:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/weather.Hourly | `qwx:v1:hourly:{lat},{lon}:h{hours}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v1/weather.Daily | `qwx:v1:daily:{lat},{lon}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/astronomy.Sun | `qwx:astronomy:sun:{location}:{date}` |
| v7/astronomy.Moon | `qwx:astronomy:moon:{location}:{date}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/astronomy.SolarElevationAngle | `qwx:astronomy:angle:{location}:{date}:{time}:{tz}:{alt}` |
| v7/historical.Weather | `qwx:historical:weather:{id}:{date}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/indices.Indices | `qwx:indices:{location}:t{type}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/indices.IndicesMulti | `qwx:indices:{location}:t{type}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/minutely.Minutely | `qwx:minutely:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| v7/ocean.Tide | `qwx:tide:{station_id}:{date}` |
| v7/storm.List | `qwx:storm:list:{basin}:{year}` |
| v7/storm.Forecast | `qwx:storm:forecast:{storm_id}` |
| v7/storm.Track | `qwx:storm:track:{storm_id}` |

## 查询参数

| 包.方法 | 参数 | 取值来源 |
| --- | --- | --- |
| console.Finance | 无 | 无 |
| console.Stats | 无 | 无 |
| geo.LookupCity | 无 | 无 |
| geo.LookupPOI | 无 | 无 |
| geo.POIRange | 无 | 无 |
| geo.TopCities | 无 | 无 |
| v1/airquality.Current | 无 | 无 |
| v1/airquality.Daily | 无 | 无 |
| v1/airquality.Hourly | 无 | 无 |
| v1/airquality.Station | 无 | 无 |
| v1/alert.Current | 无 | 无 |
| v1/solarradiation.Forecast | 无 | 无 |
| v1/weather.Current | 无 | 无 |
| v1/weather.Hourly | 无 | 无 |
| v1/weather.Daily | 无 | 无 |
| v7/astronomy.Sun | 无 | 无 |
| v7/astronomy.Moon | 无 | 无 |
| v7/astronomy.SolarElevationAngle | 无 | 无 |
| v7/historical.Weather | 无 | 无 |
| v7/indices.Indices | 无 | 无 |
| v7/indices.IndicesMulti | 无 | 无 |
| v7/minutely.Minutely | 无 | 无 |
| v7/ocean.Tide | 无 | 无 |
| v7/storm.List | 无 | 无 |
| v7/storm.Forecast | 无 | 无 |
| v7/storm.Track | 无 | 无 |

## 参数约束

客户端先校验，越界返回 `InvalidParameterError`，不打上游。

| 包.方法 | 参数 | 约束 |
| --- | --- | --- |
| v1/solarradiation.Forecast | `hours` | 1 ≤ 值 ≤ 72 |
| v1/solarradiation.Forecast | `tilt` | 0 ≤ 值 ≤ 90 |
| v1/solarradiation.Forecast | `azimuth` | 0 ≤ 值 ≤ 359 |
| v1/weather.Hourly | `hours` | 1 ≤ 值 ≤ 240 |
| v1/weather.Daily | `days` | 1 ≤ 值 ≤ 10 |
| v7/astronomy.Sun | `date` | 长度 = 8 |
| v7/astronomy.Moon | `date` | 长度 = 8 |
| v7/astronomy.SolarElevationAngle | `alt` | 值 ≥ 0 |
| v7/astronomy.SolarElevationAngle | `date` | 长度 = 8 |
| v7/astronomy.SolarElevationAngle | `time_str` | 长度 = 4 |
| v7/astronomy.SolarElevationAngle | `minutes` | 值 ≤ 59 |
| v7/historical.Weather | `date` | 长度 = 8 |
| v7/indices.Indices | `typ` | 0 ≤ 值 ≤ 16 |
| v7/indices.Indices | `days` | 只取 1 或 3 |
| v7/indices.IndicesMulti | `typ` | 0 ≤ 值 ≤ 16 |
| v7/indices.IndicesMulti | `days` | 只取 1 或 3 |
| v7/ocean.Tide | `date` | 长度 = 8 |
| v7/storm.List | `basin` | 只取 NP |
| v7/storm.List | `year` | 值 ≥ 0 |

## 客户端校验点

| 包.方法 | 校验 |
| --- | --- |
| console.Stats | `return nil, fmt.Errorf("%w: project and credential are mutually exclusive", qwx.ErrInvalidParameter)` |
| geo.LookupPOI | `return nil, fmt.Errorf("%w: unsupported POI type %q", qwx.ErrInvalidParameter, typ)` |
| geo.POIRange | `return nil, fmt.Errorf("%w: unsupported POI type %q", qwx.ErrInvalidParameter, typ)` |
| geo.POIRange | `return nil, fmt.Errorf("%w: POI range requires coordinates", qwx.ErrInvalidLocation)` |
| v1/airquality.Station | `return nil, fmt.Errorf("%w: empty station ID", qwx.ErrInvalidParameter)` |
| v1/solarradiation.Forecast | `// validateForecast 校验端点参数，越界返回 [qwx.ErrInvalidParameter]。` |
| v1/solarradiation.Forecast | `return fmt.Errorf("%w: hours %d out of range [%d,%d]", qwx.ErrInvalidParameter, hours, minForecastHours, MaxForecastHours)` |
| v1/solarradiation.Forecast | `return fmt.Errorf("%w: interval %d not in {15,30,60}", qwx.ErrInvalidParameter, o.Interval)` |
| v1/solarradiation.Forecast | `return fmt.Errorf("%w: tilt %d out of range [0,90]", qwx.ErrInvalidParameter, *o.Tilt)` |
| v1/solarradiation.Forecast | `return fmt.Errorf("%w: azimuth %d out of range [0,359]", qwx.ErrInvalidParameter, *o.Azimuth)` |
| v1/solarradiation.Forecast | `return fmt.Errorf("%w: extra=poa requires both tilt and azimuth", qwx.ErrInvalidParameter)` |
| v1/solarradiation.Forecast | `return nil, fmt.Errorf("%w: extra %q contains unknown value %q", qwx.ErrInvalidParameter, raw, part)` |
| v1/solarradiation.Forecast | `return nil, fmt.Errorf("%w: extra %q contains duplicate value %q", qwx.ErrInvalidParameter, raw, part)` |
| v1/weather.Current | `// hours 取值 1~240，超出范围返回 [qwx.ErrInvalidParameter]，不打上游。` |
| v1/weather.Hourly | `return nil, fmt.Errorf("%w: hours %d out of range [1,%d]", qwx.ErrInvalidParameter, hours, MaxHourlyHours)` |
| v1/weather.Hourly | `// days 取值 1~10，超出范围返回 [qwx.ErrInvalidParameter]，不打上游。` |
| v1/weather.Daily | `return nil, fmt.Errorf("%w: days %d out of range [1,%d]", qwx.ErrInvalidParameter, days, MaxDailyDays)` |
| v7/astronomy.Moon | `// 参数越界返回 [qwx.ErrInvalidParameter]，位置形态不对返回` |
| v7/astronomy.Moon | `// [qwx.ErrInvalidLocation]，两种都在打上游之前返回。` |
| v7/astronomy.SolarElevationAngle | `return nil, fmt.Errorf("%w: altitude %d must not be negative", qwx.ErrInvalidParameter, alt)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: astronomy requires coordinates or a LocationID", qwx.ErrInvalidLocation)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: solar elevation angle requires coordinates", qwx.ErrInvalidLocation)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: date %q must be in yyyyMMdd format", qwx.ErrInvalidParameter, date)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: date %q is not a valid calendar date", qwx.ErrInvalidParameter, date)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: time %q must be in HHmm format", qwx.ErrInvalidParameter, timeStr)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: time %q is not a valid 24-hour time", qwx.ErrInvalidParameter, timeStr)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: tz %q must be in HHmm format, like 0800 or -0530", qwx.ErrInvalidParameter, tz)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: tz %q must be in HHmm format, like 0800 or -0530", qwx.ErrInvalidParameter, tz)` |
| v7/astronomy.SolarElevationAngle | `return fmt.Errorf("%w: tz %q is out of the UTC offset range [-12:00,+14:00]", qwx.ErrInvalidParameter, tz)` |
| v7/historical.Weather | `return nil, fmt.Errorf("%w: historical weather requires a LocationID", qwx.ErrInvalidLocation)` |
| v7/historical.Weather | `return fmt.Errorf("%w: date %q must be in yyyyMMdd format", qwx.ErrInvalidParameter, date)` |
| v7/historical.Weather | `return fmt.Errorf("%w: date %q is not a valid calendar date", qwx.ErrInvalidParameter, date)` |
| v7/indices.Indices | `return nil, fmt.Errorf("%w: indices types must not be empty", qwx.ErrInvalidParameter)` |
| v7/indices.Indices | `return nil, fmt.Errorf("%w: indices type %d out of range [%d,%d]", qwx.ErrInvalidParameter, typ, TypeAll, MaxType)` |
| v7/indices.Indices | `return nil, fmt.Errorf("%w: indices type %d cannot be combined with other types", qwx.ErrInvalidParameter, TypeAll)` |
| v7/indices.Indices | `return nil, fmt.Errorf("%w: indices days %d is not supported (only 1 and 3)", qwx.ErrInvalidParameter, days)` |
| v7/indices.Indices | `return nil, fmt.Errorf("%w: indices requires coordinates", qwx.ErrInvalidLocation)` |
| v7/indices.IndicesMulti | `return nil, fmt.Errorf("%w: indices types must not be empty", qwx.ErrInvalidParameter)` |
| v7/indices.IndicesMulti | `return nil, fmt.Errorf("%w: indices type %d out of range [%d,%d]", qwx.ErrInvalidParameter, typ, TypeAll, MaxType)` |
| v7/indices.IndicesMulti | `return nil, fmt.Errorf("%w: indices type %d cannot be combined with other types", qwx.ErrInvalidParameter, TypeAll)` |
| v7/indices.IndicesMulti | `return nil, fmt.Errorf("%w: indices days %d is not supported (only 1 and 3)", qwx.ErrInvalidParameter, days)` |
| v7/indices.IndicesMulti | `return nil, fmt.Errorf("%w: indices requires coordinates", qwx.ErrInvalidLocation)` |
| v7/minutely.Minutely | `return nil, fmt.Errorf("%w: minutely forecast requires coordinates", qwx.ErrInvalidLocation)` |
| v7/ocean.Tide | `return nil, fmt.Errorf("%w: empty tide station ID", qwx.ErrInvalidParameter)` |
| v7/ocean.Tide | `return fmt.Errorf("%w: date %q must be in YYYYMMDD format", qwx.ErrInvalidParameter, date)` |
| v7/ocean.Tide | `return fmt.Errorf("%w: date %q must be in YYYYMMDD format", qwx.ErrInvalidParameter, date)` |
| v7/storm.List | `return nil, fmt.Errorf("%w: storm basin %q is not supported (only %q)", qwx.ErrInvalidParameter, basin, BasinNP)` |
| v7/storm.List | `return nil, fmt.Errorf("%w: storm year %d must be positive", qwx.ErrInvalidParameter, year)` |
| v7/storm.List | `// stormid 必填且不能为空串，空串返回 [qwx.ErrInvalidParameter]。` |
| v7/storm.Forecast | `return nil, fmt.Errorf("%w: storm forecast requires a storm id", qwx.ErrInvalidParameter)` |
| v7/storm.Forecast | `// stormid 必填且不能为空串，空串返回 [qwx.ErrInvalidParameter]。` |
| v7/storm.Track | `return nil, fmt.Errorf("%w: storm track requires a storm id", qwx.ErrInvalidParameter)` |

## 参数后缀模板

由 `internal/cachekey/params.go` 的 `Params.suffix()` 还原，顺序即字节顺序。

`:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}`

## 缓存键族前缀

前缀与包名不必对齐。`qwx:tide:` 不是 `qwx:ocean:`，这是已发布键字面量的约定。

| 族 | 前缀 |
| --- | --- |
| `FamilyWeather` | `qwx:v1:` |
| `FamilyAirQuality` | `qwx:aq:v1:` |
| `FamilyAlert` | `qwx:alert:v1:` |
| `FamilyGeo` | `qwx:geo:` |
| `FamilyTide` | `qwx:tide:` |
| `FamilyIndices` | `qwx:indices:` |
| `FamilyMinutely` | `qwx:minutely:` |
| `FamilySolarRadiation` | `qwx:solarradiation:v1:` |
| `FamilyStorm` | `qwx:storm:` |
| `FamilyAstronomy` | `qwx:astronomy:` |
| `FamilyHistorical` | `qwx:historical:` |
| `FamilyConsole` | `qwx:console:` |
