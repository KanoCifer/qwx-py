# 错误与重试

## 类别

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
| `UnauthorizedError` | 上游 401/403 | 查凭据，见 [auth.md](auth.md) |
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

## 读上游细节

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

## 重试判据

客户端自身已经带退避重试：上游 5xx、429 或网络错误时最多再试 3 次（`qwx.client.MAX_RETRY`），单次等待不超过 `qwx.client.MAX_RETRY_DELAY`（30 秒），上游给了 `Retry-After` 且更大就听上游的。4xx 不重试。

| 现象 | 类别 | 动作 |
| --- | --- | --- |
| 429 | `QuotaExceededError` | 客户端已退避重试；仍失败则按配额退避，叠加抖动 |
| 5xx / 连接失败 / 超时 | `UpstreamUnavailableError` | 客户端已指数退避重试；仍失败则在业务层退避重试 |
| 400 / 404 | `UpstreamRejectedError` | 修请求；重试只会重复消耗配额 |
| 401 / 403 | `UnauthorizedError` | 查凭据 |
| JSON 解析失败 | `InvalidResponseError` | 抓 body 判断是网关错误页还是上游异常 |

缓存故障不会变成业务错误：缓存 `get` / `set` 出错时 SDK 直接打上游，逻辑在 `src/qwx/client.py` 的 `do`。
