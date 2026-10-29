# 日志

SDK 用标准库 `logging`，不自带日志实现，也不引入第三方依赖。

## 开关

不注入 logger 时一个字节都不输出。注入：

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

`logger=None` 等同于不注入：不注入时 SDK 挂一个 `NullHandler` 并关掉 `propagate`，输出全部丢弃。

级别由 handler 决定，SDK 不再过滤：handler 放行 DEBUG，就会连缓存命中这类明细一起收到。

## 记什么

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

## 字段

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

## 不记什么

- **认证凭据**：JWT 与 API KEY 都走请求头，不进日志。
- **响应体**：只记状态码与上游给的原因。响应体只在错误对象 `qwx.UpstreamError.body` 里，截断到 2KB。
- **查询参数**：不主动记录。传输层的错误文本里内嵌了完整 URL，记录前会剥掉查询串，只留 path 与错误原因（`qwx.logger.sanitize_error_text`）。

路径与缓存键可能带位置坐标（新一代路径是 `纬度,经度`），日志的可见范围自己把握。

SDK 不对坐标脱敏：坐标是这次调用的主体，排查命中与定位都离不开它。要脱敏就在注入时包一层自己的 handler。

## 自定义脱敏

SDK 不提供脱敏开关：日志器是你注入的 handler，要改写敏感字段就在注入前包一层。

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

## 例子

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

## 性能

不注入 logger 时 SDK 挂在 `NullHandler` 上：不做格式化，也不构造字段，每个请求的额外开销只有一次 `isEnabledFor` 调用。开了日志之后，打上游的请求一条 INFO，缓存命中一条 DEBUG。字段用 dict 构造，不拼字符串。handler 的实现要自己保证并发安全。
