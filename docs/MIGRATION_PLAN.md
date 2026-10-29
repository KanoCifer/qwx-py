# qwx-py 迁移方案

把 `github.com/KanoCifer/qwx`（Go）移植成 Python SDK，导入名 `qwx`，PyPI 分发名 `qwx`。

目标：**语义对等**。端点集合、缓存键字节、端点常量值、错误分类、TTL 优先级、
上游怪癖处理全部与 Go 版一致。命名走 Python 惯例（snake_case 方法名、
dataclass 传参），数据模型用 pydantic v2。

---

## 1. 已定决策

| # | 决策 | 取值 | 理由 |
| --- | --- | --- | --- |
| D1 | HTTP 层 | httpx，同步 + 异步双栈 | httpx 无内置重试但有完整超时/传输控制；异步是真实需求，不做「异步原生 + 同步套壳」 |
| D2 | API 表面 | 语义对等 + Pythonic 命名 | `Current` → `current`，`LocalTime` → `local_time`，`Options` 用 dataclass |
| D3 | 覆盖范围 | 全量 26 个端点，含旧一代 v7 | 两代分治是上游硬约束，分期只会把坑推迟 |
| D4 | 分发名 | `qwx` | PyPI 未被占用；`qweather` 已被一个无关的 zeromq 项目占用 |
| D5 | 核心依赖 | httpx + pydantic v2 + cryptography | cryptography 提供 Ed25519；JWT 签名手写，不引 pyjwt |
| D6 | Redis 适配 | 独立 extra `qwx[redis]`，用 redis-py | 对应 Go 版的独立模块，核心包不因缓存实现而膨胀 |
| D7 | 缓存值 | 存原始 JSON bytes | 与 Go 版共享同一 Redis 实例时值也互通，不只是键互通 |
| D8 | 时间字段 | 保持 `str`，另给解析辅助函数 | 上游时间格式偶有变体，解析失败不该让整份响应变成校验错误 |
| D9 | 未知字段 | pydantic `extra="allow"` | 上游会新增字段，保留进 `model_extra` 比丢弃更可用 |
| D10 | 单次 TTL 覆盖 | contextvars 上下文管理器 | Go 用 ctx 显式传递；Python 惯用上下文管理器，且不必给 26 个方法加 `ttl=` 参数 |

---

## 2. Go → Python 抽象映射

| Go | Python | 说明 |
| --- | --- | --- |
| `qwx.Client` | `qwx.Client` | httpx 同步传输 |
| — | `qwx.AsyncClient` | httpx 异步传输；共享同一套配置与请求构造 |
| `qwx.Doer` | `qwx.Doer` / `qwx.AsyncDoer` | `typing.Protocol`，运行时可检查 |
| `qwx.Request` | `qwx.Request` | frozen dataclass，字段一一对应 |
| `qwx.Cache` | `qwx.Cache` | `Protocol`：`get(key) -> bytes \| None`、`set(key, data, ttl)` |
| `qwx.MemoryCache` | `qwx.MemoryCache` | 同样注明「无后台清理，不建议生产」 |
| `qwx.TTLPolicy` / `TTLMap` | `qwx.TTLPolicy` / `qwx.TTLMap` | 返回 `timedelta`，`<= 0` 表示不缓存 |
| `qwx.Endpoint` | `qwx.Endpoint` | `str` 子类常量，值与 Go 版逐字相同 |
| `qwx.Location` | `qwx.Location` | frozen dataclass，`path()` 纬度在前，`query()` 经度在前 |
| `qwx.Lang` | `qwx.Lang` | frozen dataclass，`Lang.ZH` 等 33 个语言常量 + 别名表 |
| `qwx.UpstreamError` + 8 个 sentinel | 异常层级 | 见 §4.4 |
| `internal/cachekey` | `qwx._cachekey` | 私有模块，键字面量逐字复制 |
| `internal/coord` | `qwx._coord` | 两位小数格式化，`-0.00` → `0.00` |
| `qwx/v1` | `qwx.v1` | `Metadata` / `Value` / `Options` |
| `v1/weather` … `v7/historical` | `qwx.v1.weather` … `qwx.v7.historical` | 一个包 = 一个资源族 |
| `log/slog` | `logging` | 标准库，字段走 `extra=` |

---

## 3. 目标目录结构

```
qwx-py/
├── pyproject.toml
├── README.md  README_EN.md
├── LICENSE                      # 与 Go 版同
├── src/qwx/
│   ├── __init__.py              # 导出 Client / AsyncClient / Location / 异常 / Lang
│   ├── client.py                # Client、AsyncClient
│   ├── request.py               # Request、Doer、AsyncDoer
│   ├── auth.py                  # JWTAuth、APIKeyAuth
│   ├── cache.py                 # Cache、MemoryCache
│   ├── ttl.py                   # Endpoint、TTLPolicy、TTLMap、TTLPolicyFunc
│   ├── errors.py                # 异常层级
│   ├── location.py  lang.py  logger.py  refer.py
│   ├── _coord.py  _cachekey.py  _service.py
│   ├── v1/
│   │   ├── __init__.py          # Metadata、Value、Options
│   │   ├── weather/  airquality/  alert/  solarradiation/
│   ├── v7/
│   │   ├── ocean/  indices/  minutely/  storm/  astronomy/  historical/
│   ├── geo/  console/
│   └── py.typed
├── tests/                       # 与源码同构：test_client.py 对应 client.py
├── tools/
│   ├── gen_endpoints.py         # 生成 docs/endpoints.md
│   └── check_json_tags.py       # Go json tag ↔ Python alias 对照
├── examples/
└── live/                        # 联网冒烟，pytest -m live
```

端点族目录内固定两个文件：`types.py`（模型 + 参数 + 常量）与 `client.py`
（服务客户端 + 端点方法）。与 Go 版「定义与实现分离」一致。

---

## 4. 核心层设计

### 4.1 同步/异步双栈：端点层只写一次

关键约束：26 个端点方法不能写两遍。做法是把「构造请求」与「发送请求」分开。

- 端点方法只负责算出 `(path, query, cache_key, ttl, endpoint)`，交给 `self._do(call)`。
- `Client._do` 是同步实现，返回模型。
- `AsyncClient._do` 是 `async def`，返回协程。

同一个方法体在两个类上都成立：同步类拿到模型，异步类 `await` 后拿到模型。

```python
class WeatherService:
    """天气端点族的公共方法体。"""

    _base: Doer | AsyncDoer

    def current(self, loc: Location, opts: Options | None = None) -> CurrentWeather:
        call = _current_call(loc, opts)
        return self._do(call)  # sync: 模型; async: 协程

    def _do(self, call: Call) -> Any: ...  # 由 Client / AsyncClient 各自实现
```

重复的只有核心层传输逻辑（重试、退避、缓存读写），约 200 行 × 2。
`_do` 返回类型标注为 `Any`，mypy 配置里对 `qwx._service` 关闭
`warn_return_any`；对外公开方法的返回类型仍是精确的模型类型。

### 4.2 请求与重试

- 默认超时 30 秒（对应 Go 的 `DefaultTimeout`），httpx 用 `httpx.Timeout(30.0)`。
- 重试次数与 Go 版一致：首次 + 最多 3 次。
- 触发条件：5xx、429、网络错误。
- 退避：第 i 次等待 i 秒；上游给了 `Retry-After`（秒数或 HTTP 日期）且更大就听上游的；单次等待上限 30 秒。
- `Retry-After` 用 `email.utils.parsedate_to_datetime` 解析 HTTP 日期。
- 同步用 `time.sleep`，异步用 `asyncio.sleep`。

### 4.3 认证

`JWTAuth` 手写 EdDSA JWT，字段与 Go 版一致：

- header：`{"alg": "EdDSA", "kid": ...}`
- payload：`iat`（回退 30 秒）、`exp = iat + 15min`、`sub`（Project ID）、`iss`（Developer ID）
- 签名：`cryptography` 的 Ed25519，私钥从 PKCS#8 PEM 读取，也接受含 `\n` 转义的字符串
- 过期前 1 分钟换新，token 缓存于实例上（`threading.Lock` 保护）

`APIKeyAuth` 写 `X-QW-Api-Key` 头。

### 4.4 错误分类

Go 的 sentinel + `errors.Is` 在 Python 里映射成异常层级，用 `isinstance` 判断：

```
QwxError
├── InvalidConfigError
├── InvalidLocationError
├── InvalidParameterError
├── InvalidResponseError
├── UpstreamError                # status_code / code / title / invalid_params / body
│   ├── UpstreamRejectedError    # 4xx
│   ├── QuotaExceededError       # 429
│   ├── UnauthorizedError        # 401 / 403
│   └── UpstreamUnavailableError # 5xx
└── UpstreamUnavailableError     # 网络错误
```

上游错误体两代都要解析（新一代 `error` 是对象，旧一代 `error` 是字符串），
响应体截断到 2KB，与 Go 版一致。

### 4.5 缓存键：字节级一致

`qwx._cachekey` 直接移植 Go 版：

- 族前缀：`qwx:v1:`、`qwx:aq:v1:`、`qwx:alert:v1:`、`qwx:geo:`、`qwx:tide:`、
  `qwx:indices:`、`qwx:minutely:`、`qwx:solarradiation:v1:`、`qwx:storm:`、
  `qwx:astronomy:`、`qwx:historical:`、`qwx:console:`
- 形状：`族前缀 + ":" + 位置段(以 : 连接) + 参数后缀`
- 参数后缀顺序固定：lang → localTime → n → r → adm → range → city → interval
  → tilt → azimuth → extra → project → credential

**前缀与包名不对齐是既定事实**（`qwx:tide:` 不是 `qwx:ocean:`），移植时原样复制，
不做「顺手修正」。

### 4.6 TTL 优先级

`单次覆盖 > TTLPolicy > 端点默认`，与 Go 版一致。

单次覆盖用上下文管理器实现：

```python
with client.override_ttl(timedelta(seconds=30)):
    weather.current(loc)
```

内部用 `contextvars.ContextVar`，同步与异步都适用。

---

## 5. pydantic 建模规约

```python
class QwxModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
        frozen=True,
    )
```

- **命名**：Python 字段用 snake_case，`to_camel` 生成上游 camelCase 别名。
  少数不规则键用 `Field(alias=...)` 显式覆盖，由 `tools/check_json_tags.py` 校验。
- **可选字段**：Go 的指针 → Python 的 `X | None = None`。缺失与零值可区分。
- **枚举**：只透传不写完备列表（上游会新增）。Go 版本就只校验少数闭集
  （如 `POIType`），这类保留 `Literal` + 客户端校验。
- **比例**：湿度、云量、降水概率在 0~1，字段 docstring 写明「不是百分数」。
  太阳辐射预报的 `humidity` 是百分数，与其他端点不同，单独标注。
- **数值与单位分离**：`Value(value: float, unit: str)`。
- **时间**：保持 `str`。另给 `qwx.timeutil.parse_qtime(s) -> datetime`，
  解析失败返回 `None` 而不是抛错。
- **列表长度**：不假设。docstring 写明「上游可能给得更少」。
- **冻结**：结果模型 `frozen=True`，避免调用方误改。

---

## 6. 两代分治的落地

位置形态按代实现，不共用一套逻辑：

| 代 | 位置形态 | 取值方式 |
| --- | --- | --- |
| 新一代 `/weather/v1/*` 等 | 只认坐标 | `loc.path()` → 纬度在前、经度在后，拼路径 |
| v7 `/v7/*` | 坐标 / LocationID / 站点 ID | `loc.query()` → 经度在前，拼查询参数 |
| GeoAPI `/geo/v2/*` | 坐标 / LocationID / 地名 | `loc.query()` |
| 控制台 | 不认位置 | 无 |

单位、时间基准、错误体、缓存键前缀同样按代分开，与 Go 版一一对应。

---

## 6.5 P0 交付状态

P0 已完成。产出：

| 产物 | 路径 |
| --- | --- |
| 端点契约基线（26 端点） | `contract/endpoints.json` |
| 类型字段契约（85 类型） | `contract/types.json` |
| 端点基线说明 | `docs/contract_baseline.md` |
| Go↔Python 字段映射清单（7 处需显式 alias） | `docs/field_map.md` |
| 契约抽取器 | `tools/extract_go_contract.py` |
| 字段对照工具 | `tools/check_field_map.py` |
| 缓存键与坐标实现 | `src/qwx/_cachekey.py`、`src/qwx/_coord.py` |

抽取器与 Go 仓库的 `docs/endpoints.md` 逐项对账通过：26 个端点的上游路径、
默认 TTL、缓存键前缀全部一致。

## 6.6 P1 交付状态

P1 已完成。核心层产出：

| 产物 | 路径 | 要点 |
| --- | --- | --- |
| 同步与异步客户端 | `src/qwx/client.py` | httpx 双栈，共享配置、URL 拼装、缓存读写与 TTL 解析 |
| 请求与发送器协议 | `src/qwx/request.py` | `Request` 与 `Doer` / `AsyncDoer` |
| 认证 | `src/qwx/auth.py` | 手写 EdDSA JWT（cryptography）与 API KEY |
| 缓存 | `src/qwx/cache.py` | `Cache` 协议与 `MemoryCache` |
| TTL | `src/qwx/ttl.py` | `Endpoint`、`TTLPolicy`、`TTLMap`、单次覆盖（contextvars） |
| 错误层级 | `src/qwx/errors.py` | 两代错误体解析，按状态码归类 |
| 位置与语言 | `src/qwx/location.py`、`src/qwx/lang.py` | 两代位置形态、31 种语言 |
| 日志 | `src/qwx/logger.py` | 标准库 logging，字段名集中定义 |
| 响应模型基类 | `src/qwx/_models.py` | `QwxModel`：别名生成器、额外字段、冻结 |
| 时间解析辅助 | `src/qwx/timeutil.py` | `parse_qtime`，解析失败返回 None |
| 端点族骨架 | `src/qwx/_service.py` | 同步与异步共用同一套端点方法体 |

与 Go 版逐条对齐的实现细节：

- 重试：首次之外最多 3 次，触发条件为 5xx、429 与网络错误。
- 退避：第 i 次等 i 秒；上游给了 `Retry-After`（秒数或 HTTP 日期）且更大就听
  上游的；单次等待上限 30 秒。
- TTL 优先级：单次覆盖 > TTLPolicy > 端点默认；`endpoint` 为空时策略不被调用。
- 缓存值存原始 JSON bytes，与 Go 版共享同一 Redis 时键和值都互通。
- 缓存读写失败降级为直连上游，不让缓存故障中断业务请求。
- 错误分类：4xx 拒绝、429 配额超限、401/403 未授权、5xx 与网络错误上游不可用；
  响应体截断到 2KB。
- 查询参数按键排序后编码，与 Go 的 `url.Values.Encode` 一致。
- JWT：header `alg=EdDSA` + `kid`，payload `iat`（回退 30 秒）、`exp`、`sub`、`iss`；
  过期前 1 分钟换新。

验收：ruff format/check、mypy strict、pytest（155 个用例）全绿；契约抽取器
`--check` 无漂移；`check_field_map.py` 已核对 `Refer` 与 `MetaData` 两个模型。

## 6.7 P2 交付状态

P2 已完成。新一代四个端点族全部落地：

| 族 | 端点 | 包 | 端点常量 |
| --- | --- | --- | --- |
| weather | current / hourly / daily | `src/qwx/v1/weather/` | `EndpointCurrent`、`EndpointHourly`、`EndpointDaily` |
| airquality | current / daily / hourly / station | `src/qwx/v1/airquality/` | `EndpointCurrent`、`EndpointDaily`、`EndpointHourly`、`EndpointStation` |
| alert | current | `src/qwx/v1/alert/` | `Endpoint` |
| solarradiation | forecast | `src/qwx/v1/solarradiation/` | `Endpoint` |

实现要点：

- 端点方法只写一份：`_XxxCalls` mixin 算请求，`XxxService`（同步）与
  `AsyncXxxService`（异步）各带一层带类型的薄包装。
- 缓存键、端点常量、TTL、查询参数与 Go 版逐字一致，且有 golden 测试守着。
- 校验先于请求：越界抛 `InvalidParameterError`，位置不合法抛
  `InvalidLocationError`，都不打上游。
- 模型字段别名全部由 `to_camel` 自动生成（显式 alias 仍是 0 处：7 处显式
  alias 全在 geo 与 v7）。Go 指针字段映射为 `X | None = None`。
- 唯一特殊命名：`POA.global` 的 Python 字段写作 `global_`（`global` 是关键字），
  别名仍是上游的 `global`。

`EndpointStation` 的值是 `airquality/v1/stations`（复数），与上游路径形态不一致
是有意的：端点标识是已发布事实，TTLPolicy 按值匹配。

验收：ruff format/check、mypy strict、pytest（272 个用例）全绿；
`check_field_map.py` 43 个模型与 Go 契约一致。

## 6.8 P3 交付状态

P3 已完成。GeoAPI 与控制台两个端点族落地：

| 族 | 端点 | 包 | 端点常量 |
| --- | --- | --- | --- |
| geo | lookup_city / lookup_poi / poi_range / top_cities | `src/qwx/geo/` | `EndpointCity`、`EndpointPOI`、`EndpointPOIRange`、`EndpointTopCities` |
| console | finance / stats | `src/qwx/console/` | `EndpointFinance`、`EndpointStats` |

实现要点：

- geo 是唯一认地名的接口族：位置形态用 `loc.query()`（经度在前），坐标对 /
  LocationID / 地名三种都收；`poi_range` 必须带坐标。
- POI 类型是闭集，用 `POIType(str, Enum)`：`scenic` / `CSTA` / `TSTA`，
  闭集外抛 `InvalidParameterError`。
- 显式 alias 4 处（geo 部分）：`CityResult.locations` → `location`、
  `POIResult.pois` → `poi`、`RangeResult.pois` → `poi`、
  `TopCityResult.cities` → `topCityList`。
- console 的 `project` 与 `credential` 互斥，客户端挡下，不打上游。
- `ResourcePlan.requests` 上游可能给字符串或数字，Python 用 `int | float | str`
  收两种形态（Go 用 `json.Number`）。

验收：ruff format/check、mypy strict、pytest（335 个用例）全绿；
缓存键与 Go 的 golden 断言逐字一致（独立复核过 geo 8 条、console 4 条）。

## 7. 分阶段实施

每阶段独立可验收，验收不过不进入下一阶段。

| 阶段 | 内容 | 产出 | 验收 |
| --- | --- | --- | --- |
| P0 | 项目骨架 + 契约基线 | pyproject、ruff/mypy/pytest 配置、`_coord`、`_cachekey`、golden 键测试 | 缓存键与 Go 版逐字相同 |
| P1 | 核心层 | client、request、auth、cache、ttl、errors、location、lang、logger | 核心层单测通过，JWT 签名可验 |
| P2 | 新一代 | `qwx.v1` 共享类型 + weather / airquality / alert / solarradiation | 模型与 Go 版字段一一对照 |
| P3 | GeoAPI + 控制台 | `qwx.geo`、`qwx.console` | 同上 |
| P4 | 旧一代 | `qwx.v7` 六个族 | 同上 |
| P5 | 收尾 | README 中英、`docs/` 七篇、examples、live 冒烟、CI、PyPI 发布配置 | 全量测试 + 文档漂移检查通过 |

工作量估计：源码约 4500 行、测试约 3500 行。P0–P1 约 2 天，P2 约 3 天，
P3 约 1 天，P4 约 3 天，P5 约 2 天。

进度：P0、P1、P2、P3 已完成（见 §6.5~§6.8），下一步是 P4 旧一代 v7 六个族。

---

## 8. 契约与漂移防线

Go 版靠 `internal/endpoints` 生成端点表并做漂移测试。Python 版补三道防线：

1. **缓存键 golden 测试**：把 Go 版 `internal/cachekey` 测试里的键字面量
   抄成 Python 常量表，逐一断言。两边键相同 → 共享 Redis 不会串味。
2. **Go json tag ↔ Python alias 对照**：`tools/check_json_tags.py` 扫 Go 源码的
   `json:"..."` tag 集合，与 Python 模型的 alias 集合比对，缺一个就失败。
   这道检查防的是「字段漏映射」——最隐蔽的一类移植 bug。
3. **端点表生成**：`tools/gen_endpoints.py` 从 Python 侧的端点注册表生成
   `docs/endpoints.md`，生成物入库并由测试校验无漂移。

Python 侧额外维护一份端点注册表（每个端点的路径、位置形态、默认 TTL、
缓存前缀、端点常量），它是生成器与文档的唯一真源。

---

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
| --- | --- | --- |
| 字段漏映射（Go 有、Python 无） | 静默丢数据 | §8 的 json tag 对照检查 |
| `to_camel` 与上游键不匹配 | 解析不到字段 | 逐族核对，不规则键显式 `Field(alias=...)` |
| 缓存键与 Go 版不一致 | 共享 Redis 时互相覆盖 | golden 测试 |
| 同步/异步行为分叉 | 异步路径出线上问题 | 端点层单实现，只核心层双份 |
| 上游怪癖漏移植 | 用户踩 Go 版已修的坑 | `docs/gotchas.md` 46 条逐条落到 docstring 与测试 |
| pydantic 校验太严 | 合法响应被判非法 | `extra="allow"`、可选字段宽松、时间不解析 |

`docs/gotchas.md` 的 46 条是迁移清单的直接来源，逐条核对：
新一代经纬倒置、默认 UTC、湿度比例、逐日无 intensity、潮汐当地日期、
POI 无数据回 400、生活指数只支持 1d/3d、分钟级降水只覆盖中国、
太阳辐射无 lang 参数且上限 72、台风 basin 只支持 NP、
日出日落可能为 null、历史天气只认 LocationID 且字段名是 `weatherDaily`、
控制台 `project` 与 `credential` 互斥、AQI 不同标准量纲不同，等等。

---

## 10. 验收标准

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy src/qwx
uv run pytest -q                    # 单元测试
uv run pytest -m live               # 联网冒烟，需真实凭据
uv run python tools/check_json_tags.py   # 与 Go 版字段对照
```

发布前：

- `docs/endpoints.md` 与注册表一致，无漂移。
- README 中英的「支持的接口」表与 26 个端点一致。
- 缓存键 golden 测试与 Go 版逐字一致。

---

## 11. 不做的事

- 不提供 Go 与 Python 的运行时混用层。
- 不改缓存键字面量与端点常量值（已发布即不可变）。
- 不为「上游新增端点」提前写代码，只按 `docs/contract.md` 的停服清单核对。
- 首版不写异步批量请求与并发限流器。
