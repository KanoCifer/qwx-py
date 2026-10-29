# P2 端点族实现规约

新一代（v1）四个端点族按本规约并行实现。规约里的每条都是硬约束：
与 Go 版语义对等是迁移的第一目标。

参考实现：Go 仓库 `/Users/liudetao/Code/qwx` 的 `v1/weather`、`v1/airquality`、
`v1/alert`、`v1/solarradiation` 四个包。Python 仓库：`/Users/liudetao/Code/qwx-py`。

## 1. 目录布局

```text
src/qwx/v1/
├── __init__.py            # 只导出共享类型，不要塞端点族
├── types.py               # Metadata / Value / Options，核心层已提供，不要改
├── weather/
│   ├── __init__.py        # 导出本族公开符号
│   ├── types.py           # 模型 + Options + 端点常量
│   └── client.py          # 服务客户端 + 端点方法
├── airquality/
├── alert/
└── solarradiation/

tests/
├── test_v1_weather_types.py
├── test_v1_weather_client.py
└── ...（其余族同构）
```

一个包 = 一个资源族；定义与实现分离（`types.py` 放结果类型、参数类型与常量，
`client.py` 放服务客户端与端点方法）。

## 2. 命名规则

| 东西 | 规则 | 例子 |
| --- | --- | --- |
| 模型类名 | 与 Go 类型名逐字相同 | `CurrentWeather`、`WindGust`、`POA` |
| 方法名 | Go 方法名的 snake_case | `Current` → `current`、`DailyForecast` → `daily_forecast` |
| 端点常量 | 包里有多个端点叫 `EndpointXxx`，只有一个叫 `Endpoint` | `EndpointCurrent`、`Endpoint` |
| 端点常量的值 | 与 Go 里的字符串逐字相同 | `Endpoint("weather/v1/current")` |
| 服务类 | `<族名>Service`（同步）、`Async<族名>Service`（异步） | `WeatherService`、`AsyncWeatherService` |

`contract/endpoints.json` 已经给出每个端点的 `py_method`、`endpoint_constant`、
`endpoint`（常量值）、`upstream_path`、`default_ttl_seconds`、`cache_key_template`、
`cache_prefix`、`location_shape`，直接照抄，不要自己推断。

## 3. 模型规则

- 基类用 `qwx.QwxModel`（别名生成器 to_camel、`extra="allow"`、frozen）。
- 字段名照 `docs/field_map.md` 给的 Python 字段名；别名除该文档标「显式」的
  7 处外自动生成，不要手写 `Field(alias=...)`。
- Go 指针字段 → Python `X | None = None`（缺失与零值可区分）。
- Go 非指针标量 → Python 有默认值（`0` / `""` / `[]`）。
- 时间字段保持 `str`，不要转 datetime（解析辅助是 `qwx.parse_qtime`）。
- 湿度、云量、降水概率是 0~1 的比例，不是百分数 —— docstring 要写明。
- 列表长度不假设 —— docstring 要写明「上游可能给得更少」。
- 枚举只透传，不写完备列表（上游会新增）。
- 每个模型与字段都要有中文 docstring，说明语义与上游怪癖。

## 4. Options（每族的可选参数）

Go 里 `v1/weather.Options` 与 `v1/alert.Options` 是 `v1.Options` 的类型别名，
Python 侧直接复用：`from qwx.v1.types import Options`。

| 族 | Options | 字段 |
| --- | --- | --- |
| weather | 复用 `qwx.v1.Options` | `lang`、`local_time` |
| alert | 复用 `qwx.v1.Options` | `lang`、`local_time` |
| airquality | 本族自定义 | `lang` |
| solarradiation | 本族自定义 | `local_time`、`interval`、`tilt`、`azimuth`、`extra` |

自建的 Options 用 `@dataclass(frozen=True, slots=True)`，字段名 snake_case，
默认值与 Go 的零值一致（`lang` 默认 `Lang.UNSPECIFIED`）。

## 5. 缓存键

键的字面量是已发布事实，**逐字不可改**。

```python
from qwx._cachekey import Family, Key, Params

key = str(
    Key(Family.WEATHER)
    .path("current")
    .path_coord(lat, lon)          # 纬度在前
    .params(Params(lang="zh"))
)
```

- 族前缀：`Family.WEATHER`（`qwx:v1:`）、`Family.AIR_QUALITY`（`qwx:aq:v1:`）、
  `Family.ALERT`（`qwx:alert:v1:`）、`Family.SOLAR_RADIATION`（`qwx:solarradiation:v1:`）。
- 坐标段用 `path_coord(lat, lon)`，经度在前的新一代路径用 `loc.path()`。
- 计数段用 `count("h", hours)` / `count("d", days)` —— 预报条数进键，
  `hours=24` 与 `hours=48` 是两份数据，共键会串。
- `Params` 字段：`lang`、`local_time`、`number`、`radius`、`adm`、`range`、
  `city`、`interval`、`tilt`、`azimuth`、`extra`、`project`、`credential`。
  `tilt`/`azimuth` 是 `int | None`：None 表示不传，0 是合法取值。
- `Params.query()` 给出上游查询参数，`Params.suffix()` 给出键后缀。

## 6. 请求

```python
from qwx.request import Request

request = Request(
    method="GET",
    path=f"/weather/v1/current/{lat}/{lon}",
    query=query,
    endpoint=EndpointCurrent,
    cache_key=cache_key,
    ttl=timedelta(seconds=600),
    out=CurrentWeather,
)
```

- `query` 由 `params.query()` 生成，再按端点需要补 `hours` / `days`。
- 客户端会按键排序后编码查询串。

## 7. 服务类骨架（照抄这个形状）

同步与异步共用同一套端点方法体，只是发送层一个同步一个协程：

```python
from typing import Any, cast

from qwx._service import Service


class _WeatherCalls(Service):
    """天气端点族的方法体。同步与异步共用。"""

    def _current_call(self, loc: Location, opts: Options | None = None) -> Any:
        ...  # 校验 → 算路径/查询/缓存键 → self._call(request)


class WeatherService(_WeatherCalls):
    """同步天气服务客户端。"""

    def current(self, loc: Location, opts: Options | None = None) -> CurrentWeather:
        return cast(CurrentWeather, self._current_call(loc, opts))


class AsyncWeatherService(_WeatherCalls):
    """异步天气服务客户端。"""

    async def current(self, loc: Location, opts: Options | None = None) -> CurrentWeather:
        return cast(CurrentWeather, await self._current_call(loc, opts))
```

规则：

- 客户端先校验：参数越界抛 `InvalidParameterError`，位置不合法抛
  `InvalidLocationError`，**不打上游**。校验顺序与 Go 一致。
- `opts` 允许为 None，表示用上游默认（语言与当地时间都不传）。
- 同步服务类配 `qwx.Client`，异步服务类配 `qwx.AsyncClient`。
- `self._call(request)` 来自 `qwx._service.Service`，同步返回模型、异步返回协程。

## 8. docstring 要求

每个端点方法写清：上游路径、位置形态、参数范围、缓存键、默认 TTL、
上游怪癖（例如太阳辐射没有 lang 参数、湿度是比例）。中文书写。

## 9. 测试要求

每个族两个测试文件：

- `tests/test_v1_<族>_types.py`：给一份真实形状的 JSON，断言模型能解析出字段；
  断言可选字段缺失时是 None；断言未知字段被保留（`extra="allow"`）。
- `tests/test_v1_<族>_client.py`：用 `httpx.MockTransport` 断言
  请求路径、查询参数、**缓存键完整字面量**、参数越界报错、缓存命中不打上游。

参考现有测试的写法：`tests/test_client.py`（MockTransport 与 `make_client` 辅助）
与 `tests/test_cachekey.py`（缓存键 golden）。

## 10. 验收命令

在 `/Users/liudetao/Code/qwx-py` 下执行：

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
python3 tools/check_field_map.py
```

四个都要过。`check_field_map.py` 会把你的模型与 Go 契约逐字段对照，
少字段、多字段都会报错。

## 11. 边界

- 只改自己那个族的目录与自己那两个测试文件。
- 不要改 `src/qwx/v1/types.py`、`src/qwx/v1/__init__.py`、`src/qwx/*.py`、
  别的族的目录、`tools/`、`contract/`、`docs/`。
- 不要 git commit —— 统一由主代理提交。
- 不引入第三方依赖（核心包只用 httpx + pydantic + 标准库）。

## 12. 四个族的事实表

| 族 | 方法 | 上游路径 | 端点常量 | TTL（秒） | 缓存键 | 位置形态 |
| --- | --- | --- | --- | --- | --- | --- |
| weather | `current` | `/weather/v1/current/{lat}/{lon}` | `EndpointCurrent` = `weather/v1/current` | 600 | `qwx:v1:current:{lat},{lon}` + 参数后缀 | 只认坐标 |
| weather | `hourly` | `/weather/v1/hourly/{lat}/{lon}` | `EndpointHourly` = `weather/v1/hourly` | 3600 | `qwx:v1:hourly:{lat},{lon}:h{hours}` + 参数后缀 | 只认坐标 |
| weather | `daily` | `/weather/v1/daily/{lat}/{lon}` | `EndpointDaily` = `weather/v1/daily` | 3600 | `qwx:v1:daily:{lat},{lon}:d{days}` + 参数后缀 | 只认坐标 |
| airquality | `current` | `/airquality/v1/current/{lat}/{lon}` | `EndpointCurrent` = `airquality/v1/current` | 1800 | `qwx:aq:v1:current:{lat},{lon}` + 参数后缀 | 只认坐标 |
| airquality | `daily` | `/airquality/v1/daily/{lat}/{lon}` | `EndpointDaily` = `airquality/v1/daily` | 3600 | `qwx:aq:v1:daily:{lat},{lon}` + 参数后缀 | 只认坐标 |
| airquality | `hourly` | `/airquality/v1/hourly/{lat}/{lon}` | `EndpointHourly` = `airquality/v1/hourly` | 3600 | `qwx:aq:v1:hourly:{lat},{lon}` + 参数后缀 | 只认坐标 |
| airquality | `station` | `/airquality/v1/stations/{station_id}` | `EndpointStation` = `airquality/v1/stations` | 1800 | `qwx:aq:v1:station:{station_id}` + 参数后缀 | 站点 ID |
| alert | `current` | `/weatheralert/v1/current/{lat}/{lon}` | `Endpoint` = `weatheralert/v1/current` | 300 | `qwx:alert:v1:{lat},{lon}` + 参数后缀 | 只认坐标 |
| solarradiation | `forecast` | `/solarradiation/v1/forecast/{lat}/{lon}` | `Endpoint` = `solarradiation/v1/forecast` | 3600 | `qwx:solarradiation:v1:forecast:{lat},{lon}:h{hours}` + 参数后缀 | 只认坐标 |

参数上限（超出抛 `InvalidParameterError`，不打上游）：

| 族 | 参数 | 范围 |
| --- | --- | --- |
| weather | `hours` | 1~240 |
| weather | `days` | 1~10 |
| solarradiation | `hours` | 1~72 |
| solarradiation | `interval` | 0（用默认）或 15/30/60 |
| solarradiation | `tilt` | 0~90 |
| solarradiation | `azimuth` | 0~359 |
| solarradiation | `extra` | 只认 `weather`、`poa`，逗号分隔，不许重复；含 `poa` 时 tilt 与 azimuth 都得给 |
| airquality | `station_id` | 不能为空 |
