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

qwx 是和风天气（QWeather）的 Python SDK，覆盖 26 个端点、12 个资源族，返回 pydantic v2 模型，同步与异步双栈。

---

<a id="features"></a>
## ✨ 特性

- **26 个端点**：天气、空气质量、预警、太阳辐射、GeoAPI、控制台、天文、历史天气、生活指数、分钟级降水、台风、潮汐。
- **同步与异步双栈**（httpx），端点方法体只写一份，异步客户端返回协程。
- **pydantic v2 模型**，上游新增字段进 `model_extra`，不会被丢弃。
- **参数本地校验**，越界与位置形态非法在客户端抛异常，不打上游。
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
uv add "qwx[redis]"
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

两种认证任选其一，不能同时使用。新项目默认选 JWT。

| 方式 | 构造 | 请求头 | 适用 |
| --- | --- | --- | --- |
| `qwx.JWTAuth` | `qwx.JWTAuth(private_key_pem=..., key_id=..., project_id=..., developer_id=...)` | `Authorization: Bearer <JWT>` | 新项目默认 |
| `qwx.APIKeyAuth` | `qwx.APIKeyAuth(key)` | `X-QW-Api-Key: <key>` | 存量项目 |

API KEY 已被官方公告限量：2027-01-01 起限制每日请求量，SDK 5+ 不再支持。

JWT 需要控制台的三项凭据与一对 Ed25519 密钥：

```bash
openssl genpkey -algorithm ED25519 -out ed25519-private.pem
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
```

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `private_key_pem` | 是 | Ed25519 PKCS#8 PEM 文本 |
| `key_id` | 是 | 控制台的 Key ID，进 JWT header 的 `kid` |
| `project_id` | 是 | 控制台的 Project ID，进 payload 的 `sub` |
| `developer_id` | 是 | 控制台的 Developer ID，进 payload 的 `iss` |
| `token_ttl` | 否 | token 有效期，默认 `timedelta(minutes=15)` |

四项凭据缺任一项抛 `qwx.InvalidConfigError`。token 在过期前 1 分钟自动重签，调用方无感。

专属 API Host 也是必填项：控制台「设置」页分配，形如 `abcxyz.qweatherapi.com`。公共域名已陆续停服，SDK 不内置默认值。只给 host 时自动补 `https://`；带 scheme 时按给的来。凭据与 Host 不匹配上游会拒。

认证失败（401 / 403，抛 `qwx.UnauthorizedError`）时按这个顺序查：

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

`api_host` 没有默认值，必须用控制台分配的专属 Host。

<a id="location"></a>
### 📍 位置

`Location` 有三种形态，同一个端点接受的子集不同。形态互不等价，传错的上游直接拒绝。

| 形态 | 构造 | 谁认 |
| --- | --- | --- |
| 坐标对 | `qwx.Location(lat=39.92, lon=116.41)` 或 `qwx.parse_location("116.41,39.92")` | 除控制台、台风、热门城市外的端点 |
| LocationID | `qwx.Location(id="101010100")` | GeoAPI；天文的日出日落与月相；历史天气。行政区划是 9~10 位数字，POI 是数字加字母后缀，潮汐站与监测站是 `P` 加数字 |
| 地名 | `qwx.Location(name="杭州")` | 仅 `GeoService.lookup_city` / `GeoService.lookup_poi` |

```python
qwx.Location(lat=39.92, lon=116.41)  # 坐标对
qwx.Location(id="101010100")  # LocationID
qwx.Location(name="杭州")  # 地名，只有 GeoAPI 认
qwx.parse_location("116.41,39.92")  # 从字符串解析：经度在前
```

坐标在 SDK 内保留两位小数，`-0` 归一为 `0.00`。`qwx.parse_location` 拒绝空串、非数字、NaN/Inf、超范围经纬度，返回 `qwx.InvalidLocationError`。坐标恰为 `(0, 0)` 时 `has_coordinates()` 为 false，会被当作无坐标。

**新一代端点（`/weather/v1/*` 等）的路径参数是纬度在前**，**v7 与 GeoAPI 的查询参数是经度在前**。写反了上游直接 400。

每个端点认哪种形态见[支持的接口](#endpoints)的表。

<a id="lang"></a>
### 🌐 多语言

上游用 `lang` 查询参数切换返回的语言。语言参数是 `qwx.Lang`，多数端点放在 `Options` 里，`qwx.v7.indices` 与 `qwx.v7.minutely` 是形参。

- SDK 内置 31 种：`qwx.Lang.ZH`、`qwx.Lang.ZH_HANT`、`qwx.Lang.EN` …… 完整列表在 `qwx.LANGS`。
- 留空（`qwx.Lang.UNSPECIFIED`）不传 `lang`，用上游默认：所在国家或地区的官方语言，没有官方语言时回退到英语。
- 官方给的等价代码（简体中文的 `zh-hans`）用 `qwx.lookup_lang` 查得到，发出去的仍是首选代码 `zh`。
- 语言代码形态不对时返回 `qwx.InvalidParameterError`，不打上游。
- 太阳辐射预报、潮汐、台风、日出日落与太阳高度角、控制台不认语言参数，SDK 也不暴露。

<a id="caching"></a>
### 🗄️ 缓存

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

内置 `qwx.MemoryCache` 是进程内、带锁的，**不建议用于生产环境**：它没有后台清理，没被再次访问的过期条目会一直留在字典里。它只适合测试替身与单实例的临时缓存；多实例部署需要共享缓存。

Redis 适配是可选依赖（`pip install "qwx[redis]"`）：

```python
import qwx
from qwx.redis_cache import RedisCache

# 用 URL 构造
cache = RedisCache.from_url("redis://127.0.0.1:6379/0")

# 或复用已有的 redis-py 客户端
import redis

cache = RedisCache(redis.Redis(host="127.0.0.1", port=6379, db=0))

client = qwx.Client(auth, "abcxyz.qweatherapi.com", cache=cache)
```

缓存值存原始 JSON bytes，与 Go 版共享同一个 Redis 时键和值互通。不要给 Redis 客户端开 `decode_responses=True`。

默认缓存时长由端点模块决定，需要调整时传一份 `ttl_policy`：

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

单次请求要临时绕过缓存，用上下文覆盖：

```python
with client.override_ttl(timedelta(0)):  # 这一次不读也不写缓存
    weather.current(loc)
```

时长解析顺序：单次上下文覆盖 > `TTLPolicy` > 端点模块内置默认时长。

缓存键模板、各端点默认 TTL、缓存键的拼装规则见 [docs/zh/cache.md](docs/zh/cache.md)。

<a id="logging"></a>
### 📝 日志

SDK 用标准库 `logging`，不自带日志实现。注入 logger 才有输出：

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

不注入时 SDK 挂一个 `NullHandler`，输出全部丢弃。级别由 handler 决定：DEBUG 能看到缓存命中与未命中，INFO 能看到上游请求，WARNING 是缓存失败与上游 4xx，ERROR 是上游 5xx 与响应解析失败。

日志不含认证凭据与响应体。字段名、脱敏做法与性能说明见 [docs/zh/logging.md](docs/zh/logging.md)。

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
| `InvalidLocationError` | location 形态非法或上游不认 | 修请求，不重试 |
| `InvalidParameterError` | 参数越界：`hours`、`days`、`type`、`radius` 外的取值、日期格式、语言代码形态 | 修请求，不重试 |
| `InvalidResponseError` | 上游返回的不是合法 JSON，或结构与模型对不上 | 看 `UpstreamError.body`，重试可能有用 |
| `UpstreamRejectedError` | 上游 4xx | 修请求，重试没有意义 |
| `QuotaExceededError` | 上游 429 | 退避后重试 |
| `UnauthorizedError` | 上游 401 / 403 | 查凭据 |
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

`UpstreamError` 上挂着上游给的细节：`status_code`（HTTP 状态码）、`code`（上游业务码）、`title`（一句话原因）、`invalid_params`（新一代接口给出的非法参数名）、`body`（原始响应体，截断到 2KB）。

客户端自带退避重试：上游 5xx、429 或网络错误时最多再试 3 次（`qwx.client.MAX_RETRY`），4xx 不重试。

缓存故障不会变成业务错误：缓存 `get` / `set` 出错时 SDK 直接打上游。

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

<a id="endpoints"></a>
## 🔌 支持的接口

26 个端点，覆盖十二个资源族。位置形态一列是调用前必看的。

| 包 | 方法 | 上游路径 | 位置形态 |
| --- | --- | --- | --- |
| `qwx.console` | `finance` | `/finance/v1/summary` | 无 |
| `qwx.console` | `stats` | `/metrics/v1/stats` | 无 |
| `qwx.geo` | `lookup_city` | `/geo/v2/city/lookup` | 坐标 / LocationID / 地名 |
| `qwx.geo` | `lookup_poi` | `/geo/v2/poi/lookup` | 坐标 / LocationID / 地名 |
| `qwx.geo` | `poi_range` | `/geo/v2/poi/range` | 坐标 |
| `qwx.geo` | `top_cities` | `/geo/v2/city/top` | 无 |
| `qwx.v1.airquality` | `current` | `/airquality/v1/current/{lat}/{lon}` | 坐标 |
| `qwx.v1.airquality` | `daily` | `/airquality/v1/daily/{lat}/{lon}` | 坐标 |
| `qwx.v1.airquality` | `hourly` | `/airquality/v1/hourly/{lat}/{lon}` | 坐标 |
| `qwx.v1.airquality` | `station` | `/airquality/v1/stations/{stationID}` | 站点 ID |
| `qwx.v1.alert` | `current` | `/weatheralert/v1/current/{lat}/{lon}` | 坐标 |
| `qwx.v1.solarradiation` | `forecast` | `/solarradiation/v1/forecast/{lat}/{lon}` | 坐标 |
| `qwx.v1.weather` | `current` | `/weather/v1/current/{lat}/{lon}` | 坐标 |
| `qwx.v1.weather` | `hourly` | `/weather/v1/hourly/{lat}/{lon}` | 坐标 |
| `qwx.v1.weather` | `daily` | `/weather/v1/daily/{lat}/{lon}` | 坐标 |
| `qwx.v7.astronomy` | `sun` | `/v7/astronomy/sun` | 坐标 / LocationID |
| `qwx.v7.astronomy` | `moon` | `/v7/astronomy/moon` | 坐标 / LocationID |
| `qwx.v7.astronomy` | `solar_elevation_angle` | `/v7/astronomy/solar-elevation-angle` | 坐标 |
| `qwx.v7.historical` | `weather` | `/v7/historical/weather` | LocationID |
| `qwx.v7.indices` | `indices` | `/v7/indices/{days}d` | 坐标 |
| `qwx.v7.indices` | `indices_multi` | `/v7/indices/{days}d` | 坐标 |
| `qwx.v7.minutely` | `minutely` | `/v7/minutely/5m` | 坐标 |
| `qwx.v7.ocean` | `tide` | `/v7/ocean/tide` | 站点 ID |
| `qwx.v7.storm` | `list` | `/v7/tropical/storm-list` | 无 |
| `qwx.v7.storm` | `forecast` | `/v7/tropical/storm-forecast` | 无 |
| `qwx.v7.storm` | `track` | `/v7/tropical/storm-track` | 无 |

每个端点的参数、返回类型与取值范围见 [docs/zh/endpoints.md](docs/zh/endpoints.md)。

---

<a id="reference"></a>
## 📚 参考文档

| 文档 | 内容 |
| --- | --- |
| [docs/zh/endpoints.md](docs/zh/endpoints.md) | 端点契约：参数、返回类型、取值范围、字段语义 |
| [docs/zh/cache.md](docs/zh/cache.md) | 缓存键模板、各端点默认 TTL、自定义 TTL |
| [docs/zh/upstream.md](docs/zh/upstream.md) | 上游停服与替代、上游怪癖与限制 |
| [docs/zh/logging.md](docs/zh/logging.md) | 日志级别与字段、脱敏 |
| [docs/zh/development.md](docs/zh/development.md) | 环境、门禁命令、测试分档、联网冒烟 |

英文版见 [docs/en/](docs/en/)。

官方文档：<https://dev.qweather.com/docs/>

---

<a id="license"></a>
## ⚖️ 许可

本包遵循 MIT 许可。

本包不是和风天气官方产品。使用上游数据需遵守[和风天气开发者许可协议](https://www.qweather.com/terms/developers-eula/)，展示天气数据时需保留上游返回的 attribution 信息。
