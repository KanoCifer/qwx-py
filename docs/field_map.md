# Go↔Python 字段映射清单

由 `tools/extract_go_contract.py` 从 Go 的 struct 定义抽取。Python 侧按本清单落模型：Go 字段名决定 Python 字段名，json tag 决定别名。

别名策略分三档：**自动** 由 `to_camel(Python 字段名)` 得到；**显式** 需要写 `Field(alias=...)`；**无 tag** 表示上游没有这个键。

## 需要显式 alias 的字段

共 7 个。Python 侧漏写 alias 就会解析不到值。

| 包 | 类型 | Go 字段 | json tag | Python 字段 | 原因 |
| --- | --- | --- | --- | --- | --- |
| geo | CityResult | `Locations` | `location` | `locations` | to_camel(locations) = locations |
| geo | POIResult | `POIs` | `poi` | `pois` | to_camel(pois) = pois |
| geo | RangeResult | `POIs` | `poi` | `pois` | to_camel(pois) = pois |
| geo | TopCityResult | `Cities` | `topCityList` | `cities` | to_camel(cities) = cities |
| v7/historical | Result | `Daily` | `weatherDaily` | `daily` | to_camel(daily) = daily |
| v7/historical | Result | `Hourly` | `weatherHourly` | `hourly` | to_camel(hourly) = hourly |
| v7/storm | ListResult | `Storms` | `storm` | `storms` | to_camel(storms) = storms |

## 类型清单

### `console`

#### APICount

> APICount 是一个 API 的逐小时请求量。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `API` | `api` | `string` |  | `api` | `str` | 自动 | API 是 API 名称，如 "Weather"、"Geo"、"AirQuality"。 官方会新增名称，不要依赖枚举的完备性。 |
| `Hours` | `hours` | `[]int` |  | `hours` | `list[int]` | 自动 | Hours 是最近 24 小时的逐小时请求量。 在 [StatsResult.Success] 里是成功请求量，在 [StatsResult.Errors] 里是 错误请求量。末位对应 AsOf 所在的那一小时：AsOf=2025-03-20T09:59Z 时， 末位是 09:00~09:59（UTC）的请求量。 上游可能给少于 24 条，不要假设长度。 |

#### AccruedCharges

> AccruedCharges 是应计费用。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PreviousDay` | `previousDay` | `float64` |  | `previous_day` | `float` | 自动 | PreviousDay 是前一天应计费用总额。 |
| `ThisMonth` | `thisMonth` | `float64` |  | `this_month` | `float` | 自动 | ThisMonth 是本月应计费用总额。 |
| `SinceLastBill` | `sinceLastBill` | `float64` |  | `since_last_bill` | `float` | 自动 | SinceLastBill 是从上次出账以来的应计费用总额。 |

#### FinanceResult

> FinanceResult 是财务汇总的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `qwx.MetaData` |  | `metadata` | `MetaData` | 自动 | Metadata 是元数据。 |
| `AsOf` | `asOf` | `string` |  | `as_of` | `str` | 自动 | AsOf 是数据的截止时间，如 "2024-04-03T17:13Z"。 上游给的是 UTC，原样透传。 |
| `Currency` | `currency` | `string` |  | `currency` | `str` | 自动 | Currency 是货币代码，如 "CNY"、"USD"。 |
| `Balance` | `balance` | `float64` |  | `balance` | `float` | 自动 | Balance 是可用额度。负数表示欠费。 |
| `AccruedCharges` | `accruedCharges` | `AccruedCharges` |  | `accrued_charges` | `AccruedCharges` | 自动 | AccruedCharges 是应计费用。 |
| `PendingBills` | `pendingBills` | `[]PendingBill` |  | `pending_bills` | `list[PendingBill]` | 自动 | PendingBills 是待支付的账单列表。 |
| `AvailableSavingsPlans` | `availableSavingsPlans` | `[]SavingsPlan` |  | `available_savings_plans` | `list[SavingsPlan]` | 自动 | AvailableSavingsPlans 是可用的节省计划列表。 |
| `AvailableResourcePlans` | `availableResourcePlans` | `[]ResourcePlan` |  | `available_resource_plans` | `list[ResourcePlan]` | 自动 | AvailableResourcePlans 是可用的资源包列表。 |

#### PendingBill

> PendingBill 是一张待支付的账单。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Number` | `number` | `string` |  | `number` | `str` | 自动 | Number 是账单号。 |
| `Date` | `date` | `string` |  | `date` | `str` | 自动 | Date 是出账日期，如 "2024-04-01T10:00Z"。 上游给的是 UTC，原样透传。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是账单类型，如 "PayAsYouGo"、"SavingsPlans"。 官方会新增类型，不要依赖枚举的完备性。 |
| `Status` | `status` | `string` |  | `status` | `str` | 自动 | Status 是账单状态，如 "unpaid"、"overdue"。 官方会新增状态，不要依赖枚举的完备性。 |
| `Amount` | `amount` | `float64` |  | `amount` | `float` | 自动 | Amount 是账单总金额。 |
| `AmountDue` | `amountDue` | `float64` |  | `amount_due` | `float` | 自动 | AmountDue 是剩余应付金额。 |
| `DueDate` | `dueDate` | `string` |  | `due_date` | `str` | 自动 | DueDate 是应付日期，如 "2024-04-10T23:59Z"。 上游给的是 UTC，原样透传。 |

#### ResourcePlan

> ResourcePlan 是一个可用的资源包。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BillNumber` | `billNumber` | `string` |  | `bill_number` | `str` | 自动 | BillNumber 是账单号。 |
| `Status` | `status` | `string` |  | `status` | `str` | 自动 | Status 是资源包状态，如 "pending"、"active"。 官方会新增状态，不要依赖枚举的完备性。 |
| `Requests` | `requests` | `json.Number` |  | `requests` | `int | float | str` | 自动 | Requests 是总请求量。 上游的返回样例给的是字符串（"1000000"），官方字段表标的是数字 —— 两种形态都用 [json.Number] 收，调用方按数值用： n, err := plan.Requests.Int64() |
| `Commitments` | `commitments` | `float64` |  | `commitments` | `float` | 自动 | Commitments 是承诺金额。 |
| `Utilized` | `utilized` | `float64` |  | `utilized` | `float` | 自动 | Utilized 是已使用的请求数量。 |
| `EffectiveTime` | `effectiveTime` | `string` |  | `effective_time` | `str` | 自动 | EffectiveTime 是生效时间，如 "2024-04-03T17:00Z"。 上游给的是 UTC，原样透传。 |

#### SavingsPlan

> SavingsPlan 是一个可用的节省计划。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `BillNumber` | `billNumber` | `string` |  | `bill_number` | `str` | 自动 | BillNumber 是账单号。 |
| `Status` | `status` | `string` |  | `status` | `str` | 自动 | Status 是计划状态，如 "pending"、"active"。 官方会新增状态，不要依赖枚举的完备性。 |
| `Term` | `term` | `string` |  | `term` | `str` | 自动 | Term 是承诺期限，如 "1"。 上游给的是字符串，原样透传。 |
| `Commitments` | `commitments` | `float64` |  | `commitments` | `float` | 自动 | Commitments 是承诺金额。 |
| `Utilized` | `utilized` | `float64` |  | `utilized` | `float` | 自动 | Utilized 是已用承诺金额。 |
| `EffectiveTime` | `effectiveTime` | `string` |  | `effective_time` | `str` | 自动 | EffectiveTime 是生效时间，如 "2024-04-30T13:00Z"。 上游给的是 UTC，原样透传。 |

#### StatsOptions

> StatsOptions 是请求量统计的可选参数。 项目与凭据两个过滤条件互斥，都留空时统计帐号下所有项目与凭据 （含已删除的 —— 已删除的项目或凭据无法单独查询，但请求量仍计入汇总）。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Project` | `` | `string` |  | `project` | `str` | 无 tag | Project 是项目 ID，只统计这个项目的请求量。 与 Credential 互斥。 |
| `Credential` | `` | `string` |  | `credential` | `str` | 无 tag | Credential 是凭据 ID，只统计这个凭据的请求量。 与 Project 互斥。 |

#### StatsResult

> StatsResult 是请求量统计的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `qwx.MetaData` |  | `metadata` | `MetaData` | 自动 | Metadata 是元数据。 |
| `AsOf` | `asOf` | `string` |  | `as_of` | `str` | 自动 | AsOf 是数据的截止时间，如 "2025-05-12T02:59Z"。 上游给的是 UTC，原样透传。 |
| `Success` | `success` | `[]APICount` |  | `success` | `list[APICount]` | 自动 | Success 是各 API 的成功请求量。 |
| `Errors` | `errors` | `[]APICount` |  | `errors` | `list[APICount]` | 自动 | Errors 是各 API 的错误请求量。 |

### `core`

#### MetaData

> MetaData 是控制台 API 返回的元数据块。 响应里的 metadata 对象说明本次响应的数据标签与来源署名。展示上游数据时 需要保留 [MetaData.Attributions]。 新一代接口用的是 [github.com/KanoCifer/qwx/v1.Metadata]：它多一个 ZeroResult 字段，用来区分「没查」与「查了是空」。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Tag` | `tag` | `string` |  | `tag` | `str` | 自动 | Tag 是本次响应的数据标签。 |
| `Attributions` | `attributions` | `[]string` |  | `attributions` | `list[str]` | 自动 | Attributions 是数据来源署名。展示数据时需要保留。 |

#### Refer

> Refer 是数据来源与许可信息。 旧一代接口（/v7/*）与 GeoAPI 在响应里带一个 refer 对象，说明数据来源与 授权方式。新一代接口没有 refer —— 同样的意思由 metadata.attributions 表达。 展示这些数据时需要一并展示来源与许可声明。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Sources` | `sources` | `[]string` |  | `sources` | `list[str]` | 自动 | Sources 是原始数据来源，或数据源说明。上游可能给空。 |
| `License` | `license` | `[]string` |  | `license` | `list[str]` | 自动 | License 是数据许可或版权声明。上游可能给空。 |

### `geo`

#### CityResult

> CityResult 是城市检索的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `Locations` | `location` | `[]Place` |  | `locations` | `list[Place]` | 显式 `location` | Locations 是匹配到的地点。 |
| `Refer` | `refer` | `Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 |

#### Options

> Options 是 GeoAPI 的可选参数。 四个检索端点接受的参数子集不同，各端点只上报自己认的参数：行政区划 只有城市检索认，搜索范围城市检索与热门城市认，限定城市只有 POI 检索认。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [qwx.LangZH]。留空用上游默认。 |
| `Number` | `` | `int` |  | `number` | `int` | 无 tag | Number 是返回条数上限。0 用上游默认（10）。 |
| `Adm` | `` | `string` |  | `adm` | `str` | 无 tag | Adm 是上级行政区划的 LocationID，如 "101010100"。 用于排除重名城市或过滤结果。只有城市检索认这个参数。 |
| `Range` | `` | `string` |  | `range` | `str` | 无 tag | Range 是搜索范围，用 ISO 3166 国家代码，如 "cn"、"world"。 留空时上游在所有城市里搜，"world" 才能查到境外城市。 城市检索与热门城市认这个参数。 |
| `City` | `` | `string` |  | `city` | `str` | 无 tag | City 是限定 POI 所在城市，城市名或 LocationID，如 "101010100"。 城市名是精准匹配，匹配不上上游返回空。只有 POI 检索认这个参数。 |

#### POIRangeOptions

> POIRangeOptions 是 POI 范围检索的可选参数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [qwx.LangZH]。留空用上游默认。 |
| `Number` | `` | `int` |  | `number` | `int` | 无 tag | Number 是返回条数上限。0 用上游默认（10）。 |
| `Radius` | `` | `int` |  | `radius` | `int` | 无 tag | Radius 是搜索半径（公里）。0 用上游默认（5）。 |

#### POIResult

> POIResult 是 POI 检索的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码。 |
| `POIs` | `poi` | `[]Place` |  | `pois` | `list[Place]` | 显式 `poi` | POIs 是匹配到的 POI。 |
| `Refer` | `refer` | `Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 |

#### Place

> Place 是一个地点条目。 GeoAPI 的几个检索接口（城市检索、POI 检索、热门城市）返回的条目 结构一致，用同一个类型。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ID` | `id` | `string` |  | `id` | `str` | 自动 | ID 是 LocationID。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是地名（如 "东城"）。 |
| `Lat` | `lat` | `string` |  | `lat` | `str` | 自动 | Lat 是纬度。 |
| `Lon` | `lon` | `string` |  | `lon` | `str` | 自动 | Lon 是经度。 |
| `Adm1` | `adm1` | `string` |  | `adm1` | `str` | 自动 | Adm1 是一级行政区（省/直辖市），如 "北京市"。 |
| `Adm2` | `adm2` | `string` |  | `adm2` | `str` | 自动 | Adm2 是二级行政区（城市），如 "北京"。 |
| `Country` | `country` | `string` |  | `country` | `str` | 自动 | Country 是国家，如 "中国"。 |
| `TZ` | `tz` | `string` |  | `tz` | `str` | 自动 | TZ 是时区，如 "Asia/Shanghai"。 |
| `UTCOffset` | `utcOffset` | `string` |  | `utc_offset` | `str` | 自动 | UTCOffset 是 UTC 偏移，如 "+08:00"。 |
| `IsDst` | `isDst` | `string` |  | `is_dst` | `str` | 自动 | IsDst 是是否夏令时（"0" / "1"）。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是地点类型，如 "city"、"scenic"。 |
| `Rank` | `rank` | `string` |  | `rank` | `str` | 自动 | Rank 是地点排名，数字越小越重要。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是该地点在和风天气官网的链接。 |

#### RangeResult

> RangeResult 是 POI 范围检索的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码。 |
| `POIs` | `poi` | `[]Place` |  | `pois` | `list[Place]` | 显式 `poi` | POIs 是范围内的 POI。 |
| `Refer` | `refer` | `Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 |

#### TopCityResult

> TopCityResult 是热门城市检索的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码。 |
| `Cities` | `topCityList` | `[]Place` |  | `cities` | `list[Place]` | 显式 `topCityList` | Cities 是热门城市列表。 |
| `Refer` | `refer` | `Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 |

### `v1`

#### Metadata

> Metadata 是新一代接口统一的元数据块。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Tag` | `tag` | `string` |  | `tag` | `str` | 自动 | Tag 是本次响应的数据标签。 |
| `Attributions` | `attributions` | `[]string` |  | `attributions` | `list[str]` | 自动 | Attributions 是数据来源署名。展示数据时需要保留。 |
| `ZeroResult` | `zeroResult` | `*bool` | 是 | `zero_result` | `bool` | 自动 | ZeroResult 表示上游确实查了但结果为空。 老于该字段的接口版本没有这个字段，此时为 false —— 无法区分 「没查」与「查了是空」，调用方需要自己结合业务判断。 |

#### Options

> Options 是新一代端点共用的可选参数。 天气与预警两个端点族接受同一组参数，所以类型放在这里 —— 只服务单一 端点族的参数留在该端点族自己的包里。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [github.com/KanoCifer/qwx.LangZH]。留空用上游默认。 上游默认是所在国家或地区的官方语言，没有官方语言时回退到英语。 |
| `LocalTime` | `` | `bool` |  | `local_time` | `bool` | 无 tag | LocalTime 是否返回查询地点的当地时间。 新一代接口默认给 UTC（"2026-10-21T05:00Z"），不传 localTime 时间会整整差 8 小时。除非明确要 UTC，否则应设为 true。 |

#### Value

> Value 是带单位的数值。 新一代接口把数值与单位拆开，不再像 v7 那样把单位拼进字符串。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Value` | `value` | `float64` |  | `value` | `float` | 自动 | Value 是数值。 |
| `Unit` | `unit` | `string` |  | `unit` | `str` | 自动 | Unit 是单位，如 "°C"、"m/s"、"mm"、"hPa"、"m"。 |

### `v1/airquality`

#### Advice

> Advice 是分人群建议。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GeneralPopulation` | `generalPopulation` | `string` |  | `general_population` | `str` | 自动 | GeneralPopulation 是普通人群的建议。 |
| `SensitivePopulation` | `sensitivePopulation` | `string` |  | `sensitive_population` | `str` | 自动 | SensitivePopulation 是敏感人群的建议。 |

#### Color

> Color 是颜色。 只有空气质量接口用这个形状，预警的预警颜色带 code 字段，两者是不同类型。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Red` | `red` | `int` |  | `red` | `int` | 自动 | Red 是红通道。 |
| `Green` | `green` | `int` |  | `green` | `int` | 自动 | Green 是绿通道。 |
| `Blue` | `blue` | `int` |  | `blue` | `int` | 自动 | Blue 是蓝通道。 |
| `Alpha` | `alpha` | `int` |  | `alpha` | `int` | 自动 | Alpha 是透明度。 |

#### Current

> Current 是实时空气质量。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Indexes` | `indexes` | `[]Index` |  | `indexes` | `list[Index]` | 自动 | Indexes 是各标准的 AQI 指数。 |
| `Pollutants` | `pollutants` | `[]Pollutant` |  | `pollutants` | `list[Pollutant]` | 自动 | Pollutants 是各污染物的实测数据。 |
| `Stations` | `stations` | `[]Station` |  | `stations` | `list[Station]` | 自动 | Stations 是附近的监测站。 |

#### DailyForecast

> DailyForecast 是逐日空气质量预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Days` | `days` | `[]Day` |  | `days` | `list[Day]` | 自动 | Days 是逐日预报。 |

#### Day

> Day 是一天的空气质量预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastStartTime` | `forecastStartTime` | `string` |  | `forecast_start_time` | `str` | 自动 | ForecastStartTime 是预报起始时刻。 |
| `ForecastEndTime` | `forecastEndTime` | `string` |  | `forecast_end_time` | `str` | 自动 | ForecastEndTime 是预报结束时刻。 |
| `Indexes` | `indexes` | `[]Index` |  | `indexes` | `list[Index]` | 自动 | Indexes 是各标准的 AQI 指数。 |
| `Pollutants` | `pollutants` | `[]Pollutant` |  | `pollutants` | `list[Pollutant]` | 自动 | Pollutants 是各污染物的预报浓度。 |

#### Health

> Health 是健康影响与建议。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Effect` | `effect` | `string` |  | `effect` | `str` | 自动 | Effect 是健康影响说明。 |
| `Advice` | `advice` | `Advice` |  | `advice` | `Advice` | 自动 | Advice 是分人群的活动建议。 |

#### Hour

> Hour 是一小时的空气质量预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastTime` | `forecastTime` | `string` |  | `forecast_time` | `str` | 自动 | ForecastTime 是预报时刻。 |
| `Indexes` | `indexes` | `[]Index` |  | `indexes` | `list[Index]` | 自动 | Indexes 是各标准的 AQI 指数。 |
| `Pollutants` | `pollutants` | `[]Pollutant` |  | `pollutants` | `list[Pollutant]` | 自动 | Pollutants 是各污染物的预报浓度。 |

#### HourlyForecast

> HourlyForecast 是逐小时空气质量预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Hours` | `hours` | `[]Hour` |  | `hours` | `list[Hour]` | 自动 | Hours 是逐小时预报。 |

#### Index

> Index 是一个 AQI 指数条目。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是标准代码，如 "us-epa"、"qaqi"。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是标准名称，如 "AQI (US)"。 |
| `AQI` | `aqi` | `float64` |  | `aqi` | `float` | 自动 | AQI 是指数值。 不同标准的量纲不同（QAQI 是 0~1，US EPA 是 0~500），不要跨标准比较。 |
| `AQIDisplay` | `aqiDisplay` | `string` |  | `aqi_display` | `str` | 自动 | AQIDisplay 是上游给的可读形式。 |
| `Level` | `level` | `string` |  | `level` | `str` | 自动 | Level 是等级（"1" ~ "6"）。 |
| `Category` | `category` | `string` |  | `category` | `str` | 自动 | Category 是等级描述，如 "Good"、"Excellent"。 |
| `Color` | `color` | `Color` |  | `color` | `Color` | 自动 | Color 是等级对应的颜色。 |
| `PrimaryPollutant` | `primaryPollutant` | `*PollutantBrief` | 是 | `primary_pollutant` | `PollutantBrief` | 自动 | PrimaryPollutant 是首要污染物。可能是 nil（空气很好时无首要污染物）。 |
| `Health` | `health` | `*Health` | 是 | `health` | `Health` | 自动 | Health 是健康建议。 |

#### Options

> Options 是空气质量接口的可选参数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [qwx.LangZH]。留空用上游默认。 |

#### Pollutant

> Pollutant 是一个污染物的实测数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是污染物代码。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是名称。 |
| `FullName` | `fullName` | `string` |  | `full_name` | `str` | 自动 | FullName 是全称。 |
| `Concentration` | `concentration` | `v1.Value` |  | `concentration` | `Value` | 自动 | Concentration 是浓度值。 |
| `SubIndexes` | `subIndexes` | `[]SubIndex` |  | `sub_indexes` | `list[SubIndex]` | 自动 | SubIndexes 是该污染物在各标准下的分指数。 |

#### PollutantBrief

> PollutantBrief 是污染物的简要信息。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是污染物代码，如 "pm2p5"。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是名称，如 "PM 2.5"。 |
| `FullName` | `fullName` | `string` |  | `full_name` | `str` | 自动 | FullName 是全称。 |

#### Station

> Station 是一个监测站。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ID` | `id` | `string` |  | `id` | `str` | 自动 | ID 是站点 ID，如 "P51762"。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是站点名称。 |

#### StationData

> StationData 是单个监测站的污染物数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Pollutants` | `pollutants` | `[]Pollutant` |  | `pollutants` | `list[Pollutant]` | 自动 | Pollutants 是各污染物的实测数据。 |

#### SubIndex

> SubIndex 是一个污染物在某标准下的分指数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是标准代码。 |
| `AQI` | `aqi` | `float64` |  | `aqi` | `float` | 自动 | AQI 是分指数值。 |
| `AQIDisplay` | `aqiDisplay` | `string` |  | `aqi_display` | `str` | 自动 | AQIDisplay 是可读形式。 |

### `v1/alert`

#### Alert

> Alert 是一条预警。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ID` | `id` | `string` |  | `id` | `str` | 自动 | ID 是预警 ID。 |
| `SenderName` | `senderName` | `string` |  | `sender_name` | `str` | 自动 | SenderName 是发布机构，如 "临桂区气象台"。 |
| `IssuedTime` | `issuedTime` | `string` |  | `issued_time` | `str` | 自动 | IssuedTime 是发布时间。 |
| `MessageType` | `messageType` | `MessageType` |  | `message_type` | `MessageType` | 自动 | MessageType 是消息类型。 |
| `EventType` | `eventType` | `EventType` |  | `event_type` | `EventType` | 自动 | EventType 是事件类型。 |
| `Urgency` | `urgency` | `*string` | 是 | `urgency` | `str` | 自动 | Urgency 是紧急程度。可能为 nil。 |
| `Severity` | `severity` | `*string` | 是 | `severity` | `str` | 自动 | Severity 是严重程度。可能为 nil。 |
| `Certainty` | `certainty` | `*string` | 是 | `certainty` | `str` | 自动 | Certainty 是确定性。可能为 nil。 |
| `Icon` | `icon` | `string` |  | `icon` | `str` | 自动 | Icon 是预警图标代码。 |
| `Color` | `color` | `Color` |  | `color` | `Color` | 自动 | Color 是预警颜色。 |
| `EffectiveTime` | `effectiveTime` | `string` |  | `effective_time` | `str` | 自动 | EffectiveTime 是生效时间。 |
| `OnsetTime` | `onsetTime` | `string` |  | `onset_time` | `str` | 自动 | OnsetTime 是开始时间。 |
| `ExpireTime` | `expireTime` | `string` |  | `expire_time` | `str` | 自动 | ExpireTime 是失效时间。 |
| `Headline` | `headline` | `string` |  | `headline` | `str` | 自动 | Headline 是预警标题。 |
| `Description` | `description` | `string` |  | `description` | `str` | 自动 | Description 是预警描述全文。 |
| `Criteria` | `criteria` | `string` |  | `criteria` | `str` | 自动 | Criteria 是预警的触发标准。 |
| `ResponseTypes` | `responseTypes` | `[]string` |  | `response_types` | `list[str]` | 自动 | ResponseTypes 是建议的响应措施。 |
| `Instruction` | `instruction` | `string` |  | `instruction` | `str` | 自动 | Instruction 是防御指南。 |

#### Color

> Color 是预警颜色。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是颜色名，如 "blue"。 |
| `Red` | `red` | `int` |  | `red` | `int` | 自动 | Red 是红通道。 |
| `Green` | `green` | `int` |  | `green` | `int` | 自动 | Green 是绿通道。 |
| `Blue` | `blue` | `int` |  | `blue` | `int` | 自动 | Blue 是蓝通道。 |
| `Alpha` | `alpha` | `int` |  | `alpha` | `int` | 自动 | Alpha 是透明度。 |

#### EventType

> EventType 是预警事件类型。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是事件名称，如 "大风"。 |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是事件代码，如 "1006"。 官方会新增代码，不要依赖枚举的完备性。 |

#### MessageType

> MessageType 是预警消息类型。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是消息类型代码，如 "update"、"alert"。 |
| `Supersedes` | `supersedes` | `[]string` |  | `supersedes` | `list[str]` | 自动 | Supersedes 是本条预警更新/替代的历史预警 ID。 |

#### Result

> Result 是预警查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Alerts` | `alerts` | `[]Alert` |  | `alerts` | `list[Alert]` | 自动 | Alerts 是预警列表。 没有预警时上游返回空列表（metadata.zeroResult 为 true）。 |

### `v1/solarradiation`

#### Forecast

> Forecast 是一个时刻的太阳辐射预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastTime` | `forecastTime` | `string` |  | `forecast_time` | `str` | 自动 | ForecastTime 是预报时刻。 |
| `SolarAngle` | `solarAngle` | `SolarAngle` |  | `solar_angle` | `SolarAngle` | 自动 | SolarAngle 是太阳角度。 |
| `DNI` | `dni` | `v1.Value` |  | `dni` | `Value` | 自动 | DNI 是法向直接辐照。 |
| `DHI` | `dhi` | `v1.Value` |  | `dhi` | `Value` | 自动 | DHI 是散射水平面辐照。 |
| `GHI` | `ghi` | `v1.Value` |  | `ghi` | `Value` | 自动 | GHI 是总水平面辐照。 |
| `Weather` | `weather` | `*Weather` | 是 | `weather` | `Weather` | 自动 | Weather 是基本天气数据。 上游只在请求了 extra=weather 时返回这个对象，其他情况为 nil。 |
| `POA` | `poa` | `*POA` | 是 | `poa` | `POA` | 自动 | POA 是阵列平面辐照度。 上游只在请求了 extra=poa 时返回这个对象，其他情况为 nil。 |

#### Options

> Options 是太阳辐射预报接口的可选参数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `LocalTime` | `` | `bool` |  | `local_time` | `bool` | 无 tag | LocalTime 是否返回查询地点的当地时间。 新一代接口默认给 UTC，不传 localTime 时间会整整差 8 小时。 |
| `Interval` | `` | `int` |  | `interval` | `int` | 无 tag | Interval 是预报数据的时间间隔分钟数，只能是 15、30、60。 0 表示不传，用上游默认（60 分钟）。 |
| `Tilt` | `` | `*int` | 是 | `tilt` | `int` | 无 tag | Tilt 是光伏系统的倾斜角，0~90。 nil 表示不传。用指针区分「没有这个参数」与「倾斜角为 0」—— 平铺的光伏板倾斜角就是 0，0 是合法取值。 |
| `Azimuth` | `` | `*int` | 是 | `azimuth` | `int` | 无 tag | Azimuth 是光伏系统的方位角，0~359，0 表示正北。 nil 表示不传，0 是合法取值。 |
| `Extra` | `` | `string` |  | `extra` | `str` | 无 tag | Extra 是额外信息，如 "weather"、"poa"，多项用逗号分隔。 Extra 含 "poa" 时上游要求 tilt 与 azimuth 都传，缺一个会被拒绝。 取值原样进缓存键，所以 "poa,weather" 与 "weather,poa" 是两个键。 |

#### POA

> POA 是阵列平面辐照度（Plane of Array）。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Global` | `global` | `v1.Value` |  | `global` | `Value` | 自动 | Global 是阵列平面总辐照度。 |
| `Direct` | `direct` | `v1.Value` |  | `direct` | `Value` | 自动 | Direct 是阵列平面直接辐照度。 |
| `Diffuse` | `diffuse` | `v1.Value` |  | `diffuse` | `Value` | 自动 | Diffuse 是阵列平面散射辐照度。 |
| `Reflected` | `reflected` | `v1.Value` |  | `reflected` | `Value` | 自动 | Reflected 是阵列平面反射辐照度。 |

#### Result

> Result 是太阳辐射预报查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Forecasts` | `forecasts` | `[]Forecast` |  | `forecasts` | `list[Forecast]` | 自动 | Forecasts 是太阳辐照预报数据列表。 条数由请求的 hours 与 interval 决定，但上游可能给得更少 —— 不要假设长度。 |

#### SolarAngle

> SolarAngle 是太阳角度。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Azimuth` | `azimuth` | `float64` |  | `azimuth` | `float` | 自动 | Azimuth 是太阳方位角，0~359，正北为 0 度。 |
| `Elevation` | `elevation` | `float64` |  | `elevation` | `float` | 自动 | Elevation 是太阳高度角。 |

#### Weather

> Weather 是太阳辐射预报附带的基本天气数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Temperature` | `temperature` | `v1.Value` |  | `temperature` | `Value` | 自动 | Temperature 是温度。 |
| `WindSpeed` | `windSpeed` | `v1.Value` |  | `wind_speed` | `Value` | 自动 | WindSpeed 是风速。 |
| `Humidity` | `humidity` | `float64` |  | `humidity` | `float` | 自动 | Humidity 是相对湿度，单位是**百分数**（0~100）。 与新一代天气端点不同：那边给的是 0~1 的比例，这边给的是百分数。 |

### `v1/weather`

#### Astro

> Astro 是天文信息。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Sunrise` | `sunrise` | `string` |  | `sunrise` | `str` | 自动 | Sunrise 是日出时刻。 |
| `Sunset` | `sunset` | `string` |  | `sunset` | `str` | 自动 | Sunset 是日落时刻。 |
| `AstronomicalDawn` | `astronomicalDawn` | `string` |  | `astronomical_dawn` | `str` | 自动 | AstronomicalDawn 是天文曙光开始时刻。 |
| `NauticalDawn` | `nauticalDawn` | `string` |  | `nautical_dawn` | `str` | 自动 | NauticalDawn 是航海曙光开始时刻。 |
| `CivilDawn` | `civilDawn` | `string` |  | `civil_dawn` | `str` | 自动 | CivilDawn 是民用曙光开始时刻。 |
| `AstronomicalDusk` | `astronomicalDusk` | `string` |  | `astronomical_dusk` | `str` | 自动 | AstronomicalDusk 是天文暮光结束时刻。 |
| `NauticalDusk` | `nauticalDusk` | `string` |  | `nautical_dusk` | `str` | 自动 | NauticalDusk 是航海暮光结束时刻。 |
| `CivilDusk` | `civilDusk` | `string` |  | `civil_dusk` | `str` | 自动 | CivilDusk 是民用暮光结束时刻。 |
| `SolarNoon` | `solarNoon` | `string` |  | `solar_noon` | `str` | 自动 | SolarNoon 是正午时刻。 |
| `SolarMidnight` | `solarMidnight` | `string` |  | `solar_midnight` | `str` | 自动 | SolarMidnight 是子夜时刻。 |
| `Moonrise` | `moonrise` | `string` |  | `moonrise` | `str` | 自动 | Moonrise 是月出时刻。 |
| `Moonset` | `moonset` | `string` |  | `moonset` | `str` | 自动 | Moonset 是月落时刻。 |
| `MoonTransit` | `moonTransit` | `string` |  | `moon_transit` | `str` | 自动 | MoonTransit 是月过中天时刻。 |
| `MoonUnderfoot` | `moonUnderfoot` | `string` |  | `moon_underfoot` | `str` | 自动 | MoonUnderfoot 是月球位于天顶的时刻。 |
| `MoonPhase` | `moonPhase` | `string` |  | `moon_phase` | `str` | 自动 | MoonPhase 是月相代码，如 "waxing-gibbous"。 |

#### Condition

> Condition 是天气现象。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Text` | `text` | `string` |  | `text` | `str` | 自动 | Text 是天气现象的文字描述，随 lang 变化。 |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是天气现象代码，如 "100"（晴）、"300"（小雨）。 官方会新增代码，不要依赖枚举的完备性。 |

#### CurrentWeather

> CurrentWeather 是实时天气。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Condition` | `condition` | `Condition` |  | `condition` | `Condition` | 自动 | Condition 是天气现象。 |
| `Temperature` | `temperature` | `v1.Value` |  | `temperature` | `Value` | 自动 | Temperature 是气温。 |
| `FeelsLike` | `feelsLike` | `v1.Value` |  | `feels_like` | `Value` | 自动 | FeelsLike 是体感温度。 |
| `Humidity` | `humidity` | `float64` |  | `humidity` | `float` | 自动 | Humidity 是相对湿度，**0~1 的比例**（不是百分数）。 |
| `Wind` | `wind` | `Wind` |  | `wind` | `Wind` | 自动 | Wind 是风。 |
| `WindGust` | `windGust` | `WindGust` |  | `wind_gust` | `WindGust` | 自动 | WindGust 是阵风。 |
| `Precipitation` | `precipitation` | `Precipitation` |  | `precipitation` | `Precipitation` | 自动 | Precipitation 是降水情况。 |
| `Pressure` | `pressure` | `Pressure` |  | `pressure` | `Pressure` | 自动 | Pressure 是气压。 |
| `Visibility` | `visibility` | `Visibility` |  | `visibility` | `Visibility` | 自动 | Visibility 是能见度。 |
| `DewPoint` | `dewPoint` | `DewPoint` |  | `dew_point` | `DewPoint` | 自动 | DewPoint 是露点。 |
| `CloudCover` | `cloudCover` | `float64` |  | `cloud_cover` | `float` | 自动 | CloudCover 是云量，**0~1 的比例**。 |
| `UVIndex` | `uvIndex` | `float64` |  | `uv_index` | `float` | 自动 | UVIndex 是紫外线指数。 |

#### Daily

> Daily 是一天的预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastStartTime` | `forecastStartTime` | `string` |  | `forecast_start_time` | `str` | 自动 | ForecastStartTime 是预报起始时刻。 |
| `ForecastEndTime` | `forecastEndTime` | `string` |  | `forecast_end_time` | `str` | 自动 | ForecastEndTime 是预报结束时刻。 |
| `Astro` | `astro` | `*Astro` | 是 | `astro` | `Astro` | 自动 | Astro 是天文信息（日出日落、月相等）。 高纬度地区可能没有日出日落 —— 该字段可能缺失。 |
| `TemperatureMax` | `temperatureMax` | `v1.Value` |  | `temperature_max` | `Value` | 自动 | TemperatureMax 是最高气温。 |
| `TemperatureMin` | `temperatureMin` | `v1.Value` |  | `temperature_min` | `Value` | 自动 | TemperatureMin 是最低气温。 |
| `TemperatureAvg` | `temperatureAvg` | `v1.Value` |  | `temperature_avg` | `Value` | 自动 | TemperatureAvg 是平均气温。 |
| `UVIndexMax` | `uvIndexMax` | `float64` |  | `uv_index_max` | `float` | 自动 | UVIndexMax 是最大紫外线指数。 |
| `Daytime` | `daytime` | `DayNight` |  | `daytime` | `DayNight` | 自动 | Daytime 是白天时段（v7 时代是一天一条，新一代拆成白天/夜间两段）。 |
| `Nighttime` | `nighttime` | `DayNight` |  | `nighttime` | `DayNight` | 自动 | Nighttime 是夜间时段。 |

#### DailyForecast

> DailyForecast 是逐日预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Days` | `days` | `[]Daily` |  | `days` | `list[Daily]` | 自动 | Days 是逐日预报列表。 |

#### DayNight

> DayNight 是白天或夜间时段的天气。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastStartTime` | `forecastStartTime` | `string` |  | `forecast_start_time` | `str` | 自动 | ForecastStartTime 是时段起始时刻。 |
| `ForecastEndTime` | `forecastEndTime` | `string` |  | `forecast_end_time` | `str` | 自动 | ForecastEndTime 是时段结束时刻。 |
| `Condition` | `condition` | `Condition` |  | `condition` | `Condition` | 自动 | Condition 是天气现象。 |
| `TemperatureMax` | `temperatureMax` | `v1.Value` |  | `temperature_max` | `Value` | 自动 | TemperatureMax 是最高气温。 |
| `TemperatureMin` | `temperatureMin` | `v1.Value` |  | `temperature_min` | `Value` | 自动 | TemperatureMin 是最低气温。 |
| `Wind` | `wind` | `Wind` |  | `wind` | `Wind` | 自动 | Wind 是风。 |
| `WindGustMax` | `windGustMax` | `WindGust` |  | `wind_gust_max` | `WindGust` | 自动 | WindGustMax 是时段内的最大阵风。 上游 daily 端点的白天/夜间时段用 windGustMax，与 current、hourly 端点的 windGust 不是同一个键。 |
| `Precipitation` | `precipitation` | `Precipitation` |  | `precipitation` | `Precipitation` | 自动 | Precipitation 是降水情况。 |
| `Humidity` | `humidity` | `float64` |  | `humidity` | `float` | 自动 | Humidity 是相对湿度，0~1 的比例。 |
| `CloudCover` | `cloudCover` | `float64` |  | `cloud_cover` | `float` | 自动 | CloudCover 是云量，0~1 的比例。 |

#### DewPoint

> DewPoint 是露点温度。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Value` | `value` | `float64` |  | `value` | `float` | 自动 | Value 是露点温度。 |
| `Unit` | `unit` | `string` |  | `unit` | `str` | 自动 | Unit 是单位（°C）。 |

#### Hourly

> Hourly 是一个小时的预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ForecastTime` | `forecastTime` | `string` |  | `forecast_time` | `str` | 自动 | ForecastTime 是预报时刻。 |
| `Condition` | `condition` | `Condition` |  | `condition` | `Condition` | 自动 | Condition 是天气现象。 |
| `Temperature` | `temperature` | `v1.Value` |  | `temperature` | `Value` | 自动 | Temperature 是气温。 |
| `FeelsLike` | `feelsLike` | `v1.Value` |  | `feels_like` | `Value` | 自动 | FeelsLike 是体感温度。 |
| `Humidity` | `humidity` | `float64` |  | `humidity` | `float` | 自动 | Humidity 是相对湿度，0~1 的比例。 |
| `Wind` | `wind` | `Wind` |  | `wind` | `Wind` | 自动 | Wind 是风。 |
| `WindGust` | `windGust` | `WindGust` |  | `wind_gust` | `WindGust` | 自动 | WindGust 是阵风。 |
| `Precipitation` | `precipitation` | `Precipitation` |  | `precipitation` | `Precipitation` | 自动 | Precipitation 是降水情况，含概率。 |
| `Pressure` | `pressure` | `Pressure` |  | `pressure` | `Pressure` | 自动 | Pressure 是气压。 |
| `Visibility` | `visibility` | `Visibility` |  | `visibility` | `Visibility` | 自动 | Visibility 是能见度。 |
| `DewPoint` | `dewPoint` | `DewPoint` |  | `dew_point` | `DewPoint` | 自动 | DewPoint 是露点。 |
| `CloudCover` | `cloudCover` | `float64` |  | `cloud_cover` | `float` | 自动 | CloudCover 是云量，0~1 的比例。 |
| `UVIndex` | `uvIndex` | `float64` |  | `uv_index` | `float` | 自动 | UVIndex 是紫外线指数。 |

#### HourlyForecast

> HourlyForecast 是逐小时预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Metadata` | `metadata` | `v1.Metadata` |  | `metadata` | `Metadata` | 自动 | Metadata 是元数据。 |
| `Hours` | `hours` | `[]Hourly` |  | `hours` | `list[Hourly]` | 自动 | Hours 是逐小时预报列表。 条数由请求的 hours 决定，但上游可能给得更少 —— 不要假设长度。 |

#### Precipitation

> Precipitation 是降水情况。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Amount` | `amount` | `v1.Value` |  | `amount` | `Value` | 自动 | Amount 是降水量。 |
| `Intensity` | `intensity` | `*v1.Value` | 是 | `intensity` | `Value` | 自动 | Intensity 是降水强度。 实况与逐时预报有这个字段，逐日预报的白天/夜间时段没有 —— 用指针区分「没有」与「强度为 0」。 |
| `Probability` | `probability` | `*float64` | 是 | `probability` | `float` | 自动 | Probability 是降水概率（0~1）。 实时天气接口没有这个字段，逐小时预报与逐日预报的白天/夜间时段 才有。用指针区分「没有」与「概率为 0」。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是降水类型代码，如 "rain"、"snow"、"none"。 上游会新增类型，不要依赖枚举的完备性。 |

#### Pressure

> Pressure 是气压。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Value` | `value` | `float64` |  | `value` | `float` | 自动 | Value 是气压值。 |
| `Unit` | `unit` | `string` |  | `unit` | `str` | 自动 | Unit 是单位（hPa）。 |

#### Visibility

> Visibility 是能见度。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Value` | `value` | `float64` |  | `value` | `float` | 自动 | Value 是能见度值。 |
| `Unit` | `unit` | `string` |  | `unit` | `str` | 自动 | Unit 是单位（m）。 |

#### Wind

> Wind 是风速与风向。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Direction` | `direction` | `WindDirection` |  | `direction` | `WindDirection` | 自动 | Direction 是风向。 |
| `Speed` | `speed` | `v1.Value` |  | `speed` | `Value` | 自动 | Speed 是风速。 |
| `Scale` | `scale` | `float64` |  | `scale` | `float` | 自动 | Scale 是风力等级（蒲福风级）。 |

#### WindDirection

> WindDirection 是风向。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Degree` | `degree` | `float64` |  | `degree` | `float` | 自动 | Degree 是风向角度（0~360，0 为北）。 |
| `Compass` | `compass` | `string` |  | `compass` | `str` | 自动 | Compass 是 16 方位英文代码（如 "sw"、"wnw"），不是中文。 |

#### WindGust

> WindGust 是阵风。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Value` | `value` | `float64` |  | `value` | `float` | 自动 | Value 是阵风风速。 |
| `Unit` | `unit` | `string` |  | `unit` | `str` | 自动 | Unit 是单位。 |

### `v7/astronomy`

#### AngleResult

> AngleResult 是太阳高度角数据。 上游这个端点的响应里没有 updateTime 与 fxLink，本类型也没有这两个字段。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `SolarElevationAngle` | `solarElevationAngle` | `string` |  | `solar_elevation_angle` | `str` | 自动 | SolarElevationAngle 是太阳高度角（度）。 上游给的是字符串，这里保持字符串 —— 转成 float64 会丢掉它的表达精度。 |
| `SolarAzimuthAngle` | `solarAzimuthAngle` | `string` |  | `solar_azimuth_angle` | `str` | 自动 | SolarAzimuthAngle 是太阳方位角（度），0 度为正北。 上游给的是字符串，这里保持字符串。 |
| `SolarHour` | `solarHour` | `string` |  | `solar_hour` | `str` | 自动 | SolarHour 是太阳时，"HHmm" 格式。 |
| `HourAngle` | `hourAngle` | `string` |  | `hour_angle` | `str` | 自动 | HourAngle 是时角。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### MoonPhase

> MoonPhase 是一小时的月相。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FXTime` | `fxTime` | `string` |  | `fx_time` | `str` | 自动 | FXTime 是月相预报时间。 |
| `Value` | `value` | `string` |  | `value` | `str` | 自动 | Value 是月相数值。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是月相名称，如 "新月"、"满月"。 名称随语言变，上游的取值也不止一种，这里只透传不写完备列表。 |
| `Illumination` | `illumination` | `string` |  | `illumination` | `str` | 自动 | Illumination 是月亮照明度，百分比数值。 上游给的是字符串，这里保持字符串 —— 转成 float64 会丢掉它的表达精度。 |
| `Icon` | `icon` | `string` |  | `icon` | `str` | 自动 | Icon 是月相图标代码。 |

#### MoonResult

> MoonResult 是月升月落和月相数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Moonrise` | `moonrise` | `*string` | 是 | `moonrise` | `str` | 自动 | Moonrise 是当天月升时间。 上游说可能为空，用指针区分"没有月升"与"空串"。 |
| `Moonset` | `moonset` | `*string` | 是 | `moonset` | `str` | 自动 | Moonset 是当天月落时间。 同 [MoonResult.Moonrise]：可能为空。 |
| `MoonPhase` | `moonPhase` | `[]MoonPhase` |  | `moon_phase` | `list[MoonPhase]` | 自动 | MoonPhase 是逐小时月相。 列表长度不固定，不假设。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### Options

> Options 是月相端点的可选参数。 只有月相端点认语言参数 —— 日出日落与太阳高度角不带语言。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [qwx.LangZH]。留空用上游默认。 |

#### SunResult

> SunResult 是日出日落数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Sunrise` | `sunrise` | `*string` | 是 | `sunrise` | `str` | 自动 | Sunrise 是日出时间。 上游在高纬度地区可能给 null，用指针区分"没有日出"与"空串"。 |
| `Sunset` | `sunset` | `*string` | 是 | `sunset` | `str` | 自动 | Sunset 是日落时间。 同 [SunResult.Sunrise]：极昼极夜地区可能为 null。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

### `v7/historical`

#### Daily

> Daily 是一天的历史天气汇总。 上游把数值都包成字符串，这里保持字符串 —— 小数位数是上游的表达精度， 转成 float64 会丢掉它。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Date` | `date` | `string` |  | `date` | `str` | 自动 | Date 是日期，"YYYY-MM-DD"。 |
| `Sunrise` | `sunrise` | `*string` | 是 | `sunrise` | `str` | 自动 | Sunrise 是日出时间。 高纬度地区上游可能不给，用指针区分"没有日出"与"空串"。 |
| `Sunset` | `sunset` | `*string` | 是 | `sunset` | `str` | 自动 | Sunset 是日落时间。 同 [Daily.Sunrise]：极昼极夜地区可能不给。 |
| `Moonrise` | `moonrise` | `*string` | 是 | `moonrise` | `str` | 自动 | Moonrise 是月升时间。上游可能不给。 |
| `Moonset` | `moonset` | `*string` | 是 | `moonset` | `str` | 自动 | Moonset 是月落时间。上游可能不给。 |
| `MoonPhase` | `moonPhase` | `string` |  | `moon_phase` | `str` | 自动 | MoonPhase 是月相名称，如 "峨眉月"。 名称随语言变，上游的取值也不止一种，这里只透传不写完备列表。 |
| `TempMax` | `tempMax` | `string` |  | `temp_max` | `str` | 自动 | TempMax 是当天最高温度。 |
| `TempMin` | `tempMin` | `string` |  | `temp_min` | `str` | 自动 | TempMin 是当天最低温度。 |
| `Humidity` | `humidity` | `string` |  | `humidity` | `str` | 自动 | Humidity 是当天相对湿度，百分比数值。 |
| `Precip` | `precip` | `string` |  | `precip` | `str` | 自动 | Precip 是当天总降水量，默认单位毫米。 空串表示"无此数据"，与 "0.0"（真的没下雨）不是一回事。 |
| `Pressure` | `pressure` | `string` |  | `pressure` | `str` | 自动 | Pressure 是站点气压，默认单位百帕。 |

#### Hourly

> Hourly 是一小时的历史天气。 上游把数值都包成字符串，这里保持字符串 —— 小数位数是上游的表达精度， 转成 float64 会丢掉它。 上游个别小时可能不带风向与风速字段，缺失时是空串。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Time` | `time` | `string` |  | `time` | `str` | 自动 | Time 是时刻，"YYYY-MM-DD HH:mm"。 |
| `Temp` | `temp` | `string` |  | `temp` | `str` | 自动 | Temp 是该小时的温度，默认单位摄氏度。 |
| `Icon` | `icon` | `string` |  | `icon` | `str` | 自动 | Icon 是天气状况的图标代码。 |
| `Text` | `text` | `string` |  | `text` | `str` | 自动 | Text 是天气状况的文字描述，如 "晴"。 描述随语言变，上游的取值也不止一种，这里只透传不写完备列表。 |
| `Wind360` | `wind360` | `string` |  | `wind360` | `str` | 自动 | Wind360 是风向 360 度角度。 |
| `WindDir` | `windDir` | `string` |  | `wind_dir` | `str` | 自动 | WindDir 是风向，如 "西南风"。 |
| `WindScale` | `windScale` | `string` |  | `wind_scale` | `str` | 自动 | WindScale 是风力等级。 |
| `WindSpeed` | `windSpeed` | `string` |  | `wind_speed` | `str` | 自动 | WindSpeed 是风速，默认单位公里/小时。 |
| `Humidity` | `humidity` | `string` |  | `humidity` | `str` | 自动 | Humidity 是该小时的相对湿度，百分比数值。 |
| `Precip` | `precip` | `string` |  | `precip` | `str` | 自动 | Precip 是该小时的降水量，默认单位毫米。 空串表示"无此数据"，与 "0.0"（真的没下雨）不是一回事。 |
| `Pressure` | `pressure` | `string` |  | `pressure` | `str` | 自动 | Pressure 是站点气压，默认单位百帕。 |

#### Options

> Options 是历史天气端点的可选参数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lang` | `` | `qwx.Lang` |  | `lang` | `Lang` | 无 tag | Lang 是语言，如 [qwx.LangZH]。留空用上游默认。 |

#### Result

> Result 是历史天气查询的结果。 上游这个端点的响应里没有 updateTime 与 fxLink 之外的元信息块，本类型 也没有对应的字段。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Daily` | `weatherDaily` | `*Daily` | 是 | `daily` | `Daily` | 显式 `weatherDaily` | Daily 是当天的天气汇总。 上游用对象给这一天的汇总数据，不是数组。上游没给这一块时是 nil。 |
| `Hourly` | `weatherHourly` | `[]Hourly` |  | `hourly` | `list[Hourly]` | 显式 `weatherHourly` | Hourly 是当天的逐小时历史天气。 列表长度不假设：上游可能给少于 24 条。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

### `v7/indices`

#### DailyIndex

> DailyIndex 是一天的生活指数。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Date` | `date` | `string` |  | `date` | `str` | 自动 | Date 是日期，"YYYY-MM-DD"。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是指数类型代码。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是指数名称，如 "运动指数"。 |
| `Level` | `level` | `string` |  | `level` | `str` | 自动 | Level 是等级。上游给的是字符串，这里保持字符串。 |
| `Category` | `category` | `string` |  | `category` | `str` | 自动 | Category 是等级描述，如 "较不宜"。 |
| `Text` | `text` | `string` |  | `text` | `str` | 自动 | Text 是详细说明。 |

#### Result

> Result 是生活指数查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Daily` | `daily` | `[]DailyIndex` |  | `daily` | `list[DailyIndex]` | 自动 | Daily 是逐日指数。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

### `v7/minutely`

#### Minutely

> Minutely 是一条分钟级降水预报。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FXTime` | `fxTime` | `string` |  | `fx_time` | `str` | 自动 | FXTime 是预报时刻。 |
| `Precip` | `precip` | `string` |  | `precip` | `str` | 自动 | Precip 是降水量。 上游给的是固定两位小数的字符串。这里保持字符串：空串表示"无此数据"， 与 "0.00"（真的没下雨）不是一回事，转成数值会把两者压成同一个 0。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是降水类型："rain" / "snow"。 |

#### Result

> Result 是分钟级降水预报的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Summary` | `summary` | `string` |  | `summary` | `str` | 自动 | Summary 是一句话摘要，如 "95分钟后雨就停了"。 |
| `Minutely` | `minutely` | `[]Minutely` |  | `minutely` | `list[Minutely]` | 自动 | Minutely 是逐 5 分钟的降水预报。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

### `v7/ocean`

#### Result

> Result 是潮汐数据。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `TideTable` | `tideTable` | `[]Tide` |  | `tide_table` | `list[Tide]` | 自动 | TideTable 是潮汐表（高低潮）。 |
| `TideHourly` | `tideHourly` | `[]TideHourly` |  | `tide_hourly` | `list[TideHourly]` | 自动 | TideHourly 是逐小时潮位。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### Tide

> Tide 是一个潮汐时刻（高低潮）。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FXTime` | `fxTime` | `string` |  | `fx_time` | `str` | 自动 | FXTime 是潮汐时刻。 |
| `Height` | `height` | `string` |  | `height` | `str` | 自动 | Height 是潮位高度（米）。 上游给的是字符串，这里保持字符串 —— 小数位数是上游的表达精度， 转成 float64 会丢掉它。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是潮汐类型："H"（高潮）/ "L"（低潮）。 |

#### TideHourly

> TideHourly 是一个小时的潮位。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FXTime` | `fxTime` | `string` |  | `fx_time` | `str` | 自动 | FXTime 是时刻。 |
| `Height` | `height` | `string` |  | `height` | `str` | 自动 | Height 是潮位高度（米）。 |

### `v7/storm`

#### Forecast

> Forecast 是一个预报时刻的台风状态。 上游把台风属性平铺在预报元素里，这里按上游 JSON 一一对应，不做嵌套。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FXTime` | `fxTime` | `string` |  | `fx_time` | `str` | 自动 | FXTime 是预报时刻。 |
| `` | `` | `StormState` |  | `` | `需人工确认` | 未解析 | StormState 是该时刻的台风状态。 |

#### ForecastResult

> ForecastResult 是台风预报查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Forecast` | `forecast` | `[]Forecast` |  | `forecast` | `list[Forecast]` | 自动 | Forecast 是台风预报数据列表。 台风已结束时上游返回空列表。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### ListResult

> ListResult 是台风列表查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `Storms` | `storm` | `[]StormSummary` |  | `storms` | `list[StormSummary]` | 显式 `storm` | Storms 是台风列表。 上游的 "storm" 是数组，不是对象。长度不固定：一个年份里可能有几十个 台风，也可能一个都没有。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### StormState

> StormState 是一个时刻的台风状态。 上游把台风属性平铺在预报元素与轨迹元素里，这两组字段完全一样，所以 收成一个类型内嵌进 [Forecast] 与 [TrackPoint] —— JSON 形状不变，字段 访问也不变。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Lat` | `lat` | `string` |  | `lat` | `str` | 自动 | Lat 是台风所处纬度。 上游把数值包成字符串，这里保持字符串 —— 小数位数是上游的表达精度， 转成 float64 会丢掉它。 |
| `Lon` | `lon` | `string` |  | `lon` | `str` | 自动 | Lon 是台风所处经度。上游给的是字符串，这里保持字符串。 |
| `Type` | `type` | `string` |  | `type` | `str` | 自动 | Type 是台风类型，如 "TS"、"TD"、"STS"。 |
| `Pressure` | `pressure` | `string` |  | `pressure` | `str` | 自动 | Pressure 是台风中心气压。上游给的是字符串，这里保持字符串。 |
| `WindSpeed` | `windSpeed` | `string` |  | `wind_speed` | `str` | 自动 | WindSpeed 是台风附近最大风速。上游给的是字符串，这里保持字符串。 |
| `MoveSpeed` | `moveSpeed` | `string` |  | `move_speed` | `str` | 自动 | MoveSpeed 是台风移动速度。上游给的是字符串，这里保持字符串。 |
| `MoveDir` | `moveDir` | `string` |  | `move_dir` | `str` | 自动 | MoveDir 是台风移动方位，如 "NE"。 |
| `Move360` | `move360` | `string` |  | `move360` | `str` | 自动 | Move360 是台风移动方位 360 度方向。上游可能是空串。 |
| `WindRadius30` | `windRadius30` | `*WindRadius` | 是 | `wind_radius30` | `WindRadius` | 自动 | WindRadius30 是 7 级风圈半径。台风等级不够时上游不给，这时是 nil。 |
| `WindRadius50` | `windRadius50` | `*WindRadius` | 是 | `wind_radius50` | `WindRadius` | 自动 | WindRadius50 是 10 级风圈半径。台风等级不够时上游不给，这时是 nil。 |
| `WindRadius64` | `windRadius64` | `*WindRadius` | 是 | `wind_radius64` | `WindRadius` | 自动 | WindRadius64 是 12 级风圈半径。台风等级不够时上游不给，这时是 nil。 |

#### StormSummary

> StormSummary 是一个台风的概要。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `ID` | `id` | `string` |  | `id` | `str` | 自动 | ID 是台风 ID，如 "NP2018"。 |
| `Name` | `name` | `string` |  | `name` | `str` | 自动 | Name 是台风名称，如 "莫拉菲"。 |
| `Basin` | `basin` | `string` |  | `basin` | `str` | 自动 | Basin 是台风所处流域，如 "NP"。 |
| `Year` | `year` | `string` |  | `year` | `str` | 自动 | Year 是台风所处年份。上游给的是字符串，这里保持字符串。 |
| `IsActive` | `isActive` | `string` |  | `is_active` | `str` | 自动 | IsActive 是活跃标记："1" 活跃台风，"0" 停编。 上游给的是字符串，这里保持字符串，不转成 bool。 |

#### TrackPoint

> TrackPoint 是一个轨迹点的台风状态。 上游把台风属性平铺在轨迹元素里，这里按上游 JSON 一一对应，不做嵌套。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `PubTime` | `pubTime` | `string` |  | `pub_time` | `str` | 自动 | PubTime 是实况发布时间。只有 "now" 元素有这个字段。 |
| `Time` | `time` | `string` |  | `time` | `str` | 自动 | Time 是轨迹点时刻。只有 "track" 数组元素有这个字段。 |
| `` | `` | `StormState` |  | `` | `需人工确认` | 未解析 | StormState 是该时刻的台风状态。 |

#### TrackResult

> TrackResult 是台风实况和路径查询的结果。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Code` | `code` | `string` |  | `code` | `str` | 自动 | Code 是上游状态码，"200" 为成功。 |
| `UpdateTime` | `updateTime` | `string` |  | `update_time` | `str` | 自动 | UpdateTime 是数据更新时间。 |
| `FXLink` | `fxLink` | `string` |  | `fx_link` | `str` | 自动 | FXLink 是官网链接。 |
| `IsActive` | `isActive` | `string` |  | `is_active` | `str` | 自动 | IsActive 是活跃标记："1" 活跃台风，"0" 停编。 上游给的是字符串，这里保持字符串，不转成 bool。 |
| `Now` | `now` | `*TrackPoint` | 是 | `now` | `TrackPoint` | 自动 | Now 是当前台风实况。 台风已结束时上游可能给 null，这时是 nil。 |
| `Track` | `track` | `[]TrackPoint` |  | `track` | `list[TrackPoint]` | 自动 | Track 是台风轨迹点列表。长度不固定。 |
| `Refer` | `refer` | `qwx.Refer` |  | `refer` | `Refer` | 自动 | Refer 是数据来源与许可信息。 上游在结果里带 refer 对象，展示这些数据时需要一并展示。 |

#### WindRadius

> WindRadius 是一个风圈的四个方向半径。

| Go 字段 | json tag | Go 类型 | 可选 | Python 字段 | Python 类型 | 别名 | 说明 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `NERadius` | `neRadius` | `string` |  | `ne_radius` | `str` | 自动 | NERadius 是东北半径。上游可能是空串。 |
| `SERadius` | `seRadius` | `string` |  | `se_radius` | `str` | 自动 | SERadius 是东南半径。上游可能是空串。 |
| `SWRadius` | `swRadius` | `string` |  | `sw_radius` | `str` | 自动 | SWRadius 是西南半径。上游可能是空串。 |
| `NWRadius` | `nwRadius` | `string` |  | `nw_radius` | `str` | 自动 | NWRadius 是西北半径。上游可能是空串。 |
