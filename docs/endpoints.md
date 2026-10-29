# 端点索引

一处看全所有端点：Python 模块、方法名、端点常量、上游路径、位置形态、默认 TTL、缓存键前缀与缓存键模板。

表体是生成物，不要手改：

```bash
python tools/gen_endpoints.py         # 写文件
python tools/gen_endpoints.py --check # 只校验漂移
```

数据源是 `contract/endpoints.json` —— 由 `tools/extract_go_contract.py` 从 Go 源码抽取的契约基线，已与 Go 仓库的 `docs/endpoints.md` 逐项对账。Python 侧的端点常量值与默认 TTL 由 `tests/test_endpoints_doc.py` 反向核对这份基线。

端点常量的真源在各端点族的 `types.py`（`qwx.v1.weather.EndpointCurrent`、`qwx.geo.EndpointCity`……）。一个包只导出一个端点时，常量名就是 `Endpoint`（`qwx.v1.alert.Endpoint`、`qwx.v7.ocean.Endpoint`）。常量的**值**发布后不再变更：`qwx.TTLPolicy` 按值匹配，改值会让用户的 TTL 配置静默失效。

端点总数：**26**。

## 端点常量总览

| 端点常量 | 值 | 模块 | 方法 |
| --- | --- | --- | --- |
| `qwx.console.EndpointFinance` | `finance/v1/summary` | `qwx.console` | `finance` |
| `qwx.console.EndpointStats` | `metrics/v1/stats` | `qwx.console` | `stats` |
| `qwx.geo.EndpointCity` | `geo/v2/city/lookup` | `qwx.geo` | `lookup_city` |
| `qwx.geo.EndpointPOI` | `geo/v2/poi/lookup` | `qwx.geo` | `lookup_poi` |
| `qwx.geo.EndpointPOIRange` | `geo/v2/poi/range` | `qwx.geo` | `poi_range` |
| `qwx.geo.EndpointTopCities` | `geo/v2/city/top` | `qwx.geo` | `top_cities` |
| `qwx.v1.airquality.EndpointCurrent` | `airquality/v1/current` | `qwx.v1.airquality` | `current` |
| `qwx.v1.airquality.EndpointDaily` | `airquality/v1/daily` | `qwx.v1.airquality` | `daily` |
| `qwx.v1.airquality.EndpointHourly` | `airquality/v1/hourly` | `qwx.v1.airquality` | `hourly` |
| `qwx.v1.airquality.EndpointStation` | `airquality/v1/stations` | `qwx.v1.airquality` | `station` |
| `qwx.v1.alert.Endpoint` | `weatheralert/v1/current` | `qwx.v1.alert` | `current` |
| `qwx.v1.solarradiation.Endpoint` | `solarradiation/v1/forecast` | `qwx.v1.solarradiation` | `forecast` |
| `qwx.v1.weather.EndpointCurrent` | `weather/v1/current` | `qwx.v1.weather` | `current` |
| `qwx.v1.weather.EndpointHourly` | `weather/v1/hourly` | `qwx.v1.weather` | `hourly` |
| `qwx.v1.weather.EndpointDaily` | `weather/v1/daily` | `qwx.v1.weather` | `daily` |
| `qwx.v7.astronomy.EndpointSun` | `v7/astronomy/sun` | `qwx.v7.astronomy` | `sun` |
| `qwx.v7.astronomy.EndpointMoon` | `v7/astronomy/moon` | `qwx.v7.astronomy` | `moon` |
| `qwx.v7.astronomy.EndpointAngle` | `v7/astronomy/solar-elevation-angle` | `qwx.v7.astronomy` | `solar_elevation_angle` |
| `qwx.v7.historical.Endpoint` | `v7/historical/weather` | `qwx.v7.historical` | `weather` |
| `qwx.v7.indices.Endpoint` | `v7/indices` | `qwx.v7.indices` | `indices`、`indices_multi` |
| `qwx.v7.minutely.Endpoint` | `v7/minutely/5m` | `qwx.v7.minutely` | `minutely` |
| `qwx.v7.ocean.Endpoint` | `v7/ocean/tide` | `qwx.v7.ocean` | `tide` |
| `qwx.v7.storm.EndpointList` | `v7/tropical/storm-list` | `qwx.v7.storm` | `list` |
| `qwx.v7.storm.EndpointForecast` | `v7/tropical/storm-forecast` | `qwx.v7.storm` | `forecast` |
| `qwx.v7.storm.EndpointTrack` | `v7/tropical/storm-track` | `qwx.v7.storm` | `track` |

## 端点方法总表

| 包 | 方法 | 端点常量 | 上游路径 | 位置形态 | 默认 TTL | 缓存键前缀 | 缓存键模板 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwx.console` | `finance` | `qwx.console.EndpointFinance` | `/finance/v1/summary` | 无 | 1 小时 | `qwx:console:` | `qwx:console:finance` |
| `qwx.console` | `stats` | `qwx.console.EndpointStats` | `/metrics/v1/stats` | 无 | 1 小时 | `qwx:console:` | `qwx:console:stats:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.geo` | `lookup_city` | `qwx.geo.EndpointCity` | `/geo/v2/city/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` | `qwx:geo:city:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.geo` | `lookup_poi` | `qwx.geo.EndpointPOI` | `/geo/v2/poi/lookup` | 坐标 / LocationID / 地名 | 24 小时 | `qwx:geo:` | `qwx:geo:poi:{typ}:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.geo` | `poi_range` | `qwx.geo.EndpointPOIRange` | `/geo/v2/poi/range` | 坐标 | 24 小时 | `qwx:geo:` | `qwx:geo:poirange:{typ}:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.geo` | `top_cities` | `qwx.geo.EndpointTopCities` | `/geo/v2/city/top` | 无 | 24 小时 | `qwx:geo:` | `qwx:geo:topcity:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.airquality` | `current` | `qwx.v1.airquality.EndpointCurrent` | `/airquality/v1/current/{lat}/{lon}` | 坐标 | 30 分钟 | `qwx:aq:v1:` | `qwx:aq:v1:current:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.airquality` | `daily` | `qwx.v1.airquality.EndpointDaily` | `/airquality/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` | `qwx:aq:v1:daily:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.airquality` | `hourly` | `qwx.v1.airquality.EndpointHourly` | `/airquality/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:aq:v1:` | `qwx:aq:v1:hourly:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.airquality` | `station` | `qwx.v1.airquality.EndpointStation` | `/airquality/v1/stations/{stationID}` | 站点 ID | 30 分钟 | `qwx:aq:v1:` | `qwx:aq:v1:station:{station_id}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.alert` | `current` | `qwx.v1.alert.Endpoint` | `/weatheralert/v1/current/{lat}/{lon}` | 坐标 | 5 分钟 | `qwx:alert:v1:` | `qwx:alert:v1:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.solarradiation` | `forecast` | `qwx.v1.solarradiation.Endpoint` | `/solarradiation/v1/forecast/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:solarradiation:v1:` | `qwx:solarradiation:v1:forecast:{lat},{lon}:h{hours}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.weather` | `current` | `qwx.v1.weather.EndpointCurrent` | `/weather/v1/current/{lat}/{lon}` | 坐标 | 10 分钟 | `qwx:v1:` | `qwx:v1:current:{lat},{lon}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.weather` | `hourly` | `qwx.v1.weather.EndpointHourly` | `/weather/v1/hourly/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` | `qwx:v1:hourly:{lat},{lon}:h{hours}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v1.weather` | `daily` | `qwx.v1.weather.EndpointDaily` | `/weather/v1/daily/{lat}/{lon}` | 坐标 | 1 小时 | `qwx:v1:` | `qwx:v1:daily:{lat},{lon}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.astronomy` | `sun` | `qwx.v7.astronomy.EndpointSun` | `/v7/astronomy/sun` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` | `qwx:astronomy:sun:{location}:{date}` |
| `qwx.v7.astronomy` | `moon` | `qwx.v7.astronomy.EndpointMoon` | `/v7/astronomy/moon` | 坐标 / LocationID | 24 小时 | `qwx:astronomy:` | `qwx:astronomy:moon:{location}:{date}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx.v7.astronomy.EndpointAngle` | `/v7/astronomy/solar-elevation-angle` | 坐标 | 24 小时 | `qwx:astronomy:` | `qwx:astronomy:angle:{location}:{date}:{time}:{tz}:{alt}` |
| `qwx.v7.historical` | `weather` | `qwx.v7.historical.Endpoint` | `/v7/historical/weather` | LocationID | 24 小时 | `qwx:historical:` | `qwx:historical:weather:{id}:{date}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.indices` | `indices` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` | `qwx:indices:{location}:t{type}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.indices` | `indices_multi` | `qwx.v7.indices.Endpoint` | `/v7/indices/{days}d` | 坐标 | 1 小时 | `qwx:indices:` | `qwx:indices:{location}:t{type}:d{days}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.minutely` | `minutely` | `qwx.v7.minutely.Endpoint` | `/v7/minutely/5m` | 坐标 | 5 分钟 | `qwx:minutely:` | `qwx:minutely:{location}:lang={lang}:localTime=1:n={n}:r={r}:adm={adm}:range={range}:city={city}:interval={interval}:tilt={tilt}:azimuth={azimuth}:extra={extra}:project={project}:credential={credential}` |
| `qwx.v7.ocean` | `tide` | `qwx.v7.ocean.Endpoint` | `/v7/ocean/tide` | 站点 ID | 1 小时 | `qwx:tide:` | `qwx:tide:{station_id}:{date}` |
| `qwx.v7.storm` | `list` | `qwx.v7.storm.EndpointList` | `/v7/tropical/storm-list` | 无 | 24 小时 | `qwx:storm:` | `qwx:storm:list:{basin}:{year}` |
| `qwx.v7.storm` | `forecast` | `qwx.v7.storm.EndpointForecast` | `/v7/tropical/storm-forecast` | 无 | 1 小时 | `qwx:storm:` | `qwx:storm:forecast:{storm_id}` |
| `qwx.v7.storm` | `track` | `qwx.v7.storm.EndpointTrack` | `/v7/tropical/storm-track` | 无 | 1 小时 | `qwx:storm:` | `qwx:storm:track:{storm_id}` |

## 位置形态

位置形态决定调用方怎么传位置。形态互不等价，传错的上游直接拒绝：

| 形态 | 怎么构造 | 谁认 |
| --- | --- | --- |
| 坐标对 | `qwx.Location(lat=39.92, lon=116.41)` 或 `qwx.parse_location("116.41,39.92")` | 新一代全部端点；v7 的生活指数、分钟级降水、太阳高度角 |
| 坐标对 / LocationID | `qwx.Location(id="101010100")` | 天文的日出日落与月相 |
| 坐标对 / LocationID / 地名 | `qwx.Location(name="杭州")` | GeoAPI 的城市检索与 POI 检索 |
| 站点 ID | `qwx.Location(id="P2352")` | 潮汐、空气质量监测站 |

新一代的路径参数是**纬度在前**，v7 与 GeoAPI 的查询参数是**经度在前**。

每个端点认哪种形态见上面的方法总表。参数上限、返回类型、字段单位见 [contract.md](contract.md)；上游的怪癖见 [gotchas.md](gotchas.md)。

## 缓存时长

默认时长由端点包内置，用户用 `qwx.TTLPolicy` 按端点覆盖：

```python
from datetime import timedelta

import qwx
from qwx.v1.airquality import EndpointCurrent as AQCurrent
from qwx.v1.weather import EndpointCurrent

policy = qwx.TTLMap({
    EndpointCurrent: timedelta(seconds=30),
    AQCurrent: timedelta(0),  # 该端点不缓存
})
client = qwx.Client(auth, "abcxyz.qweatherapi.com", ttl_policy=policy)
```

优先级：单次上下文覆盖（`qwx.override_ttl`） > `TTLPolicy` > 端点默认时长。TTL 与缓存键是两回事：改 TTL 不会让已写入的旧条目提前失效。

## 加新端点时

- 端点常量放进所属资源族的 `types.py`：包里有多个端点时命名 `EndpointFoo`，只有一个时命名 `Endpoint`。
- 在 `client.py` 构造的 `qwx.Request` 里填上 `endpoint` 与 `ttl`，用户才能按端点调 TTL。
- 缓存键在 `qwx/_cachekey.py` 里拼：选一个 `Family`，用 `Params` 声明影响结果的参数，不要自己拼 `:lang=` 这类字符串。
- 跑 `python tools/gen_endpoints.py` 更新本文件的表体。
- 同步 [contract.md](contract.md) 的端点表、[caching.md](caching.md) 的键表与 TTL 表、README 的「支持的接口」表。
