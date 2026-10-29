# 认证

两种认证不能同时使用（同时带上会让上游拒绝请求）。默认选 JWT。

| 方式 | 构造 | 请求头 | 适用 |
| --- | --- | --- | --- |
| `qwx.JWTAuth` | `qwx.JWTAuth(private_key_pem=..., key_id=..., project_id=..., developer_id=...)` | `Authorization: Bearer <JWT>` | 新项目默认 |
| `qwx.APIKeyAuth` | `qwx.APIKeyAuth(key)` | `X-QW-Api-Key: <key>` | 存量项目 |

API KEY 已被官方公告限量：2027-01-01 起限制每日请求量，SDK 5+ 不再支持。新项目用 JWT。

## JWT

需要控制台生成的凭据三项：Key ID（JWT header `kid`）、Project ID（payload `sub`）、Developer ID（payload `iss`）。私钥是 Ed25519 PKCS#8 PEM，公钥上传控制台。

Developer ID 必填，缺失时 `qwx.JWTAuth` 抛 `qwx.InvalidConfigError`。官方口径是 `iss` 为签发者，上游按它校验凭据归属，值在控制台「设置」页查看（Q 开头的 10 位字母数字）。SDK 只校验非空，不校验格式。

```bash
openssl genpkey -algorithm ED25519 -out ed25519-private.pem
openssl pkey -pubout -in ed25519-private.pem > ed25519-public.pem
```

```python
import qwx

auth = qwx.JWTAuth(
    private_key_pem=open("ed25519-private.pem", encoding="utf-8").read(),
    key_id="你的 Key ID",
    project_id="你的 Project ID",
    developer_id="你的 Developer ID",
)
```

`qwx.JWTAuth` 只接受关键字参数。四项凭据缺任一项抛 `qwx.InvalidConfigError`：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `private_key_pem` | 是 | Ed25519 PKCS#8 PEM 文本 |
| `key_id` | 是 | 控制台的 Key ID，进 JWT header 的 `kid` |
| `project_id` | 是 | 控制台的 Project ID，进 payload 的 `sub` |
| `developer_id` | 是 | 控制台的 Developer ID，进 payload 的 `iss` |
| `token_ttl` | 否 | token 有效期，默认 `timedelta(minutes=15)` |
| `clock` | 否 | 时钟注入点，供测试断言 `iat` / `exp` |

签名口径（实现见 `src/qwx/auth.py`）：

- header `alg=EdDSA`、`kid=key_id`；payload `iss=developer_id`、`sub=project_id`、`iat`、`exp=iat+token_ttl`（默认 15 分钟）。
- `iat` 回退 30 秒，容忍时钟偏差。
- token 在过期前 1 分钟自动重签，调用方无感；签名有锁，并发安全。
- PEM 接受含 `\n` 转义的字符串（环境变量常见写法）；非 PKCS#8 或非 Ed25519 抛 `qwx.InvalidConfigError`。

配套：控制台「设置」页会分配专属 API Host（形如 `abcxyz.qweatherapi.com`），它是必填项：`qwx.Client(auth, host)`。公共域名 `devapi.qweather.com`、`api.qweather.com`、`geoapi.qweather.com` 自 2026 年起陆续停服，SDK 不再内置默认值。只给 host 时自动补 `https://`；带 scheme 时按给的来。Host 是身份认证的一部分，凭据与 Host 不匹配上游会拒。

断言 `iat` / `exp` 用 `clock` 注入时钟：

```python
from datetime import datetime, timezone

auth = qwx.JWTAuth(
    private_key_pem=pem,
    key_id="你的 Key ID",
    project_id="你的 Project ID",
    developer_id="你的 Developer ID",
    clock=lambda: datetime(2026, 10, 29, 12, 0, tzinfo=timezone.utc),
)
```

## API KEY

```python
import qwx

auth = qwx.APIKeyAuth("你的 API KEY")
```

空 key 抛 `qwx.InvalidConfigError`。

## 认证失败排查

401/403 归为 `qwx.UnauthorizedError`，见 [errors.md](errors.md)。排查顺序：

1. `kid` 与控制台的 Key ID 一致。
2. `sub` 是 Project ID，不是 Developer ID。
3. `iss` 是 Developer ID，取自控制台「设置」页，不是凭据 ID。
4. 私钥与上传到控制台的公钥是同一对。
5. 凭据、Developer ID 与 API Host 属于同一个开发者账号。
