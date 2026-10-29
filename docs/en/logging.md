# Logging

Reference: the logging switch, levels and fields, and how redaction is done.

The SDK uses the standard library `logging`. It ships no logging implementation and adds no third-party dependency.

## Enabling Logging

Without an injected logger not a single byte is emitted. Inject one:

```python
import logging

import qwx

client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logging.getLogger("qwx"))
```

`logger=None` is equivalent to not injecting: without injection the SDK attaches a `NullHandler` and disables `propagate`, so all output is discarded.

The level is decided by the handler; the SDK does not filter further. A handler that lets DEBUG through also receives details such as cache hits.

## What Is Logged

| Level | Message | Trigger |
| --- | --- | --- |
| DEBUG | `cache hit` | Cache hit, upstream was not called |
| DEBUG | `cache miss` | Cache miss, the request goes to upstream |
| WARNING | `cache read failed` | Cache read failed, the request degrades to a direct upstream call |
| WARNING | `cache write failed` | Cache write failed, the response was already received, the result is unaffected |
| INFO | `upstream request` | Upstream returned 2xx |
| WARNING | `upstream rejected` | Upstream returned 4xx, the request itself is invalid |
| ERROR | `upstream rejected` | Upstream returned 5xx, upstream failure |
| WARNING | `upstream retry` | 5xx, 429, or a network error triggers a retry |
| ERROR | `decode response failed` | The response is not valid JSON, or its structure does not match the model |
| ERROR | `sign request failed` | Writing the authentication information failed |

A single request produces at most one `upstream request` or `upstream rejected`, plus the occasional retry and cache records. A cache hit has no upstream record, only `cache hit`.

## Fields

Field names are defined centrally as constants in `src/qwx/logger.py`, so you can filter by name in your own handler.

| Field | Meaning |
| --- | --- |
| `endpoint` | Endpoint identifier, e.g. `weather/v1/current`. Absent when the request has no endpoint |
| `method` | HTTP method; empty is treated as GET |
| `path` | Endpoint path, without query parameters |
| `status` | HTTP status code |
| `duration_ms` | Duration in milliseconds |
| `cache_key` | Cache key |
| `attempt` | Retry attempt number, starting at 1 |
| `error` | Error text |
| `upstream_code` | Upstream business status code |
| `upstream_title` | One-line reason given by upstream |

Fields are passed through the `extra` of the standard library `LogRecord`; read them by name in the handler:

```python
class FieldFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Fields are optional: requests without an endpoint have no endpoint field, so use getattr.
        return getattr(record, "endpoint", "") != "weather/v1/current"
```

## What Is Not Logged

- **Authentication credentials**: both JWT and API KEY travel in request headers and never enter the logs.
- **Response body**: only the status code and the reason given by upstream are logged. The response body appears only in the error object `qwx.UpstreamError.body`, truncated to 2KB.
- **Query parameters**: never logged proactively. Transport-level error text embeds the full URL, and the query string is stripped before logging, leaving only the path and the error reason (`qwx.logger.sanitize_error_text`).

Paths and cache keys may carry location coordinates (the new-generation path is `latitude,longitude`); keep the visibility of the logs under your own control.

The SDK does not redact coordinates: the coordinates are the subject of the call, and neither cache-hit debugging nor geolocation works without them. To redact, wrap your own handler at injection time.

## Custom Redaction

The SDK provides no redaction switch. The logger is the handler you inject, so wrap it before injection to rewrite sensitive fields.

```python
import logging


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Rewrite the path / cache_key fields, then pass the record on.
        if hasattr(record, "path"):
            record.path = "<redacted>"
        if hasattr(record, "cache_key"):
            record.cache_key = "<redacted>"
        return True


logger = logging.getLogger("qwx")
logger.addFilter(RedactFilter())
client = qwx.Client(auth, "abcxyz.qweatherapi.com", logger=logger)
```

## Examples

JSON output to stdout:

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

To care only about failures and warnings, raise the level to WARNING:

```python
logger.setLevel(logging.WARNING)
```

## Performance

Without an injected logger the SDK hangs on a `NullHandler`: no formatting, no field construction, and the only per-request overhead is one `isEnabledFor` call. With logging enabled, a request that goes upstream produces one INFO record and a cache hit produces one DEBUG record. Fields are built from a dict, not by concatenating strings. Concurrency safety of the handler implementation is up to you.
