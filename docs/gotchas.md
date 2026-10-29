# 上游怪癖分诊表

按症状索引。每条给出根因一句话、处理方式与代码位置，规则的完整表述在对应 docstring 里。

| 症状 | 根因 | 处理 | 位置 |
| --- | --- | --- | --- |
| 400，`invalidParams:["longitude","latitude"]` | 经纬倒置：新一代路径是 `{纬度}/{经度}`，v7 与 GeoAPI 查询参数是 `"经度,纬度"` | 新一代用 `Location.path()`，旧代用 `Location.query()` | `src/qwx/location.py` `path` / `query` |
| 404 且响应体为空 | 传了 LocationID，新一代只认坐标 | 先 `geo.lookup_city` 换坐标再调新一代 | `src/qwx/v1/weather/client.py` `current` 注释 |
| 时间整整差 8 小时，值形如 `2026-10-21T05:00Z` | 新一代默认给 UTC | 传 `local_time=True` | `src/qwx/v1/types.py` `Options` |
| 湿度 `0.69` 被当成 69% 直接展示 | 新一代湿度与云量是 0~1 比例 | 按比例换算后再展示 | `src/qwx/v1/weather/types.py` `CurrentWeather.humidity` |
| 逐日预报的降水强度恒为 0 | 逐日预报的白天/夜间时段上游没有 `intensity` 字段 | 判断 `Precipitation.intensity` 不是 `None` 再取值 | `src/qwx/v1/weather/types.py` `Precipitation.intensity` |
| 潮汐查询 400 | `date` 用了 UTC 日期，潮汐窗口下界是站点当地当天；北京时间 00:00–08:00 会落到「昨天」 | 用站点当地日期 | `src/qwx/v7/ocean/client.py` `tide` |
| POI 检索 400 `No Such Location`，不是空列表 | 该类型附近确实没有 POI：内陆城市查 TSTA / CSTA 必 400，沿海城市（舟山、高雄）才查得到 | 按错误处理，查询前先判断城市临海 | `src/qwx/geo/client.py` `lookup_poi` / `poi_range` |
| 生活指数 404 | `days` 只支持 1 与 3，实测 2d / 7d / 10d / 15d / 30d 全 404 | 只传 1 或 3 | `src/qwx/v7/indices/client.py` `indices` |
| 生活指数 400 | 传了裸经度（如 `121.47`），上游只认坐标对 | 用 `"经度,纬度"` | `src/qwx/v7/indices/client.py` `indices` |
| 分钟级降水无数据 | 只覆盖中国区域，境外坐标上游没有数据 | 境外场景别调这个端点 | `src/qwx/v7/minutely/client.py` `minutely` |
| 找不到潮汐 / 生活指数 / 分钟级降水的新一代路径 | 这三个端点至今只有 v7：实测 `/weather/v1/indices/*`、`/v1/indices/*`、`/ocean/v1/tide/*` 全 404 | 用 v7 版本 | `src/qwx/v7/` 下的三个子模块 |
| 401 / 403 | 凭据与控制台不一致，或 JWT 缺 `iss`（Developer ID） | 见 `auth.md` 排查顺序 | `src/qwx/auth.py` |
| 控制台接口 403 | 凭据默认没有控制台权限，要帐号所有者在控制台「项目管理 - 凭据 - 控制台权限」里开通 | 先开权限再调 | `src/qwx/console/client.py` `finance` / `stats` |
| 404 且提示路径不对，GeoAPI 查不到 | GeoAPI 在专属 Host 下的路径是 `/geo/v2/*`，旧公共域名才是 `/v2/*` | 用控制台分配的 Host 拼路径，不要自己改前缀 | `src/qwx/geo/client.py` |
| 公共域名突然不可用 | `devapi.qweather.com` 2026-01 停服，`api.qweather.com` 与 `geoapi.qweather.com` 2026-06 停服 | 换成控制台「设置」页的专属 Host | `src/qwx/client.py` `Client` |
| 缓存返回了别的请求的数据 | 键漏了影响结果的参数（`hours`、`days`、`lang`、`localTime`、`number`、`radius`） | 键要包含全部影响结果的参数 | `docs/caching.md` |
| 改了 TTL 但旧数据还在 | 缓存键不含 TTL，已写入的条目按写入时的 TTL 到期 | 换缓存实例或手动清键 | `docs/caching.md` 「TTL 与缓存键」 |
| 某个端点不缓存，其他端点照旧 | 策略返回 0 表示该端点不缓存 | `qwx.TTLMap({端点常量: timedelta(0)})` | `src/qwx/ttl.py` `TTLMap` |
| 返回条数比请求的少 | 上游可以给更少，SDK 不补齐 | 不假设长度 | `src/qwx/v1/weather/types.py` `HourlyForecast.hours`、`src/qwx/v1/airquality/types.py` `DailyForecast.days` |
| 坐标 `(0, 0)` 报 `qwx.InvalidLocationError` | `has_coordinates()` 用「lat 或 lon 非零」判定，`(0, 0)` 被当成无坐标 | 已知边界；该坐标点走 `Location(id=...)` 之外的端点前先确认 | `src/qwx/location.py` `has_coordinates` |
| 预警查不到 | 预警只认坐标，传 LocationID 或地名上游直接拒绝 | 先 `geo.lookup_city` 换坐标再调 `alert.current` | `src/qwx/v1/alert/client.py` `current` |
| 太阳辐射预报的湿度按比例换算后不对 | 太阳辐射预报的 `humidity` 是百分数（0~100），新一代其他端点给的是 0~1 比例 | 按百分数展示 | `src/qwx/v1/solarradiation/types.py` `Weather.humidity` |
| 太阳辐射预报回 400 | 这一族没有 `lang` 参数，上游不返回文字描述，多传会被拒 | 别传 lang | `src/qwx/v1/solarradiation/client.py` `forecast` |
| 读 OpenAPI 以为 hours 上限是 60 | 整份 spec 只有这一处 `maximum: 60`，与同一条参数的 description「可选1-72」自相矛盾，官方文档页也写 72 | 以官方文档页为准，上限取 72 | `src/qwx/v1/solarradiation/types.py` `MAX_FORECAST_HOURS` |
| 台风预报返回空列表 | 台风已结束时上游返回空数据，不是错误 | 先 `storm.list` 查台风状态再决定要不要查 | `src/qwx/v7/storm/client.py` `forecast` |
| 台风列表 400 | 上游目前只支持中国沿海流域，即 `basin=NP` | basin 只传 `NP` | `src/qwx/v7/storm/client.py` `list` |
| 日出日落为空 | 高纬度与极昼极夜地区上游给 null | 用 `is None` 判断，别当空串 | `src/qwx/v7/astronomy/types.py` `SunResult.sunrise` |
| 天文日期回 400 | 上游最多接受未来 60 天（含今天） | 超范围由上游拒绝 | `src/qwx/v7/astronomy/client.py` |
| 在公共域名上探测新路径得到 404 | `api.qweather.com` 与 `devapi.qweather.com` 已停服，跑的是旧路由表：监测站路径在旧表里是单数 `/airquality/v1/station/{id}`，规范里的复数 `/airquality/v1/stations/{id}` 在旧表上 404 | 验证路径要在控制台分配的专属 Host 上做，别用公共域名下结论 | `src/qwx/client.py` `Client` |
| 监测站数据缺失或滞后 | 上游明确警告：观测值仅供参考，可能因故障、移除、维护或当地法规导致延迟或缺失 | 当作尽力而为的数据源，缺失是正常状态 | `src/qwx/v1/airquality/client.py` `station` |
| 历史天气 400 | `loc` 只认 LocationID，坐标对与地名都被拒 | 先 `geo.lookup_city` 换 LocationID 再调 | `src/qwx/v7/historical/client.py` `weather` |
| 历史天气日期回 400 | 上游只给最近 10 天、不含今天的历史数据 | 传过去的日期；超范围由上游拒绝 | `src/qwx/v7/historical/client.py` `weather` |
| 历史天气的字段名与其他端点不同 | 上游用 `weatherDaily` / `weatherHourly` 两块，不是 `daily` / `hourly` | 用 `Result.daily` 与 `Result.hourly` | `src/qwx/v7/historical/types.py` `Result` |
| AQI 数值对不上 | 不同标准的量纲不同（QAQI 是 0~1，US EPA 是 0~500） | 不要跨标准比较 | `src/qwx/v1/airquality/types.py` |
| 缓存串到别的账号 | 缓存键不含 API Host | 一个 Cache 实例只服务一个 Host | `src/qwx/client.py` `Client` |
| 城市检索查不到境外城市 | 上游默认只在有限范围内搜 | 用 `Options.range` 传 ISO 3166 国家代码，如 `world` | `src/qwx/geo/client.py` `lookup_city` |
| 请求量统计回 400 | `project` 与 `credential` 互斥，同时传上游会拒绝 | 只传一个；SDK 已在客户端挡下（`qwx.InvalidParameterError`），不打上游 | `src/qwx/console/client.py` `stats` |
| 控制台数据与网页显示的对不上 | 控制台 API 的数据截止至上一个小时或更早，网页上是实时的 | 以响应里的 `as_of` 为准 | `src/qwx/console/types.py` `FinanceResult.as_of` |
| 资源包的 `requests` 拿不到数字 | 上游返回样例给的是字符串（`"1000000"`），官方字段表标的是数字 | SDK 用 `int \| float \| str` 收，两种形态都解析 | `src/qwx/console/types.py` `ResourcePlan.requests` |

通用判据：上游返回与文档冲突时，以 `live/live_test.py` 或线上真实请求的实测为准；确认过的新行为要同时写进 docstring 与 `README.md` 的坑位清单。
