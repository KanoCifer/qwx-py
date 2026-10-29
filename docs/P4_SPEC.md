# P4 端点族实现规约：旧一代 v7

P4 落地旧一代（/v7/*）六个端点族：`qwx.v7.astronomy`、`qwx.v7.historical`、
`qwx.v7.indices`、`qwx.v7.minutely`、`qwx.v7.ocean`、`qwx.v7.storm`。

**两代分治是硬约束**：v7 与新一代的字段形态、单位、时间基准、位置形态、
缓存键前缀全都不一样，不要共用逻辑，也不要把新时代的写法套到 v7 上。

参考：Go 仓库 `/Users/liudetao/Code/qwx` 的 `v7/` 六个包；
P2 规约 `docs/P2_SPEC.md` 第 2~10 节同样适用（命名、模型规则、缓存键、
请求构造、服务类骨架、docstring、测试、验收）。

## 1. v7 与新一代的差异

| 维度 | 新一代 v1 | 旧一代 v7 |
| --- | --- | --- |
| 位置形态 | 只认坐标，路径参数 `{纬度}/{经度}` | 查询参数 `location=经度,纬度`，按端点还认 LocationID / 站点 ID |
| 取位置 | `loc.path()` | `loc.query()` |
| 数值与单位 | 分开：`{"value": 31.7, "unit": "°C"}` | 拼在一个字符串里：`"31.7°C"` |
| 湿度等比例 | 0~1 | v7 给的是百分数 |
| 时间 | 默认 UTC，要当地时间传 localTime | 本地时间字符串 |
| 缓存键前缀 | `qwx:v1:`、`qwx:aq:v1:`、`qwx:alert:v1:`、`qwx:solarradiation:v1:` | `qwx:astronomy:`、`qwx:historical:`、`qwx:indices:`、`qwx:minutely:`、`qwx:tide:`、`qwx:storm:` |

注意潮汐族的键前缀是 `qwx:tide:`（不是 `qwx:ocean:`）—— 已发布字面量，
逐字不可改。

## 2. 目录布局

```text
src/qwx/v7/
├── __init__.py          # 只做命名空间，不放 Go 文件
├── astronomy/
│   ├── __init__.py
│   ├── types.py
│   └── client.py
├── historical/
├── indices/
├── minutely/
├── ocean/
└── storm/

tests/
├── test_v7_astronomy_types.py
├── test_v7_astronomy_client.py
├── ...（其余族同构）
```

`src/qwx/v7/__init__.py` 只是命名空间，不放实现（与 Go 的 `v7/` 目录同构）。

## 3. 六个族的事实表

```text
| 族 | 方法 | 上游路径 | 端点常量 | TTL(秒) | 缓存键 | 位置形态 |
| astronomy | sun | /v7/astronomy/sun | EndpointSun = "v7/astronomy/sun" | 86400 | qwx:astronomy:sun:{location}:{date} | 坐标 / LocationID |
| astronomy | moon | /v7/astronomy/moon | EndpointMoon = "v7/astronomy/moon" | 86400 | qwx:astronomy:moon:{location}:{date} + 参数后缀 | 坐标 / LocationID |
| astronomy | solar_elevation_angle | /v7/astronomy/solar-elevation-angle | EndpointAngle = "v7/astronomy/solar-elevation-angle" | 86400 | qwx:astronomy:angle:{location}:{date}:{time}:{tz}:{alt} | 只认坐标 |
| historical | weather | /v7/historical/weather | Endpoint = "v7/historical/weather" | 86400 | qwx:historical:weather:{id}:{date} + 参数后缀 | 只认 LocationID |
| indices | indices / indices_multi | /v7/indices/{days}d | Endpoint = "v7/indices" | 3600 | qwx:indices:{location}:t{type}:d{days} + 参数后缀 | 只认坐标对 |
| minutely | minutely | /v7/minutely/5m | Endpoint = "v7/minutely/5m" | 300 | qwx:minutely:{location} + 参数后缀 | 坐标 |
| ocean | tide | /v7/ocean/tide | Endpoint = "v7/ocean/tide" | 3600 | qwx:tide:{station_id}:{date} | 站点 ID |
| storm | list | /v7/tropical/storm-list | EndpointList = "v7/tropical/storm-list" | 86400 | qwx:storm:list:{basin}:{year} | 无 |
| storm | forecast | /v7/tropical/storm-forecast | EndpointForecast = "v7/tropical/storm-forecast" | 3600 | qwx:storm:forecast:{storm_id} | 无 |
| storm | track | /v7/tropical/storm-track | EndpointTrack = "v7/tropical/storm-track" | 3600 | qwx:storm:track:{storm_id} | 无 |
```

- `v7/indices` 包的两个方法（单类型与多类型）共用同一个端点常量 `Endpoint`。
- 端点常量值与 Go 逐字相同（`v7/indices` 的值是 `v7/indices`，不含 `{days}d`）。

## 4. 各族的参数与怪癖

### astronomy

- `date` 是 8 位日期（YYYYMMDD）；上游最多接受**未来 60 天（含今天）**，超范围由上游拒绝。
- 日出日落可能为 null（高纬度与极昼极夜）→ Go 指针字段映射成 `X | None = None`。
- `solar_elevation_angle` 只认坐标，还要 `time`（HHMM，4 位）、`tz`（时区偏移，
  如 `+08:00`）、`alt`（海拔，米，必填）。
- `sun` 没有语言参数（键里也没有参数后缀）；`moon` 有（多语言月相文案）。
- 缓存键的 `{location}` 段用 `loc.query()`。

### historical

- `location` 只认 LocationID，坐标对与地名都被拒 → 传非 LocationID 抛
  `InvalidLocationError`。
- 上游只给最近 10 天、**不含今天**的历史数据。
- 响应里的两块字段名是 `weatherDaily` 与 `weatherHourly`，不是 `daily`/`hourly` →
  **必须显式 alias**：`daily: ... = Field(alias="weatherDaily")`、
  `hourly: ... = Field(alias="weatherHourly")`。

### indices

- `days` 只支持 1 与 3（实测 2d/7d/10d/15d/30d 全 404），其它值抛
  `InvalidParameterError`。
- `type` 是 0~16 的闭集，越界抛 `InvalidParameterError`。
- 只认坐标对；传裸经度（如 `121.47`）上游 400 → 客户端要挡。
- 两个方法：单类型与多类型（一次查多种指数），共用端点常量。

### minutely

- 分钟级降水**只覆盖中国区域**，境外坐标上游没有数据。
- TTL 只有 5 分钟。

### ocean（潮汐）

- `location` 是潮汐站点 ID（如 `P2352`），不是坐标。
- `date` 必须用**站点当地日期**：潮汐窗口下界是站点当地当天，北京时间
  00:00–08:00 会落到「昨天」。
- 缓存键前缀是 `qwx:tide:`。

### storm（台风）

- `basin` 目前只支持 `NP`（中国沿海流域），传别的上游 400 → 客户端只放行 NP。
- 台风已结束时预报返回**空列表**，不是错误：先查列表再决定要不要查预报。
- `ListResult` 的列表字段 json tag 是 `storm`（Go 字段名 `Storms`）→
  **必须显式 alias**：`storms: list[Storm] = Field(default_factory=list, alias="storm")`。

## 5. 必须显式 alias 的字段（v7 部分）

| 模型 | Python 字段 | alias |
| --- | --- | --- |
| `v7/historical.Result` | `daily` | `weatherDaily` |
| `v7/historical.Result` | `hourly` | `weatherHourly` |
| `v7/storm.ListResult` | `storms` | `storm` |

其余字段别名由 `to_camel` 自动生成。

## 6. 验收

在 `/Users/liudetao/Code/qwx-py` 下执行：

```bash
.venv/bin/ruff format --check src/qwx/v7 tests
.venv/bin/ruff check src/qwx/v7 tests
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
python3 tools/check_field_map.py
```

四个都要过。`check_field_map.py` 会把模型与 Go 契约逐字段对照。

## 7. 边界

- 只改自己那个族的目录与自己那两个测试文件。
- 不要改 `src/qwx/` 下其它文件（含 `src/qwx/v1/`、`src/qwx/v7/__init__.py`）、
  其它族的目录、tools/、contract/、docs/。
- 不要 git commit。
