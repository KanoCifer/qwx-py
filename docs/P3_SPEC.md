# P3 端点族实现规约：GeoAPI 与控制台

P3 落地两个端点族：`qwx.geo`（GeoAPI 城市/POI 检索）与 `qwx.console`
（控制台财务汇总与请求量统计）。规约与 P2 同源，核心约束不变：

- 与 Go 版语义对等：端点集合、缓存键字节、端点常量值、错误分类、TTL 优先级一致。
- 一个包 = 一个资源族；定义与实现分离（`types.py` + `client.py`）。
- 校验先于请求，越界不打上游。

参考：Go 仓库 `/Users/liudetao/Code/qwx` 的 `geo/` 与 `console/` 包；
P2 规约 `docs/P2_SPEC.md` 的第 2~10 节同样适用（命名、模型、Options、
缓存键、请求、服务类骨架、docstring、测试、验收）。

## 1. 目录布局

```text
src/qwx/geo/
├── __init__.py
├── types.py
└── client.py
src/qwx/console/
├── __init__.py
├── types.py
└── client.py

tests/
├── test_geo_types.py
├── test_geo_client.py
├── test_console_types.py
└── test_console_client.py
```

## 2. geo 端点

```text
| 方法 | 上游路径 | 端点常量 | TTL(秒) | 缓存键 | 位置形态 |
| lookup_city | /geo/v2/city/lookup | EndpointCity = "geo/v2/city/lookup" | 86400 | qwx:geo:city:{location} + 参数后缀 | 坐标 / LocationID / 地名 |
| lookup_poi | /geo/v2/poi/lookup | EndpointPOI = "geo/v2/poi/lookup" | 86400 | qwx:geo:poi:{typ}:{location} + 参数后缀 | 坐标 / LocationID / 地名 |
| poi_range | /geo/v2/poi/range | EndpointPOIRange = "geo/v2/poi/range" | 86400 | qwx:geo:poirange:{typ}:{location} + 参数后缀 | 只认坐标 |
| top_cities | /geo/v2/city/top | EndpointTopCities = "geo/v2/city/top" | 86400 | qwx:geo:topcity + 参数后缀 | 无 |
```

- GeoAPI 是唯一认地名的接口族：位置形态用 `loc.query()`（经度在前），
  坐标对 / LocationID / 地名三种都收。
- `poi_range` 必须带坐标，否则抛 `InvalidLocationError`。
- 查询参数：`location` 恒有；`lookup_poi` 与 `poi_range` 还要 `type`。
- 缓存键的 {location} 段就是 `loc.query()` 的结果；{typ} 是 POI 类型代码。

### POI 类型

```python
class POIType(str, Enum):
    SCENIC = "scenic"   # 景点
    CSTA = "CSTA"       # 综合观测站
    TSTA = "TSTA"       # 潮汐观测站
```

闭集：传别的类型抛 `InvalidParameterError`。上游查询串与缓存键都发代码
本身（`scenic` / `CSTA` / `TSTA`）。

### geo 的 Options

```python
@dataclass(frozen=True, slots=True)
class Options:
    lang: Lang = Lang.UNSPECIFIED
    number: int = 0          # 返回条数上限，0 用上游默认（10）
    adm: str = ""            # 上级行政区划 LocationID，排除重名城市
    range: str = ""          # 搜索范围，ISO 3166 国家代码，如 "cn"、"world"
    city: str = ""           # 限定 POI 所在城市，城市名或 LocationID


@dataclass(frozen=True, slots=True)
class POIRangeOptions:
    lang: Lang = Lang.UNSPECIFIED
    number: int = 0
    radius: int = 0          # 半径（公里），0 用上游默认
```

哪个参数进哪个端点，与 Go 一致：

| 端点 | 进 Params 的字段 |
| --- | --- |
| lookup_city | lang、number、adm、range |
| lookup_poi | lang、number、city |
| poi_range | lang、number、radius |
| top_cities | lang、number、range |

半径语义：`Params.radius` 为 None 表示端点没有半径参数；非 None 时半径进键，
半径为 0 只进键、不上报（上游按自己的默认值处理）。所以 `poi_range` 的
`radius` 永远要传进 Params（哪怕是 0）。

### geo 的模型

类名与 Go 逐字相同：`Place`、`CityResult`、`POIResult`、`RangeResult`、
`TopCityResult`。四个检索端点共享 `Place` 类型。

**这 4 个字段必须显式写 alias**（Go 字段名与 json tag 不一致）：

| 模型 | Python 字段 | alias |
| --- | --- | --- |
| `CityResult` | `locations` | `location` |
| `POIResult` | `pois` | `poi` |
| `RangeResult` | `pois` | `poi` |
| `TopCityResult` | `cities` | `topCityList` |

写法：`pois: list[Place] = Field(default_factory=list, alias="poi")`。

`refer` 字段用根包的 `qwx.Refer`。

### geo 的上游怪癖（必须写进 docstring）

- 上游在该类型附近无数据时回 **400 "No Such Location"**，不是空列表 —— 内陆城市
  查 TSTA/CSTA 会 400，沿海城市才查得到。调用方要按错误处理。
- `range` 留空时上游在所有城市里搜，要查境外城市得传 "world"。
- `city` 是精准匹配，匹配不上上游返回空。
- 坐标反查：传 "经度,纬度" 拿该点所在的城市。

## 3. console 端点

```text
| 方法 | 上游路径 | 端点常量 | TTL(秒) | 缓存键 | 位置形态 |
| finance | /finance/v1/summary | EndpointFinance = "finance/v1/summary" | 3600 | qwx:console:finance | 无 |
| stats | /metrics/v1/stats | EndpointStats = "metrics/v1/stats" | 3600 | qwx:console:stats + 参数后缀 | 无 |
```

- 控制台 API 不认位置，没有位置参数。
- `stats` 的 `project` 与 `credential` **互斥**：两个都填在客户端被挡下，
  抛 `InvalidParameterError`，不打上游；都留空统计帐号下所有项目与凭据。
- 缓存键：`finance` 没有参数后缀；`stats` 的后缀只含 project / credential。

### console 的 Options

```python
@dataclass(frozen=True, slots=True)
class StatsOptions:
    project: str = ""
    credential: str = ""
```

### console 的模型

类名与 Go 逐字相同：`FinanceResult`、`AccruedCharges`、`PendingBill`、
`SavingsPlan`、`ResourcePlan`、`StatsResult`、`APICount`。

`metadata` 字段用根包的 `qwx.MetaData`。

### console 的上游怪癖（必须写进 docstring）

- 凭据默认没有权限访问这两个端点：帐号所有者要在控制台
  「项目管理 - 凭据 - 控制台权限」里勾选对应权限，否则上游拒绝。
- 返回的数据截止至上一个小时或更晚，与控制台网页显示可能有 1 小时以上延迟，
  以 `as_of` 为准。

## 4. 验收

在 `/Users/liudetao/Code/qwx-py` 下执行：

```bash
.venv/bin/ruff format --check src/qwx/geo src/qwx/console tests
.venv/bin/ruff check src/qwx/geo src/qwx/console tests
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
python3 tools/check_field_map.py
```

四个都要过。`check_field_map.py` 会把模型与 Go 契约逐字段对照。

## 5. 边界

- 只改 `src/qwx/geo/`、`src/qwx/console/` 与自己那四个测试文件。
- 不要改 `src/qwx/` 下的核心文件、其它族的目录、tools/、contract/、docs/。
- 不要 git commit。
