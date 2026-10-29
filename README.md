<p align="center">
  <img src="https://raw.githubusercontent.com/KanoCifer/qwx-py/main/assets/banner.png" width="100%" alt="qwx" />
</p>

<p align="center">
  <a href="https://github.com/KanoCifer/qwx-py/actions/workflows/ci.yml" target="_blank" rel="noopener"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/KanoCifer/qwx-py/ci.yml?branch=main" height="20"></a>
  <a href="https://pypi.org/project/qwx/" target="_blank" rel="noopener"><img alt="PyPI" src="https://img.shields.io/pypi/v/qwx" height="20"></a>
  <a href="https://pypi.org/project/qwx/" target="_blank" rel="noopener"><img alt="Python" src="https://img.shields.io/pypi/pyversions/qwx" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py/blob/main/LICENSE" target="_blank" rel="noopener"><img alt="License" src="https://img.shields.io/github/license/KanoCifer/qwx-py" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py#endpoints" target="_blank" rel="noopener"><img alt="端点数" src="https://img.shields.io/badge/%E7%AB%AF%E7%82%B9-26%20%E4%B8%AA-blue" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx-py#endpoints" target="_blank" rel="noopener"><img alt="模型" src="https://img.shields.io/badge/%E6%A8%A1%E5%9E%8B-pydantic%20v2-success" height="20"></a>
  <a href="https://github.com/KanoCifer/qwx" target="_blank" rel="noopener"><img alt="Go 版" src="https://img.shields.io/badge/Go-%E5%8F%82%E8%80%83-00ADD8?logo=go&logoColor=white" height="20"></a>
</p>

<p align="center">
  <a href="README.md"><b>简体中文</b></a> · <a href="README_EN.md">English</a>
</p>

qwx 是社区维护的 Python SDK，覆盖和风天气（QWeather）上游文档里的核心接口族，返回 pydantic v2 模型。

与 Go 版（[KanoCifer/qwx](https://github.com/KanoCifer/qwx)）语义对等：端点集合、缓存键字节、端点常量的值、错误分类、TTL 优先级全部一致，两边共用同一个 Redis 时键和值互通。

---

<details>
<summary><b>📖 目录</b></summary>

- [✨ 特性](#features)
- [📦 安装](#installation)
- [🚀 快速开始](#quick-start)
- [📖 使用指南](#guide)
  - [🔑 认证](#authentication)
  - [⚙️ 客户端选项](#client-options)
  - [📍 位置](#location)
  - [🌐 语言](#lang)
  - [🗄️ 缓存与 TTL](#caching)
  - [📝 日志](#logging)
  - [🚨 错误处理](#errors)
  - [⏱️ 并发与超时](#concurrency)
  - [🧪 测试与验证](#verification)
- [🔌 支持的接口](#endpoints)
- [📋 端点契约](#contract)
- [🔗 官方文档](#upstream-docs)
- [⚖️ 许可](#license)

</details>

---

<a id="features"></a>
## ✨ 特性

- **26 个端点**，覆盖天气、空气质量、预警、太阳辐射、GeoAPI、控制台、天文、历史天气、生活指数、分钟级降水、台风、潮汐十二个资源族。
- **同步与异步双栈**（httpx），端点方法体只写一份：同步客户端返回模型，异步客户端返回协程。
- **pydantic v2 模型**，上游新增的字段不会被丢弃，未知字段留在 `model_extra` 里。
- **缓存键与 Go 版逐字相同**，键字面量是已发布事实，改了会让已写入的条目全部失效。
- **客户端先校验**，参数越界与位置形态非法在本地抛异常，不打上游。
- **错误分层**，按异常类型判断，不解析错误字符串。

---

<a id="installation"></a>
## 📦 安装

```bash
pip install qwx
```

要求 Python 3.10 及以上，依赖 `httpx`、`pydantic`、`cryptography`（JWT 签名）。

需要 Redis 缓存时装可选 extra：

```bash
pip install "qwx[redis]"
```

从源码装：

```bash
git clone https://github.com/KanoCifer/qwx-py.git
cd qwx-py
pip install -e ".[dev]"
```

---

<a id="quick-start"></a>
## 🚀 快速开始

三步：创建认证、创建基础客户端、创建接口族的客户端。

### 同步

```python
import qwx
from qwx.v1.weather import WeatherService

# 1. 认证。JWT 用控制台分配的凭据，API KEY 用 qwx.APIKeyAuth。
auth = qwx.JWTAuth(
    private_key_pem=open("ed25519-private.pem", encoding="utf-8").read(),
    key_id="YOUR_KEY_ID",
    project_id="YOUR_PROJECT_ID",
    developer_id="YOUR_DEVELOPER_ID",  # 必填，控制台「设置」页
)

# 2. 基础客户端。api_host 是控制台「设置」页分配的专属 Host，必填。
with qwx.Client(auth, "abcxyz.qweatherapi.com") as client:
    # 3. 接口族的客户端。
    weather = WeatherService(client)
    result = weather.current(qwx.Location(lat=39.92, lon=116.41))
    print(result.condition.text, result.temperature.value, result.temperature.unit)
```

`Client` 是上下文管理器，`with` 退出时关闭底层 HTTP 连接。不用上下文管理时自己调 `client.close()`。

### 异步

异步版方法同名，返回协程：

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

### 可运行示例

`examples/` 下有四个脚本，读环境变量后直接跑：

| 脚本 | 内容 |
| --- | --- |
| `examples/basic_sync.py` | API KEY 认证，取实时天气 |
| `examples/basic_async.py` | 异步版 |
| `examples/jwt_auth.py` | JWT 认证 |
| `examples/cache_redis.py` | 接 Redis 缓存 |

```bash
QWX_API_KEY=YOUR_API_KEY QWX_API_HOST=your-host.qweatherapi.com python examples/basic_sync.py
```

---
<a id="guide"></a>
## 📖 使用指南

<a id="authentication"></a>
### 🔑 认证

两种认证任选其一，不能同时使用，一起带上会被上游拒。新项目默认选 JWT。

| 方式 | 构造 | 请求头 | 适用 |
| --- | --- | --- | --- |
| `qwx.JWTAuth` | `qwx.JWTAuth(private_key_pem=..., key_id=..., project_id=..., developer_id=...)` | `Authorization: Bearer <JWT>` | 新项目默认 |
| `qwx.APIKeyAuth` | `qwx.APIKeyAuth(key)` | `X-QW-Api-Key: <key>` | 存量项目 |

API KEY 已被官方公告限量：2027-01-01 起限制每日请求量，SDK 5+ 不再支持。

#### JWT

控制台生成三项凭据：Key ID（进 JWT header 的 `kid`）、Project ID（进 payload 的 `sub`）、Developer ID（进 payload 的 `iss`）。私钥是 Ed25519 PKCS#8 PEM，公钥上传控制台。

Developer ID 必填，缺失时 `qwx.JWTAuth` 抛 `qwx.InvalidConfigError`。官方口径是 `iss` 为签发者，上游按它校验凭据归属，值在控制台「设置」页查看（Q 开头的 10 位字母数字）。

```bash
openssl genpkey -algorithm ED25519 -out ed25519-private.pem
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
```

`qwx.JWTAuth` 只接受关键字参数，四项凭据缺任一项抛 `qwx.InvalidConfigError`：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `private_key_pem` | 是 | Ed25519 PKCS#8 PEM 文本 |
| `key_id` | 是 | 控制台的 Key ID，进 JWT header 的 `kid` |
| `project_id` | 是 | 控制台的 Project ID，进 payload 的 `sub` |
| `developer_id` | 是 | 控制台的 Developer ID，进 payload 的 `iss` |
| `token_ttl` | 否 | token 有效期，默认 `timedelta(minutes=15)` |

签名口径，实现见 `src/qwx/auth.py`：

- header `alg=EdDSA`、`kid=key_id`；payload `iss=developer_id`、`sub=project_id`、`iat`、`exp=iat+token_ttl`（默认 15 分钟）。
- `iat` 回退 30 秒，容忍时钟偏差。
- token 在过期前 1 分钟自动重签，调用方无感；签名有锁，并发安全。
- PEM 接受含 `\n` 转义的字符串（环境变量常见写法）；非 PKCS#8 或非 Ed25519 抛 `qwx.InvalidConfigError`。


```python
auth = qwx.JWTAuth(
    private_key_pem=pem,
    key_id="你的 Key ID",
    project_id="你的 Project ID",
    developer_id="你的 Developer ID",
)
```

#### API KEY

```python
import qwx

auth = qwx.APIKeyAuth("你的 API KEY")
```

空 key 抛 `qwx.InvalidConfigError`。

#### 专属 API Host

控制台「设置」页会分配专属 API Host（形如 `abcxyz.qweatherapi.com`），它是必填项：`qwx.Client(auth, host)`。公共域名 `devapi.qweather.com`、`api.qweather.com`、`geoapi.qweather.com` 自 2026 年起陆续停服，SDK 不再内置默认值。

只给 host 时自动补 `https://`；带 scheme 时按给的来。Host 是身份认证的一部分，凭据与 Host 不匹配上游会拒。

#### 认证失败排查

401/403 归为 `qwx.UnauthorizedError`，见[错误处理](#errors)。排查顺序：

1. `kid` 与控制台的 Key ID 一致。
2. `sub` 是 Project ID，不是 Developer ID。
3. `iss` 是 Developer ID，取自控制台「设置」页，不是凭据 ID。
4. 私钥与上传到控制台的公钥是同一对。
5. 凭据、Developer ID 与 API Host 属于同一个开发者账号。

<a id="client-options"></a>
### ⚙️ 客户端选项

```python
client = qwx.Client(
    auth,
    "abcxyz.qweatherapi.com",
    timeout=30.0,  # 单请求超时（秒）
    cache=cache,  # 缓存实现，默认 None
    ttl_policy=policy,  # 按端点决定缓存时长
    logger=logger,  # 标准库 logging 的 logger
    http_client=httpx.Client(...),  # 自定义 httpx 客户端
)
```

`api_host` 没有默认值，公共域名已陆续停服，必须用控制台「设置」页分配的专属 Host。

<a id="location"></a>
### 📍 位置

`Location` 有三种形态，同一个端点接受的子集不同。形态互不等价，传错的上游直接拒绝。

| 形态 | 构造 | 谁认 |
| --- | --- | --- |
| 坐标对 | `qwx.Location(lat=39.92, lon=116.41)` 或 `qwx.parse_location("116.41,39.92")` | 除控制台、台风、热门城市外的端点 |
| LocationID | `qwx.Location(id="101010100")` | GeoAPI；天文的日出日落与月相；历史天气。行政区划是 9~10 位数字，POI 是数字加字母后缀，潮汐站是 `P` 加数字 |
| 地名 | `qwx.Location(name="杭州")` | 仅 `GeoService.lookup_city` / `GeoService.lookup_poi` |

坐标在 SDK 内保留两位小数，`-0` 归一为 `0.00`。`qwx.parse_location` 拒绝空串、非数字、NaN/Inf、超范围经纬度，返回 `qwx.InvalidLocationError`。

已知边界：坐标恰为 `(0, 0)` 时 `has_coordinates()` 为 false，会被当作无坐标。

**新一代端点（`/weather/v1/*` 等）的路径参数是纬度在前**，**v7 与 GeoAPI 的查询参数是经度在前**。写反了上游直接 400：

```python
qwx.Location(lat=39.92, lon=116.41)  # 坐标对
qwx.Location(id="101010100")  # LocationID
qwx.Location(name="杭州")  # 地名，只有 GeoAPI 认
qwx.parse_location("116.41,39.92")  # 从字符串解析：经度在前
```

每个端点认哪种形态见[支持的接口](#endpoints)的方法总表。

<a id="lang"></a>
### 🌐 语言

上游用 `lang` 查询参数切换返回的语言。各端点的语言参数都是 `qwx.Lang`（`qwx.v7.indices` 与 `qwx.v7.minutely` 是形参，其余在 `Options` 里）。

- 语言代码取自官方「多语言」页，SDK 内置 31 种：`qwx.Lang.ZH`、`qwx.Lang.ZH_HANT`、`qwx.Lang.EN` …… 完整列表在 `qwx.LANGS`。
- 留空（`qwx.Lang.UNSPECIFIED`）不传 `lang`，用上游默认：所在国家或地区的官方语言，没有官方语言时回退到英语。官方数据不支持指定语言时，回退顺序是指定语言 > 官方语言 > 英语。
- 官方给的等价代码（简体中文的 `zh-hans`）用 `qwx.lookup_lang` 查得到，发出去的仍是首选代码 `zh`。
- 语言代码形态不对时返回 `qwx.InvalidParameterError`，不打上游。
- 认语言参数的端点：新一代天气（`current`/`hourly`/`daily`）、空气质量（`current`/`daily`/`hourly`/`station`）、预警（`current`）、GeoAPI 四个检索端点、旧一代生活指数与分钟级降水、月相（`moon`）、历史天气。监测站数据有独立文档页（`/docs/api/air-quality/air-station/`），明确带 `lang` 参数。
- 不认语言参数的端点：太阳辐射预报、潮汐、台风三个端点、日出日落与太阳高度角、控制台两个端点。上游没有这个参数，多传会被拒，SDK 也不暴露。
- 缓存键里带的是 API 代码（`:lang=zh`），不是语言名，即 `qwx.Lang` 的 `api` 字段。换语言就是换一份数据，键必须跟着变。

---
<a id="caching"></a>
### 🗄️ 缓存与 TTL

不传 `cache` 时每次请求都打到上游。缓存接口只有两个方法，自己实现即可：

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

内置 `qwx.MemoryCache` 是进程内、带锁的，**不建议用于生产环境**。它没有后台清理，过期条目只在被 `get` 命中时顺手删除，没被再次访问的过期条目会一直留在字典里，长跑进程的内存占用只增不减。它只适合测试替身与单实例的临时缓存；生产环境用 Redis 等共享缓存，多实例部署也需要共享缓存，否则命中率被摊薄。

```python
import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=qwx.MemoryCache())
```

#### Redis 实现

Redis 适配是可选依赖，装 extra：

```bash
pip install "qwx[redis]"
```

```python
import qwx
from qwx.redis_cache import RedisCache

# 用 URL 构造
cache = RedisCache.from_url("redis://127.0.0.1:6379/0")

# 或复用已有的 redis-py 客户端，连接池、超时、TLS 都由调用方控制
import redis

cache = RedisCache(redis.Redis(host="127.0.0.1", port=6379, db=0))

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

要点：

- 构造时**不连 Redis**，连接在第一次读写时建立。地址写错要等第一次读写才暴露。
- `from_url` 需要装了 redis-py，没装时抛 `ImportError`；`RedisCache(client)` 接受任何有 `get` / `set` 方法的对象。
- `set` 的 `ttl` 是相对时长，换算成 Redis 的 `ex=`（整数秒，向上取整，不足 1 秒按 1 秒算）。ttl 非正数抛 `qwx.InvalidParameterError` 且不写入，不带过期时间的天气数据会一直是旧的。
- 缓存值存**原始 JSON bytes**，与 Go 版共享同一个 Redis 时键和值都互通：Python 写入的条目 Go 版能读，反之亦然。
- 不要给客户端开 `decode_responses=True`，值按 bytes 存取，开了之后与 Go 版不再互通。
- 缓存错误照旧被 SDK 吞掉并降级为直连上游，Redis 挂了不影响接口可用性。

#### 缓存键

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

键字面量在已发布版本里定死，改动会让已写入的缓存条目全部失效。`qwx.v7.ocean` 的键前缀是 `qwx:tide:` 而不是 `qwx:ocean:`，与模块名不对齐是有意为之，不要「顺手修正」。

后缀承载影响结果的查询参数：语言 `:lang=<lang>`、新一代本地时间 `:localTime=1`、条数 `:n=<number>`、半径 `:r=<radius>`、行政区划 `:adm=<adm>`、搜索范围 `:range=<range>`、限定城市 `:city=<city>`、时间间隔 `:interval=<n>`、倾斜角 `:tilt=<n>`、方位角 `:azimuth=<n>`、额外信息 `:extra=<extra>`、项目 `:project=<project>`、凭据 `:credential=<credential>`。坐标统一两位小数，`-0` 归一为 `0.00`。

语言段进的是 API 代码（`:lang=zh`），不是语言名。`qwx.Lang` 的 `api` 字段。

后缀顺序固定：语言 → 本地时间 → 条数 → 半径 → 行政区划 → 搜索范围 → 城市 → 时间间隔 → 倾斜角 → 方位角 → 额外信息 → 项目 → 凭据。新加的参数一律追加在末尾，老调用方不设它们，键的字节与发布时完全一致。

键不含 API Host，不同 Host 对应不同开发者账号，一个 Cache 实例不要跨账号共用，否则会串味。

##### 键怎么拼

拼法只有一处：`src/qwx/_cachekey.py`。端点模块不自己拼字符串，只声明两件事，自己属于哪个族、有哪些影响结果的参数。

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

影响结果的查询参数用同一个 `qwx._cachekey.Params` 声明，它同时生成上游查询串与键的后缀。新增参数只改这一处，参数漏进键不会发生。

```python
# src/qwx/v1/weather/client.py
def _params(opts: Options) -> Params:
    return Params(lang=opts.lang.api, local_time=opts.local_time)
```

半径用 `None` 表示「端点没有半径参数」；半径为 0 时只进键、不发给上游，上游按自己的默认值处理。

倾斜角与方位角也用 `None` 表示「不传」，0 是合法取值，非 `None` 时要连 0 一起发给上游。

#### TTL

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

##### 自定义 TTL

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
    ttl_policy=qwx.TTLMap(
        {
            EndpointCurrent: timedelta(minutes=5),
            AQCurrent: timedelta(0),  # 该端点不缓存
        }
    ),
)
```

`qwx.TTLMap` 是最常用的形态：键是端点常量，值是缓存时长。键不存在时沿用端点默认时长，值为 0 表示该端点不缓存。

需要按时间或负载动态调整时用 `qwx.TTLPolicyFunc`：

```python
policy = qwx.TTLPolicyFunc(
    lambda endpoint, default: timedelta(seconds=10) if endpoint == EndpointCurrent else default
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

##### TTL 与缓存键

改 TTL 不改缓存键。已写入的旧条目按写入时的 TTL 到期，调小策略不会让它们提前失效。想立刻生效要换缓存实例或手动清键。

---
<a id="logging"></a>
### 📝 日志

SDK 用标准库 `logging`，不自带日志实现，也不引入第三方依赖。

#### 开关

不注入 logger 时一个字节都不输出。注入：

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

`logger=None` 等同于不注入：不注入时 SDK 挂一个 `NullHandler` 并关掉 `propagate`，输出全部丢弃。

级别由 handler 决定，SDK 不再过滤。handler 放行 DEBUG，就会连缓存命中这类明细一起收到。

#### 记什么

| 级别 | 消息 | 触发时机 |
| --- | --- | --- |
| DEBUG | `cache hit` | 命中缓存，没打上游 |
| DEBUG | `cache miss` | 没命中缓存，请求打到上游 |
| WARNING | `cache read failed` | 缓存读失败，请求降级为直连上游 |
| WARNING | `cache write failed` | 缓存写失败，响应已经拿到，不影响结果 |
| INFO | `upstream request` | 上游返回 2xx |
| WARNING | `upstream rejected` | 上游返回 4xx，请求本身不合法 |
| ERROR | `upstream rejected` | 上游返回 5xx，上游故障 |
| WARNING | `upstream retry` | 5xx、429 或网络错误触发重试 |
| ERROR | `decode response failed` | 响应不是合法 JSON，或结构与模型对不上 |
| ERROR | `sign request failed` | 写入认证信息失败 |

一次请求最多一条 `upstream request` 或 `upstream rejected`，加上重试与缓存的零星记录。命中缓存的请求没有上游记录，只有 `cache hit`。

#### 字段

字段名集中定义在 `src/qwx/logger.py` 的常量里，可以在自己的 handler 里按名字过滤。

| 字段 | 含义 |
| --- | --- |
| `endpoint` | 端点标识，如 `weather/v1/current`。请求没填端点时没有这个字段 |
| `method` | HTTP 方法，留空按 GET 处理 |
| `path` | 接口路径，不含查询参数 |
| `status` | HTTP 状态码 |
| `duration_ms` | 耗时毫秒 |
| `cache_key` | 缓存键 |
| `attempt` | 第几次重试，从 1 开始 |
| `error` | 错误文本 |
| `upstream_code` | 上游业务状态码 |
| `upstream_title` | 上游给的一句话原因 |

字段通过标准库 `LogRecord` 的 `extra` 传入，在 handler 里按名字取：

```python
class FieldFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # 字段是可选的，没填端点的请求没有 endpoint，用 getattr 取。
        return getattr(record, "endpoint", "") != "weather/v1/current"
```

#### 不记什么

- **认证凭据**：JWT 与 API KEY 都走请求头，不进日志。
- **响应体**：只记状态码与上游给的原因。响应体只在错误对象 `qwx.UpstreamError.body` 里，截断到 2KB。
- **查询参数**：不主动记录。传输层的错误文本里内嵌了完整 URL，记录前会剥掉查询串，只留 path 与错误原因（`qwx.logger.sanitize_error_text`）。

路径与缓存键可能带位置坐标（新一代路径是 `纬度,经度`），日志的可见范围自己把握。

SDK 不对坐标脱敏，坐标是这次调用的主体，排查命中与定位都离不开它。要脱敏就在注入时包一层自己的 handler。

#### 自定义脱敏

SDK 不提供脱敏开关。日志器是你注入的 handler，要改写敏感字段就在注入前包一层。

```python
import logging


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # 改写 record 的 path / cache_key，再交给下游 handler。
        if hasattr(record, "path"):
            record.path = "<redacted>"
        if hasattr(record, "cache_key"):
            record.cache_key = "<redacted>"
        return True


logger = logging.getLogger("qwx")
logger.addFilter(RedactFilter())
client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logger)
```

#### 例子

JSON 输出到 stdout：

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

只关心失败与告警，把级别调到 WARNING：

```python
logger.setLevel(logging.WARNING)
```

#### 性能

不注入 logger 时 SDK 挂在 `NullHandler` 上：不做格式化，也不构造字段，每个请求的额外开销只有一次 `isEnabledFor` 调用。开了日志之后，打上游的请求一条 INFO，缓存命中一条 DEBUG。字段用 dict 构造，不拼字符串。handler 的实现要自己保证并发安全。

<a id="errors"></a>
### 🚨 错误处理

所有 SDK 异常都继承 `qwx.QwxError`。用 `isinstance` / `except` 判断类别，不解析错误字符串。

```
QwxError
├── InvalidConfigError
├── InvalidLocationError
├── InvalidParameterError
├── InvalidResponseError
└── UpstreamError
    ├── UpstreamRejectedError     上游 4xx
    ├── QuotaExceededError        上游 429
    ├── UnauthorizedError         上游 401 / 403
    └── UpstreamUnavailableError  上游 5xx 或网络错误
```

| 异常 | 触发 | 处置 |
| --- | --- | --- |
| `InvalidConfigError` | 构造参数有问题：缺认证、空私钥、空 API KEY、空 API Host | 修代码，不重试 |
| `InvalidLocationError` | location 形态非法或上游不认：空串、非数字、NaN/Inf、超范围坐标、无坐标 | 修请求，不重试 |
| `InvalidParameterError` | 参数越界：`hours`、`days`、`type`、`radius` 外的取值、日期格式、语言代码形态 | 修请求，不重试 |
| `InvalidResponseError` | 上游返回的不是合法 JSON，或结构与模型对不上 | 看 `UpstreamError.body`，重试可能有用 |
| `UpstreamRejectedError` | 上游 4xx | 修请求，重试没有意义 |
| `QuotaExceededError` | 上游 429 | 退避后重试 |
| `UnauthorizedError` | 上游 401/403 | 查凭据，见[认证](#authentication) |
| `UpstreamUnavailableError` | 上游 5xx 或网络错误（含超时） | 指数退避重试 |

前四类在客户端本地抛出，不打上游。

```python
import qwx

try:
    result = weather.current(loc)
except qwx.UnauthorizedError:
    ...  # 查凭据
except qwx.QuotaExceededError:
    ...  # 退避后重试
except qwx.InvalidParameterError:
    ...  # 修请求
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params)
except qwx.QwxError:
    ...  # 其余 SDK 异常
```

#### 读上游细节

`UpstreamError` 上挂着上游给的细节：

```python
except qwx.UpstreamError as exc:
    print(exc.status_code, exc.code, exc.title, exc.invalid_params, exc.body)
```

字段：`status_code`（HTTP 状态码）、`code`（上游业务码）、`title`（一句话原因）、`invalid_params`（新一代接口给出的非法参数名）、`body`（原始响应体，截断到 2KB）。

两代错误体都解析：

- 新一代：`{"error":{"status":400,"title":"Invalid Parameters","invalidParams":["longitude","latitude"]}}`
- 旧一代：`{"code":"400","error":"Invalid Parameters"}`

拿不到响应的网络错误也是 `UpstreamUnavailableError`，此时 `status_code` 为 0。

#### 重试判据

客户端自身已经带退避重试：上游 5xx、429 或网络错误时最多再试 3 次（`qwx.client.MAX_RETRY`），单次等待不超过 `qwx.client.MAX_RETRY_DELAY`（30 秒），上游给了 `Retry-After` 且更大就听上游的。4xx 不重试。

| 现象 | 类别 | 动作 |
| --- | --- | --- |
| 429 | `QuotaExceededError` | 客户端已退避重试；仍失败则按配额退避，叠加抖动 |
| 5xx / 连接失败 / 超时 | `UpstreamUnavailableError` | 客户端已指数退避重试；仍失败则在业务层退避重试 |
| 400 / 404 | `UpstreamRejectedError` | 修请求；重试只会重复消耗配额 |
| 401 / 403 | `UnauthorizedError` | 查凭据 |
| JSON 解析失败 | `InvalidResponseError` | 抓 body 判断是网关错误页还是上游异常 |

缓存故障不会变成业务错误：缓存 `get` / `set` 出错时 SDK 直接打上游，逻辑在 `src/qwx/client.py` 的 `do`。

<a id="concurrency"></a>
### ⏱️ 并发与超时

`Client` 与 `AsyncClient` 无状态，可并发共享。默认单请求超时 30 秒；需要代理、连接池或自定义证书时注入自己的 httpx 客户端：

```python
import httpx

import qwx

http = httpx.Client(
    timeout=httpx.Timeout(10.0, connect=3.0), limits=httpx.Limits(max_connections=50)
)
client = qwx.Client(auth, "abcxyz.qweatherapi.com", http_client=http)
```

异步版同理，注入 `httpx.AsyncClient`。

---
<a id="verification"></a>
### 🧪 测试与验证

#### 装依赖

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

要跑 Redis 适配的测试再装 Redis extra：

```bash
.venv/bin/pip install -e ".[dev,redis]"
```

用 uv 的话：

```bash
uv sync --all-extras
uv run pytest -q
```

#### 门禁命令

```bash
.venv/bin/ruff format --check .   # 必须无输出
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
```

`ruff` 的配置在 `pyproject.toml`：`line-length = 100`，`target-version = "py310"`，选中的规则集是 `E F I UP B SIM RUF N`。

`mypy` 是 strict 模式，只检查 `src/qwx`（`files = ["src/qwx"]`），Python 版本目标 3.10。

#### 测试分档

只跑与本次改动直接相关的最小测试集。

| 档 | 改动 | 跑什么 |
| --- | --- | --- |
| 1 | 单个端点族 / 单个文件 | 该模块对应的 `tests/test_*.py` + `ruff format --check .` + `mypy` |
| 2 | 跨模块（`client.py`、`auth.py`、`cache.py`、`location.py`） | 涉及模块 + 直接依赖模块的测试 |
| 3 | 核心重构（缓存键、位置解析、请求执行） | `.venv/bin/python -m pytest tests/ -q` 全量 |

#### 联网冒烟

`live/` 下的四个文件带 `live` 标记，默认不参与 `pytest tests/`（测试路径只含 `tests/`）。需要真实凭据，缺任一项即 skip，不会让 CI 因缺凭据失败。

| 文件 | 覆盖 |
| --- | --- |
| `live/conftest.py` | 共用装置：读环境变量、造客户端、缺凭据时的 skip 标记 |
| `live/test_live_v1.py` | 新一代：天气、空气质量、预警、太阳辐射 |
| `live/test_live_v7.py` | 旧一代：天文、历史天气、生活指数、分钟级降水、台风、潮汐 |
| `live/test_live_geo.py` | GeoAPI：城市检索、POI 检索、POI 范围、城市榜 |
| `live/test_live_console.py` | 控制台：财务汇总、请求量统计 |

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_API_KEY=YOUR_API_KEY \
.venv/bin/python -m pytest live/ -q -m live
```

或者走 JWT，私钥是 PEM 内容，也接受含字面量 `\n` 转义的写法：

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)" \
QWX_KEY_ID=YOUR_KEY_ID \
QWX_PROJECT_ID=YOUR_PROJECT_ID \
QWX_DEVELOPER_ID=YOUR_DEVELOPER_ID \
.venv/bin/python -m pytest live/ -q -m live
```

环境变量：

| 变量 | 说明 |
| --- | --- |
| `QWX_API_HOST` | 控制台分配的专属 API Host，必填 |
| `QWX_API_KEY` | API KEY，与 JWT 二选一 |
| `QWX_JWT_PRIVATE_KEY` | Ed25519 私钥 PEM 内容 |
| `QWX_KEY_ID` | Key ID |
| `QWX_PROJECT_ID` | Project ID |
| `QWX_DEVELOPER_ID` | Developer ID |

JWT 凭据齐全就走 JWT，缺了就退到 API KEY。两种都没配齐时整个模块 skip。

改了上游行为、端点字段或请求参数后跑它，验证真实响应。

#### 完成判定

- `ruff format --check .` 无输出，`ruff check .` 无告警，`mypy` 通过。
- 涉及改动的模块测试通过，错误分支也有覆盖。
- 端点行为变化时，本文档的[端点契约](#contract)、[支持的接口](#endpoints)、[缓存与 TTL](#caching)对应段落同步更新。
- `.venv/bin/python -m pytest tests/ -q` 全绿。

---

<a id="endpoints"></a>
## 🔌 支持的接口

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

缓存键的完整模板见[缓存与 TTL](#caching)，那里还有参数的进键规则。

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

---
<a id="contract"></a>
## 📋 端点契约

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

端点常量用于按端点调缓存时长，见[自定义 TTL](#caching)。

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

### 上游有但 qwx 未覆盖

上游还有这些端点，本库没接。它们分两类：已定停服日的不要再写，仍活着的可以按需补。

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

本库支持的 `/v7/minutely/5m`、`/v7/indices/{days}`、`/v7/ocean/tide`、`/v7/historical/weather` 都不在停服名单里，可以继续用。

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

---

<a id="upstream-docs"></a>
## 🔗 官方文档

<https://dev.qweather.com/docs/>

---

<a id="license"></a>
## ⚖️ 许可

本包遵循 MIT 许可。

本包不是和风天气官方产品。使用上游数据需遵守[和风天气开发者许可协议](https://www.qweather.com/terms/developers-eula/)，展示天气数据时需保留上游返回的 attribution 信息。





