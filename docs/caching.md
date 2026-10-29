# 缓存

## 接口约定

```python
from datetime import timedelta
from typing import Protocol


class Cache(Protocol):
    def get(self, key: str) -> bytes | None: ...
    def set(self, key: str, data: bytes, ttl: timedelta) -> None: ...
```

- 命中返回 `bytes`，未命中返回 `None`。
- 读写失败抛异常。SDK 会吞掉缓存错误并降级为直连上游，实现方可以放心抛错。
- `ttl` 是相对时长。

内置 `qwx.MemoryCache`：进程内、带锁，**不建议用于生产环境**。它没有后台清理 —— 过期条目只在被 `get` 命中时顺手删除，没被再次访问的过期条目会一直留在字典里，长跑进程的内存占用只增不减。它只适合测试替身与单实例的临时缓存；生产环境用 Redis 等共享缓存，多实例部署也需要共享缓存，否则命中率被摊薄。

接入：

```python
import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=qwx.MemoryCache())
```

## Redis 实现

Redis 适配是可选依赖，装 extra：

```bash
pip install "qwx[redis]"
```

```python
import qwx
from qwx.redis_cache import RedisCache

# 用 URL 构造
cache = RedisCache.from_url("redis://127.0.0.1:6379/0")

# 或复用已有的 redis-py 客户端（连接池、超时、TLS 都由调用方控制）
import redis

cache = RedisCache(redis.Redis(host="127.0.0.1", port=6379, db=0))

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

要点：

- 构造时**不连 Redis**，连接在第一次读写时建立。地址写错要等第一次读写才暴露。
- `from_url` 需要装了 redis-py，没装时抛 `ImportError`；`RedisCache(client)` 接受任何有 `get` / `set` 方法的对象。
- `set` 的 `ttl` 是相对时长，换算成 Redis 的 `ex=`（整数秒，向上取整，不足 1 秒按 1 秒算）。ttl 非正数抛 `qwx.InvalidParameterError` 且不写入 —— 不带过期时间的天气数据会一直是旧的。
- 缓存值存**原始 JSON bytes**，与 Go 版共享同一个 Redis 时键和值都互通：Python 写入的条目 Go 版能读，反之亦然。
- 不要给客户端开 `decode_responses=True`：值按 bytes 存取，开了之后与 Go 版不再互通。
- 缓存错误照旧被 SDK 吞掉并降级为直连上游，Redis 挂了不影响接口可用性。

## 键

键由 SDK 生成，带代际前缀，两代不共键，旧缓存不会被新解析器读到。

| 模块 | 方法 | 键 |
| --- | --- | --- |
| `qwx.v1.weather` | `current` | `qwx:v1:current:<lat>,<lon>` + 后缀 |
| `qwx.v1.weather` | `hourly` | `qwx:v1:hourly:<lat>,<lon>:h<hours>` + 后缀 |
| `qwx.v1.weather` | `daily` | `qwx:v1:daily:<lat>,<lon>:d<days>` + 后缀 |
| `qwx.v1.airquality` | `current` | `qwx:aq:v1:current:<lat>,<lon>` + 后缀 |
| `qwx.v1.airquality` | `daily` | `qwx:aq:v1:daily:<lat>,<lon>` + 后缀 |
| `qwx.v1.airquality` | `hourly` | `qwx:aq:v1:hourly:<lat>,<lon>` + 后缀 |
| `qwx.v1.airquality` | `station` | `qwx:aq:v1:station:<station_id>` + 后缀 |
| `qwx.v1.alert` | `current` | `qwx:alert:v1:<lat>,<lon>` + 后缀 |
| `qwx.v1.solarradiation` | `forecast` | `qwx:solarradiation:v1:forecast:<lat>,<lon>:h<hours>` + 后缀 |
| `qwx.geo` | `lookup_city` | `qwx:geo:city:<location>` + 后缀 |
| `qwx.geo` | `lookup_poi` | `qwx:geo:poi:<typ>:<location>` + 后缀 |
| `qwx.geo` | `poi_range` | `qwx:geo:poirange:<typ>:<location>` + 后缀（含半径 `:r=<radius>`） |
| `qwx.geo` | `top_cities` | `qwx:geo:topcity` + 后缀 |
| `qwx.console` | `finance` | `qwx:console:finance` |
| `qwx.console` | `stats` | `qwx:console:stats` + 后缀 |
| `qwx.v7.ocean` | `tide` | `qwx:tide:<station_id>:<date>` |
| `qwx.v7.indices` | `indices` | `qwx:indices:<location>:t<type>:d<days>` + 后缀 |
| `qwx.v7.indices` | `indices_multi` | `qwx:indices:<location>:t<types>:d<days>` + 后缀 |
| `qwx.v7.minutely` | `minutely` | `qwx:minutely:<location>` + 后缀 |
| `qwx.v7.storm` | `list` | `qwx:storm:list:<basin>:<year>` |
| `qwx.v7.storm` | `forecast` | `qwx:storm:forecast:<storm_id>` |
| `qwx.v7.storm` | `track` | `qwx:storm:track:<storm_id>` |
| `qwx.v7.astronomy` | `sun` | `qwx:astronomy:sun:<location>:<date>` |
| `qwx.v7.astronomy` | `moon` | `qwx:astronomy:moon:<location>:<date>` + 后缀 |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `qwx:astronomy:angle:<location>:<date>:<time>:<tz>:<alt>` |
| `qwx.v7.historical` | `weather` | `qwx:historical:weather:<id>:<date>` + 后缀 |

键字面量在已发布版本里定死，改动会让已写入的缓存条目全部失效。`qwx.v7.ocean` 的键前缀是 `qwx:tide:` 而不是 `qwx:ocean:` —— 与模块名不对齐是有意为之，不要「顺手修正」。

后缀承载影响结果的查询参数：语言 `:lang=<lang>`、新一代本地时间 `:localTime=1`、条数 `:n=<number>`、半径 `:r=<radius>`、行政区划 `:adm=<adm>`、搜索范围 `:range=<range>`、限定城市 `:city=<city>`、时间间隔 `:interval=<n>`、倾斜角 `:tilt=<n>`、方位角 `:azimuth=<n>`、额外信息 `:extra=<extra>`、项目 `:project=<project>`、凭据 `:credential=<credential>`。坐标统一两位小数，`-0` 归一为 `0.00`。

语言段进的是 API 代码（`:lang=zh`），不是语言名 —— `qwx.Lang` 的 `api` 字段。换语言就是换一份数据，键必须跟着变。

后缀顺序固定：语言 → 本地时间 → 条数 → 半径 → 行政区划 → 搜索范围 → 城市 → 时间间隔 → 倾斜角 → 方位角 → 额外信息 → 项目 → 凭据。新加的参数一律追加在末尾，老调用方不设它们，键的字节与发布时完全一致。

键不含 API Host：不同 Host 对应不同开发者账号，一个 Cache 实例不要跨账号共用，否则会串味。

### 键怎么拼

拼法只有一处：`src/qwx/_cachekey.py`。端点模块不自己拼字符串，只声明两件事 —— 自己属于哪个族、有哪些影响结果的参数。

| 族常量 | 前缀根 | 模块 |
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

形状固定：族前缀 + 位置段 + 参数段。

- 位置段按追加顺序拼接：端点名、坐标、站点 ID、地点 ID、计数段（`:h24`）。
- 坐标段由 `_cachekey` 格式化：两位小数，`-0` 归一为 `0.00`。新一代是纬度在前（`path_coord`）；旧一代与 GeoAPI 的位置段用 `Location.query()`，经度在前。
- 参数段固定排在最后，顺序是语言 → 本地时间 → 条数 → 半径 → 行政区划 → 搜索范围 → 城市 → 时间间隔 → 倾斜角 → 方位角 → 额外信息 → 项目 → 凭据。

影响结果的查询参数用同一个 `qwx._cachekey.Params` 声明：它同时生成上游查询串与键的后缀。新增参数只改这一处，参数漏进键不会发生。

```python
# src/qwx/v1/weather/client.py
def _params(opts: Options) -> Params:
    return Params(lang=opts.lang.api, local_time=opts.local_time)
```

半径用 `None` 表示「端点没有半径参数」；半径为 0 时只进键、不发给上游（上游按自己的默认值处理）。

倾斜角与方位角也用 `None` 表示「不传」，0 是合法取值（非 `None` 时要连 0 一起发给上游）。

## TTL

| 端点 | 端点常量 | 默认 TTL | 依据 |
| --- | --- | --- | --- |
| 天气实况 | `qwx.v1.weather.EndpointCurrent` | 10 分钟 | 上游更新节奏 |
| 逐时 / 逐日预报 | `qwx.v1.weather.EndpointHourly` / `EndpointDaily` | 1 小时 | 同上 |
| 空气质量实况 | `qwx.v1.airquality.EndpointCurrent` | 30 分钟 | 上游逐小时更新 |
| 空气质量预报 | `qwx.v1.airquality.EndpointDaily` / `EndpointHourly` | 1 小时 | 同上 |
| 监测站 | `qwx.v1.airquality.EndpointStation` | 30 分钟 | 同上 |
| 预警 | `qwx.v1.alert.Endpoint` | 5 分钟 | 上游 5 分钟更新 |
| 分钟级降水 | `qwx.v7.minutely.Endpoint` | 5 分钟 | 上游 5 分钟更新 |
| 潮汐 / 生活指数 | `qwx.v7.ocean.Endpoint` / `qwx.v7.indices.Endpoint` | 1 小时 | 数据更新节奏 |
| 太阳辐射预报 | `qwx.v1.solarradiation.Endpoint` | 1 小时 | 上游逐 15 分钟更新预报 |
| 台风列表 | `qwx.v7.storm.EndpointList` | 24 小时 | 列表一天内基本不变 |
| 台风预报 / 路径 | `qwx.v7.storm.EndpointForecast` / `EndpointTrack` | 1 小时 | 上游几小时更新一次 |
| 天文 | `qwx.v7.astronomy.EndpointSun` 等三个 | 24 小时 | 数据按日期固定，一天内不变 |
| 历史天气 | `qwx.v7.historical.Endpoint` | 24 小时 | 数据按日期固定，过去之后不再变 |
| GeoAPI | `qwx.geo.EndpointCity` 等四个 | 24 小时 | 地理信息几乎不变 |
| 控制台 | `qwx.console.EndpointFinance` / `EndpointStats` | 1 小时 | 上游数据截止至上一个小时或更早 |

### 自定义 TTL

默认时长由端点模块决定，需要调整时传一份 `ttl_policy`：

```python
from datetime import timedelta

import qwx
from qwx.v1.airquality import EndpointCurrent as AQCurrent
from qwx.v1.weather import EndpointCurrent

client = qwx.Client(
    auth,
    "abcxyz.qweatherapi.com",
    cache=cache,
    ttl_policy=qwx.TTLMap({
        EndpointCurrent: timedelta(seconds=30),
        AQCurrent: timedelta(0),  # 该端点不缓存
    }),
)
```

`qwx.TTLMap` 是最常用的形态：键是端点常量，值是缓存时长。键不存在时沿用端点默认时长，值为 0 表示该端点不缓存。

需要按时间或负载动态调整时用 `qwx.TTLPolicyFunc`：

```python
policy = qwx.TTLPolicyFunc(
    lambda endpoint, default: timedelta(seconds=10)
    if endpoint == EndpointCurrent
    else default
)
```

`default` 是端点模块内置的默认时长，策略对它没有意见时原样返回即可。策略在每次请求时求值，实现方要保证并发安全。

单次请求要临时绕过缓存，用上下文覆盖，不用改任何端点签名：

```python
with client.override_ttl(timedelta(0)):  # 这一次不读也不写缓存
    weather.current(loc)
```

覆盖优先级高于策略与端点默认时长。覆盖用 `contextvars` 实现，同步与异步都适用，异步任务之间不会互相串。

时长解析顺序：单次上下文覆盖 > `TTLPolicy` > 端点模块内置默认时长。

端点为空（外部代码直接构造 `qwx.Request` 而没填 `endpoint`）的请求不参与策略匹配，策略不会被调用，缓存时长只由 `Request.ttl` 决定。

### TTL 与缓存键

改 TTL 不改缓存键。已写入的旧条目按写入时的 TTL 到期，调小策略不会让它们提前失效。想立刻生效要换缓存实例或手动清键。

## 加新端点时

- TTL 取上游更新节奏，留一半余量。
- 导出端点常量放进该族的 `types.py`，并在 `Request` 里填上 `endpoint`，用户才能按端点调 TTL。族里有多个端点时命名为 `EndpointFoo`，只有一个时命名为 `Endpoint`。
- 键包含所有影响结果的参数：路径参数与查询参数都要进键，漏一个就是一次缓存串味。
- 键在 `src/qwx/_cachekey.py` 里拼：选一个族常量，用 `Params` 声明影响结果的参数，不要自己拼 `:lang=` 这类字符串。
- 前缀按代分：`qwx:v1:` / `qwx:aq:v1:` / `qwx:alert:v1:` / `qwx:solarradiation:v1:` 给新一代，`qwx:geo:` / `qwx:tide:` / `qwx:indices:` / `qwx:minutely:` / `qwx:storm:` / `qwx:astronomy:` / `qwx:historical:` 给旧一代与 GeoAPI，`qwx:console:` 给控制台。新增族要在 `_cachekey.py` 里加族常量，并更新键表。
- 端点放在所属资源族的子模块里，键与 TTL 由该族自己定，不要回流到根包。
