# 端点契约

参考文档：26 个端点的位置形态、默认 TTL、缓存键前缀，以及每个端点的参数与返回类型。

## 支持的接口

26 个端点，覆盖十二个资源族。表里的位置形态、默认 TTL、缓存键前缀是调用前要看的三件事。

| 包 | 方法 | 端点常量 | 上游路径 | 位置形态 | 默认 TTL | 缓存键前缀 |
| --- | --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `qwx.console.EndpointFinance` | `/finance/v1/summary` | 无 | 1 小时 | `qwx:console:` |
| `qwx.console` | `stats` | `qwx.console.EndpointStats` | `/metrics/v1/stats` | 无 | 1 小时 | `qwx:console:` |
| `qwx.geo` | `lookup_city` | `qwx.geo.EndpointCity` | `/geo/v2/city/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` |
| `qwx.geo` | `lookup_poi` | `qwx.geo.EndpointPOI` | `/geo/v2/poi/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` |
| `qwx.geo` | `poi_range` | `qwx.geo.EndpointPOIRange` | `/geo/v2/poi/range` | 坐标 | 24 小时 | `qwx:geo:` |
| `qwx.geo` | `top_cities` | `qwx.geo.EndpointTopCities` | `/geo/v2/city/top` | 无 | 24 小时 | `qwx:geo:` |
| `qwx.v1.airquality` | `current` | `qwx.v1.airquality.EndpointCurrent` | `/airquality/v1/current/{lat}/{lon}` | 坐标 | 30 分钟 | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `daily` | `qwx.v1.airquality.EndpointDaily` | `/airquality/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `hourly` | `qwx.v1.airquality.EndpointHourly` | `/airquality/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` |
| `qwx.v1.airquality` | `station` | `qwx.v1.airquality.EndpointStation` | `/airquality/v1/stations/{stationID}` | 站点 ID | 30 分钟 | `qwx:aq:v1:` |
| `qwx.v1.alert` | `current` | `qwx.v1.alert.Endpoint` | `/weatheralert/v1/current/{lat}/{lon}` | 坐标 | 5 分钟 | `qwx:alert:v1:` |
| `qwx.v1.solarradiation` | `forecast` | `qwx.v1.solarradiation.Endpoint` | `/solarradiation/v1/forecast/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:solarradiation:v1:` |
| `qwx.v1.weather` | `current` | `qwx.v1.weather.EndpointCurrent` | `/weather/v1/current/{lat}/{lon}` | 坐标 | 10 分钟 | `qwx:v1:` |
| `qwx.v1.weather` | `hourly` | `qwx.v1.weather.EndpointHourly` | `/weather/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` |
| `qwx.v1.weather` | `daily` | `qwx.v1.weather.EndpointDaily` | `/weather/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` |
| `qwx.v7.astronomy` | `sun` | `qwx.v7.astronomy.EndpointSun` | `/v7/astronomy/sun` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `moon` | `qwx.v7.astronomy.EndpointMoon` | `/v7/astronomy/moon` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx.v7.astronomy.EndpointAngle` | `/v7/astronomy/solar-elevation-angle` | 坐标 | 24 小时 | `qwx:astronomy:` |
| `qwx.v7.historical` | `weather` | `qwx.v7.historical.Endpoint` | `/v7/historical/weather` | LocationID | 24 小时 | `qwx:historical:` |
| `qwx.v7.indices` | `indices` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` |
| `qwx.v7.indices` | `indices_multi` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` |
| `qwx.v7.minutely` | `minutely` | `qwx.v7.minutely.Endpoint` | `/v7/minutely/5m` | 坐标 | 5 分钟 | `qwx:minutely:` |
| `qwx.v7.ocean` | `tide` | `qwx.v7.ocean.Endpoint` | `/v7/ocean/tide` | 站点 ID | 1 小时 | `qwx:tide:` |
| `qwx.v7.storm` | `list` | `qwx.v7.storm.EndpointList` | `/v7/tropical/storm-list` | 无 | 24 小时 | `qwx:storm:` |
| `qwx.v7.storm` | `forecast` | `qwx.v7.storm.EndpointForecast` | `/v7/tropical/storm-forecast` | 无 | 1 小时 | `qwx:storm:` |
| `qwx.v7.storm` | `track` | `qwx.v7.storm.EndpointTrack` | `/v7/tropical/storm-track` | 无 | 1 小时 | `qwx:storm:` |

缓存键的完整模板见[缓存与 TTL](cache.md)，那里还有参数的进键规则。

上游有但 qwx 未覆盖的端点见[上游行为与限制](upstream.md)。

端点常量的**值**发布后不再变更：`qwx.TTLPolicy` 按值匹配，改值会让用户的 TTL 配置静默失效。

### 模块结构

| 模块 | 承载 |
| --- | --- |
| `qwx` | 基础客户端、认证、缓存、`Location`、错误层级、两代共用的请求结构、`Refer`、`Metadata` |
| `qwx.v1` | 新一代跨端点族共用的基础类型（`Metadata`、`Value`、`Options`） |
| `qwx.v1.weather` | 新一代天气 `/weather/v1/*` |
| `qwx.v1.airquality` | 新一代空气质量 `/airquality/v1/*` |
| `qwx.v1.alert` | 预警 `/weatheralert/v1/*` |
| `qwx.v1.solarradiation` | 新一代太阳辐射预报 `/solarradiation/v1/*` |
| `qwx.v7.ocean` | 旧一代潮汐 `/v7/ocean/tide` |
| `qwx.v7.indices` | 旧一代生活指数 `/v7/indices/*` |
| `qwx.v7.minutely` | 旧一代分钟级降水 `/v7/minutely/*` |
| `qwx.v7.storm` | 台风 `/v7/tropical/*` |
| `qwx.v7.astronomy` | 天文 `/v7/astronomy/*` |
| `qwx.v7.historical` | 旧一代历史天气 `/v7/historical/weather` |
| `qwx.geo` | GeoAPI `/geo/v2/*` |
| `qwx.console` | 控制台 `/finance/v1/*`、`/metrics/v1/stats` |
| `qwx.redis_cache` | Redis 缓存实现（可选依赖 `qwx[redis]`） |

一个模块 = 一个上游资源族。两个例外：`geo` 的四个检索端点共享 `Place` 类型，`console` 的两个端点在上游归在同一页文档下、共享同一套响应骨架。

## 端点契约

写调用代码前查这里：端点要传什么、返回什么、边界在哪。

### 服务客户端

端点按上游代际分属不同模块，方法挂在各自的服务客户端上：

| 模块 | 服务客户端（同步 / 异步） | 覆盖 |
| --- | --- | --- |
| `qwx.v1` | 无 | 新一代跨端点族共用的基础类型（`Metadata`、`Value`、`Options`） |
| `qwx.v1.weather` | `WeatherService` / `AsyncWeatherService` | 新一代天气 |
| `qwx.v1.airquality` | `AirQualityService` / `AsyncAirQualityService` | 新一代空气质量 |
| `qwx.v1.alert` | `AlertService` / `AsyncAlertService` | 预警 |
| `qwx.v1.solarradiation` | `SolarRadiationService` / `AsyncSolarRadiationService` | 新一代太阳辐射预报 |
| `qwx.v7.indices` | `IndicesService` / `AsyncIndicesService` | 旧一代生活指数 |
| `qwx.v7.minutely` | `MinutelyService` / `AsyncMinutelyService` | 旧一代分钟级降水 |
| `qwx.v7.storm` | `StormService` / `AsyncStormService` | 台风 |
| `qwx.v7.astronomy` | `AstronomyService` / `AsyncAstronomyService` | 天文 |
| `qwx.v7.historical` | `HistoricalService` / `AsyncHistoricalService` | 旧一代历史天气 |
| `qwx.v7.ocean` | `OceanService` / `AsyncOceanService` | 旧一代潮汐 |
| `qwx.geo` | `GeoService` / `AsyncGeoService` | GeoAPI |
| `qwx.console` | `ConsoleService` / `AsyncConsoleService` | 控制台（财务汇总、请求量统计） |

`qwx.geo` 是唯一的例外：它的四个检索端点共享同一个地点类型，拆开会让该类型失去归属。

服务客户端用基础客户端构造，无状态，可并发共享：

```python
import qwx
from qwx.v1.weather import WeatherService

auth = qwx.APIKeyAuth("你的 API KEY")
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    weather = WeatherService(client)
    current = weather.current(qwx.Location(lat=39.92, lon=116.41))
```

异步版对称，方法变成协程：

```python
import qwx
from qwx.v1.weather import AsyncWeatherService

async with qwx.AsyncClient(auth, "abcxyz.qweatherapi.com") as client:
    weather = AsyncWeatherService(client)
    current = await weather.current(qwx.Location(lat=39.92, lon=116.41))
```

所有模块共用同一个基础客户端 `qwx.Client(auth, api_host, ...)`。`api_host` 是控制台「设置」页里的专属 API Host，必填；路径前缀因 Host 而定，GeoAPI 在专属 Host 下是 `/geo/v2/*`。

端点常量用于按端点调缓存时长，见[自定义 TTL](cache.md#自定义-ttl)。

### 新一代（只认坐标）

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.v1.weather` | `current` | `GET /weather/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `CurrentWeather` | `EndpointCurrent` |
| `qwx.v1.weather` | `hourly` | `GET /weather/v1/hourly/{lat}/{lon}` | `hours` 1..240；`opts` | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.weather` | `daily` | `GET /weather/v1/daily/{lat}/{lon}` | `days` 1..10；`opts` | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `current` | `GET /airquality/v1/current/{lat}/{lon}` | `opts: Options(lang)` | `Current` | `EndpointCurrent` |
| `qwx.v1.airquality` | `daily` | `GET /airquality/v1/daily/{lat}/{lon}` | 同上 | `DailyForecast` | `EndpointDaily` |
| `qwx.v1.airquality` | `hourly` | `GET /airquality/v1/hourly/{lat}/{lon}` | 同上 | `HourlyForecast` | `EndpointHourly` |
| `qwx.v1.airquality` | `station` | `GET /airquality/v1/stations/{location_id}` | 站点 ID（如 `P51762`）非空 | `StationData` | `EndpointStation` |
| `qwx.v1.alert` | `current` | `GET /weatheralert/v1/current/{lat}/{lon}` | `opts: Options(lang, local_time)` | `Result` | `Endpoint` |
| `qwx.v1.solarradiation` | `forecast` | `GET /solarradiation/v1/forecast/{lat}/{lon}` | `hours` 1..72；`opts: Options(local_time, interval, tilt, azimuth, extra)` | `Result` | `Endpoint` |

越界参数在客户端拦截：`hours`/`days` 返回 `qwx.InvalidParameterError`，无坐标返回 `qwx.InvalidLocationError`，两处都不打上游。

太阳辐射预报的 `Options` 各字段的取值：`interval` 只能是 15、30、60（0 表示不传，用上游默认 60）；`tilt` 0~90；`azimuth` 0~359；`extra` 只认 `"weather"` 与 `"poa"`，多项用逗号分隔，重复项与未知取值都会被拒。`extra` 含 `"poa"` 时上游要求 `tilt` 与 `azimuth` 都传。

### GeoAPI（认坐标 / LocationID / 地名）

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.geo` | `lookup_city` | `GET /geo/v2/city/lookup` | `loc` 三形态皆可；`opts: Options(lang, number, adm, range)` | `CityResult` | `EndpointCity` |
| `qwx.geo` | `lookup_poi` | `GET /geo/v2/poi/lookup` | `loc` 三形态皆可；`typ` ∈ `POIType.SCENIC` / `POIType.CSTA` / `POIType.TSTA`；`opts: Options(lang, number, city)` | `POIResult` | `EndpointPOI` |
| `qwx.geo` | `poi_range` | `GET /geo/v2/poi/range` | `loc` 只认坐标；`typ`；`opts: POIRangeOptions(lang, number, radius)` | `RangeResult` | `EndpointPOIRange` |
| `qwx.geo` | `top_cities` | `GET /geo/v2/city/top` | `opts: Options(lang, number, range)` | `TopCityResult` | `EndpointTopCities` |

`number` 为 0 时走上游默认（10），`radius` 为 0 时走默认（5）。

`adm`、`range`、`city` 是 `Options` 上的可选参数，各端点只上报自己认的那几个：`adm` 与 `range` 只有城市检索认，`city` 只有 POI 检索认，`range` 热门城市也认。`adm` 传上级行政区划的 LocationID（如 `101010100`），`range` 传 ISO 3166 国家代码（如 `cn`、`world`），`city` 传城市名或 LocationID。三个参数都影响结果，都进缓存键。

`typ` 必填，取值是闭集，传闭集外的类型抛 `qwx.InvalidParameterError`，不打上游。

### 旧一代 v7

旧一代的端点至今没有新一代对应版本。旧一代预警 `/v7/warning/now` 已移除，统一用 `qwx.v1.alert`。

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.v7.ocean` | `tide` | `GET /v7/ocean/tide` | `station_id` 潮汐站 ID（`P2352`）；`date` 为站点当地 `YYYYMMDD` | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices` | `GET /v7/indices/{days}d` | `loc` 只认坐标；`typ` 0..16；`days` ∈ {1, 3}；`lang` | `Result` | `Endpoint` |
| `qwx.v7.indices` | `indices_multi` | `GET /v7/indices/{days}d` | 同上，`typ` 可传多个（`[3, 5]`） | `Result` | `Endpoint` |
| `qwx.v7.minutely` | `minutely` | `GET /v7/minutely/5m` | `loc` 只认坐标；`lang` | `Result` | `Endpoint` |
| `qwx.v7.storm` | `list` | `GET /v7/tropical/storm-list` | `basin` 只认 `NP`；`year` 正整数 | `ListResult` | `EndpointList` |
| `qwx.v7.storm` | `forecast` | `GET /v7/tropical/storm-forecast` | `storm_id` 非空 | `ForecastResult` | `EndpointForecast` |
| `qwx.v7.storm` | `track` | `GET /v7/tropical/storm-track` | `storm_id` 非空 | `TrackResult` | `EndpointTrack` |
| `qwx.v7.astronomy` | `sun` | `GET /v7/astronomy/sun` | `loc` 认坐标或 LocationID；`date` 为 `YYYYMMDD` | `SunResult` | `EndpointSun` |
| `qwx.v7.astronomy` | `moon` | `GET /v7/astronomy/moon` | 同上；`opts: Options(lang)` | `MoonResult` | `EndpointMoon` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `GET /v7/astronomy/solar-elevation-angle` | `loc` 只认坐标；`date`、`time_str`（`HHmm`）、`tz`（如 `0800`）、`alt`（海拔，米，非负） | `AngleResult` | `EndpointAngle` |
| `qwx.v7.historical` | `weather` | `GET /v7/historical/weather` | `loc` 只认 LocationID；`date` 为 `YYYYMMDD`；`opts: Options(lang)` | `Result` | `Endpoint` |

`qwx.v7.indices` 的 `typ` 取 0~16，0 表示全部（`TYPE_ALL`）；`indices_multi` 传多个类型时不能带上 0。`days` 只支持 1 与 3。

`tide`、`indices`、`minutely` 至今只有 v7：实测 `/weather/v1/indices/*`、`/v1/indices/*`、`/ocean/v1/tide/*` 全部 404。

旧一代各端点的结果都带顶层 `refer` 对象（数据来源与许可），与 GeoAPI 同形，取 `Result.refer`。新一代接口没有 `refer`，同样的意思在 `Metadata.attributions` 里。

### 控制台

控制台 API 查的是帐号自己的财务与请求量，不是天气数据。凭据默认没有权限访问：帐号所有者要在控制台的「项目管理 - 凭据 - 控制台权限」里单独开通，否则上游回 403（`qwx.UnauthorizedError`）。

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `GET /finance/v1/summary` | 无 | `FinanceResult` | `EndpointFinance` |
| `qwx.console` | `stats` | `GET /metrics/v1/stats` | `opts: StatsOptions(project, credential)` | `StatsResult` | `EndpointStats` |

`project` 与 `credential` 互斥，都填在客户端被挡下（`qwx.InvalidParameterError`），不打上游。都留空时统计帐号下所有项目与凭据。已删除的项目或凭据无法单独查询，但请求量仍计入汇总。

返回的数据截止至上一个小时或更早，与控制台网页上显示的可能有 1 小时或更长的延迟，以响应里的 `as_of` 为准。

字段形态：

- `balance` 负数表示欠费；`currency` 是货币代码（`CNY`、`USD`）。
- `accrued_charges` 的三个数是应计费用总额：前一天、本月、上次出账以来。
- `pending_bills[].type` 与 `status`、各类计划的 `status` 是枚举，官方会新增，SDK 只透传，不枚举完备列表。
- `available_resource_plans[].requests` 上游的返回样例给的是字符串（`"1000000"`），官方字段表标的是数字。SDK 用联合类型 `int | float | str` 收，两种形态都能解析。
- `as_of`、`pending_bills[].date`、`due_date`、`effective_time` 都是 UTC 时间字符串，原样透传。
- `success` / `errors` 里每一项的 `hours` 是最近 24 小时的逐小时请求量，上游可能给少于 24 条，不要假设长度。

### 字段语义

同一概念在两代里形态不同，取值前先确认落在哪一代。

| 概念 | 新一代 | v7 |
| --- | --- | --- |
| 数值与单位 | 分离：`Value(value, unit)` | 拼在一个字符串里 |
| 降水概率 | 0~1，逐时与逐日预报有，实时天气没有（`None` 区分「没有」与 0） | 无此字段 |
| 降水强度 | `Precipitation.intensity` 可为 `None`：实时天气与逐时预报有，逐日预报没有（`None` 区分「没有」与 0） | 无此字段 |
| 潮位高度 | 无 | `Tide.height` 保持字符串，保留上游精度 |
| 分钟级降水 | 无 | `Minutely.precip` 保持字符串：空串是「无此数据」，`"0.00"` 是「真的没下雨」 |
| 数据来源与许可 | `Metadata.attributions` | `Refer.sources` / `Refer.license`，形状相同 |
| 相对湿度 | 太阳辐射预报是百分数（0~100） | 无此字段 |

统一规则，不要假设：

- 可选字段一律用 `None`，缺失与零值可区分：`Metadata.zero_result`、`Astro`、`Alert.urgency` / `severity` / `certainty`、`Precipitation.probability`、`Precipitation.intensity`。
- 阵风键名按端点分：实时天气与逐时预报是 `wind_gust`，逐日预报的白天/夜间时段是 `wind_gust_max`（`DayNight.wind_gust_max`）。
- 列表长度不假设：`HourlyForecast.hours`、`DailyForecast.days` 上游可能给得更少。
- 枚举会新增，只透传不枚举完备：`Condition.code`、`Alert.event_type.code`、`DailyIndex.type`。
- 时间字符串原样透传：带 `Z` 表示 UTC，传 `local_time=True` 才是当地时间。
- `Place.display_name()` 拼「城市 + 区县」（上游 `name` 是区县、`adm2` 是城市），城市级条目不会拼出重复市名。
