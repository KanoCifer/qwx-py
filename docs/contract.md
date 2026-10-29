# 端点契约

写调用代码前查这里：端点要传什么、返回什么、边界在哪。位置形态与单位的第一性解释见仓库根目录 `AGENTS.md` 的词汇表。

端点按上游代际分属不同模块，方法挂在各自的服务客户端上：

| 模块 | 服务客户端（同步 / 异步） | 覆盖 |
| --- | --- | --- |
| `qwx.v1` | —— | 新一代跨端点族共用的基础类型（`Metadata`、`Value`、`Options`） |
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

一个模块 = 一个上游资源族。`qwx.geo` 是唯一的例外：它的四个检索端点共享同一个地点类型，拆开会让该类型失去归属。

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

端点常量用于按端点调缓存时长，见 `caching.md` 的「自定义 TTL」。

## 位置形态

`Location` 有三种形态，同一个端点接受的子集不同。

| 形态 | 构造 | 谁认 |
| --- | --- | --- |
| 坐标对 | `qwx.Location(lat=39.92, lon=116.41)` 或 `qwx.parse_location("116.41,39.92")` | 除控制台、台风、热门城市外的端点 |
| LocationID | `qwx.Location(id="101010100")` | GeoAPI；天文的日出日落与月相；历史天气。行政区划是 9~10 位数字，POI 是数字加字母后缀，潮汐站是 `P` 加数字 |
| 地名 | `qwx.Location(name="杭州")` | 仅 `GeoService.lookup_city` / `GeoService.lookup_poi` |

坐标在 SDK 内保留两位小数，`-0` 归一为 `0.00`。`qwx.parse_location` 拒绝空串、非数字、NaN/Inf、超范围经纬度，返回 `qwx.InvalidLocationError`。

已知边界：坐标恰为 `(0, 0)` 时 `has_coordinates()` 为 false，会被当作无坐标。

## 语言

上游用 `lang` 查询参数切换返回的语言。各端点的语言参数都是 `qwx.Lang`（`qwx.v7.indices` 与 `qwx.v7.minutely` 是形参，其余在 `Options` 里）。

- 语言代码取自官方「多语言」页，SDK 内置 31 种：`qwx.Lang.ZH`、`qwx.Lang.ZH_HANT`、`qwx.Lang.EN` …… 完整列表在 `qwx.LANGS`。
- 留空（`qwx.Lang.UNSPECIFIED`）不传 `lang`，用上游默认：所在国家或地区的官方语言，没有官方语言时回退到英语。官方数据不支持指定语言时，回退顺序是指定语言 > 官方语言 > 英语。
- 官方给的等价代码（简体中文的 `zh-hans`）用 `qwx.lookup_lang` 查得到，发出去的仍是首选代码 `zh`。
- 语言代码形态不对时返回 `qwx.InvalidParameterError`，不打上游。
- 认语言参数的端点：新一代天气（`current`/`hourly`/`daily`）、空气质量（`current`/`daily`/`hourly`/`station`）、预警（`current`）、GeoAPI 四个检索端点、旧一代生活指数与分钟级降水、月相（`moon`）、历史天气。
  监测站数据有独立文档页（`/docs/api/air-quality/air-station/`），明确带 `lang` 参数。
- 不认语言参数的端点：太阳辐射预报、潮汐、台风三个端点、日出日落与太阳高度角、控制台两个端点 —— 上游没有这个参数，多传会被拒，SDK 也不暴露。
- 缓存键里带的是 API 代码（`:lang=zh`）：语言不同是不同的数据，不共键。

## 新一代（只认坐标）

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

## GeoAPI（认坐标 / LocationID / 地名）

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.geo` | `lookup_city` | `GET /geo/v2/city/lookup` | `loc` 三形态皆可；`opts: Options(lang, number, adm, range)` | `CityResult` | `EndpointCity` |
| `qwx.geo` | `lookup_poi` | `GET /geo/v2/poi/lookup` | `loc` 三形态皆可；`typ` ∈ `POIType.SCENIC` / `POIType.CSTA` / `POIType.TSTA`；`opts: Options(lang, number, city)` | `POIResult` | `EndpointPOI` |
| `qwx.geo` | `poi_range` | `GET /geo/v2/poi/range` | `loc` 只认坐标；`typ`；`opts: POIRangeOptions(lang, number, radius)` | `RangeResult` | `EndpointPOIRange` |
| `qwx.geo` | `top_cities` | `GET /geo/v2/city/top` | `opts: Options(lang, number, range)` | `TopCityResult` | `EndpointTopCities` |

`number` 为 0 时走上游默认（10），`radius` 为 0 时走默认（5）。

`adm`、`range`、`city` 是 `Options` 上的可选参数，各端点只上报自己认的那几个：
`adm` 与 `range` 只有城市检索认，`city` 只有 POI 检索认，`range` 热门城市也认。
`adm` 传上级行政区划的 LocationID（如 `101010100`），`range` 传 ISO 3166 国家代码
（如 `cn`、`world`），`city` 传城市名或 LocationID。三个参数都影响结果，都进缓存键。

`typ` 必填，取值是闭集：传闭集外的类型抛 `qwx.InvalidParameterError`，不打上游。

## 旧一代 v7

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

旧一代各端点的结果都带顶层 `refer` 对象（数据来源与许可），与 GeoAPI 同形，取
`Result.refer`。新一代接口没有 `refer` —— 同样的意思在 `Metadata.attributions` 里。

## 控制台

控制台 API 查的是帐号自己的财务与请求量，不是天气数据。凭据默认没有权限
访问：帐号所有者要在控制台的「项目管理 - 凭据 - 控制台权限」里单独开通，
否则上游回 403（`qwx.UnauthorizedError`）。

| 模块 | 方法 | 上游路径 | 参数 | 返回 | 端点常量 |
| --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `GET /finance/v1/summary` | 无 | `FinanceResult` | `EndpointFinance` |
| `qwx.console` | `stats` | `GET /metrics/v1/stats` | `opts: StatsOptions(project, credential)` | `StatsResult` | `EndpointStats` |

`project` 与 `credential` 互斥，都填在客户端被挡下（`qwx.InvalidParameterError`），
不打上游。都留空时统计帐号下所有项目与凭据 —— 已删除的项目或凭据无法单独
查询，但请求量仍计入汇总。

返回的数据截止至上一个小时或更早，与控制台网页上显示的可能有 1 小时或更长
的延迟，以响应里的 `as_of` 为准。

字段形态：

- `balance` 负数表示欠费；`currency` 是货币代码（`CNY`、`USD`）。
- `accrued_charges` 的三个数是应计费用总额：前一天、本月、上次出账以来。
- `pending_bills[].type` 与 `status`、各类计划的 `status` 是枚举，官方会新增，
  SDK 只透传，不枚举完备列表。
- `available_resource_plans[].requests` 上游的返回样例给的是字符串（`"1000000"`），
  官方字段表标的是数字 —— SDK 用联合类型 `int | float | str` 收，两种形态都能解析。
- `as_of`、`pending_bills[].date`、`due_date`、`effective_time` 都是 UTC 时间字符串，
  原样透传。
- `success` / `errors` 里每一项的 `hours` 是最近 24 小时的逐小时请求量，
  上游可能给少于 24 条，不要假设长度。

## 上游有但 qwx 未覆盖

上游还有这些端点，本库没接。它们分两类：**已定停服日**的不要再写，**仍活着**
的可以按需补。

| 上游路径 | 状态 | 说明 |
| --- | --- | --- |
| `/v7/warning/now` | 2026-09-01 停服 | 用 `qwx.v1.alert` |
| `/v7/air/now` | 2026-06-01 停服 | 用 `qwx.v1.airquality` |
| `/v7/air/5d` | 2026-06-01 停服 | 用 `qwx.v1.airquality` |
| `/v7/solar-radiation/{hours}` | 2026-12-31 停服 | 用 `qwx.v1.solarradiation` |
| `/v7/grid-weather/now` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/grid-weather/{days}` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/grid-weather/{hours}` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/weather/now` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/weather/{days}` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/weather/{hours}` | 2027-02-01 停服 | 用 `qwx.v1.weather` |
| `/v7/historical/air` | 已弃用 | 无替代 |

本库支持的 `/v7/minutely/5m`、`/v7/indices/{days}`、`/v7/ocean/tide`、
`/v7/historical/weather` 都不在停服名单里，可以继续用。

## 字段语义

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

统一规则（不要假设）：

- 可选字段一律用 `None`，缺失与零值可区分：`Metadata.zero_result`、`Astro`、`Alert.urgency` / `severity` / `certainty`、`Precipitation.probability`、`Precipitation.intensity`。
- 阵风键名按端点分：实时天气与逐时预报是 `wind_gust`，逐日预报的白天/夜间时段是 `wind_gust_max`（`DayNight.wind_gust_max`）。
- 列表长度不假设：`HourlyForecast.hours`、`DailyForecast.days` 上游可能给得更少。
- 枚举会新增，只透传不枚举完备：`Condition.code`、`Alert.event_type.code`、`DailyIndex.type`。
- 时间字符串原样透传：带 `Z` 表示 UTC，传 `local_time=True` 才是当地时间。
- `Place.display_name()` 拼「城市 + 区县」（上游 `name` 是区县、`adm2` 是城市），城市级条目不会拼出重复市名。
