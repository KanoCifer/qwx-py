# 上游行为与限制

参考文档：上游端点的停服状态与替代方案，以及各端点的实测怪癖。

## 停服与替代

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

公共域名 `devapi.qweather.com`、`api.qweather.com`、`geoapi.qweather.com` 已陆续停服，SDK 不内置默认 Host，必须用控制台分配的专属 Host。

## 上游怪癖与限制

一条一句，写清症状与根因。

- 公共域名 2026-01 与 2026-06 陆续停服；`/v7/warning/now` 2026-09-01 停服（用 `qwx.v1.alert`）；`/v7/grid-weather/*`、`/v7/weather/*` 2027-02-01 停服（用 `qwx.v1.weather`）。
- API KEY 认证 2027-01-01 起限制每日请求量，SDK 5+ 不再支持。新项目用 JWT。
- 控制台接口需要帐号所有者在控制台「项目管理 - 凭据 - 控制台权限」里单独开通，否则 403。
- `tide`、`indices`、`minutely` 至今只有 v7 版本，实测所有「新一代」变体路径全 404。
- `days` 在生活指数上只支持 1 与 3。
- 台风 `basin` 只支持 `NP`。
- 太阳辐射预报的 `humidity` 是百分数（0~100），新一代其他端点给的是 0~1 比例。
- 太阳辐射预报这一族没有 `lang` 参数，多传会被拒。
- 监测站路径是复数 `/airquality/v1/stations/{id}`。
- 新一代默认给 UTC 时间（值形如 `2026-10-21T05:00Z`），传 `local_time=True` 才是当地时间。
- 新一代的湿度与云量是 0~1 比例，不是百分数。逐日预报的白天/夜间时段没有 `intensity` 字段。
- 逐日预报的降水强度恒为 0，是因为上游没给 `intensity`，不是真的没雨。判断 `Precipitation.intensity` 不是 `None` 再取值。
- 潮汐的 `date` 要用站点当地日期。北京时间 00:00–08:00 会落到「昨天」，用 UTC 日期必 400。
- POI 检索返回 400 `No Such Location`（不是空列表）：该类型附近确实没有 POI。内陆城市查 TSTA / CSTA 必 400，沿海城市才查得到。
- 生活指数的 `loc` 只认坐标对，裸经度（如 `121.47`）会被拒。
- 分钟级降水只覆盖中国区域，境外坐标上游没有数据。
- 天文的 `date` 最多接受未来 60 天（含今天）。
- 日出日落在高纬度与极昼极夜地区是 null，用 `is None` 判断，别当空串。
- 台风结束后查预报返回空列表，不是错误。先 `storm.list` 查台风状态。
- 预警只认坐标，传 LocationID 或地名上游直接拒绝。
- 历史天气只给最近 10 天、不含今天的数据，`loc` 只认 LocationID。字段是 `weatherDaily` / `weatherHourly`，不是 `daily` / `hourly`。
- 城市检索默认只在有限范围内搜，境外城市要传 `Options.range` 传 ISO 3166 国家代码（如 `world`）。
- AQI 不同标准的量纲不同（QAQI 是 0~1，US EPA 是 0~500），不要跨标准比较。
- 控制台数据截止至上一个小时或更晚，网页上是实时的，以响应里的 `as_of` 为准。
- 控制台 `available_resource_plans[].requests` 上游样例给的是字符串，官方字段表标的是数字，SDK 用 `int | float | str` 收。

上游行为与官方文档冲突时以联网冒烟的实测为准，实测结论写进本文件，并同步进对应方法的 docstring。
