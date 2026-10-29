# qwx

和风天气（QWeather）开发服务的 Python 客户端。

Python 版与 Go 版（[KanoCifer/qwx](https://github.com/KanoCifer/qwx)）语义对等：
端点集合、缓存键字节、端点常量值、错误分类与 TTL 优先级完全一致。

## 当前状态

迁移进行中。**P0 与 P1 阶段已完成**：契约基线与核心层就绪，端点族实现尚未开始。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| P0 | 项目骨架与契约基线 | 完成 |
| P1 | 核心层（client / auth / cache / ttl / errors） | 完成 |
| P2 | 新一代 v1 端点 | 未开始 |
| P3 | GeoAPI 与控制台 | 未开始 |
| P4 | 旧一代 v7 端点 | 未开始 |
| P5 | 文档、示例、发布 | 未开始 |

完整阶段计划见 [迁移方案](docs/MIGRATION_PLAN.md)。

## 安装

```bash
pip install qwx
```

Redis 缓存适配是可选的（适配器本身尚未实现，计划在 P5 收尾阶段补上）：

```bash
pip install "qwx[redis]"
```

## 核心层用法

端点族（P2 起）在各自的子包里，用同一个客户端构造服务客户端。

```python
from datetime import timedelta

import qwx

auth = qwx.APIKeyAuth("你的 API KEY")
client = qwx.Client(auth, "abcxyz.qweatherapi.com")

# JWT 认证
jwt = qwx.JWTAuth(
    private_key_pem=open("ed25519-private.pem").read(),
    key_id="你的 Key ID",
    project_id="你的 Project ID",
    developer_id="你的 Developer ID",
)

# 注入缓存与 TTL 策略
cache = qwx.MemoryCache()
policy = qwx.TTLMap({"weather/v1/current": timedelta(minutes=10)})
```

异步版用法对称，`do` 是协程：

```python
async with qwx.AsyncClient(auth, "abcxyz.qweatherapi.com") as client:
    ...
```

单次缓存时长覆盖用上下文管理器，优先级高于 TTLPolicy 与端点默认：

```python
with client.override_ttl(timedelta(seconds=30)):
    ...
```

错误按类型判断，不解析错误字符串：

```python
from qwx import QuotaExceededError, UnauthorizedError, UpstreamError

try:
    ...
except UnauthorizedError:
    ...
except QuotaExceededError:
    ...
except UpstreamError as exc:
    print(exc.status_code, exc.title, exc.invalid_params)
```

## P0 与 P1 产出

| 产物 | 位置 | 说明 |
| --- | --- | --- |
| 端点契约基线 | [contract/endpoints.json](contract/endpoints.json) | 26 个端点的路径、位置形态、TTL、缓存键模板、查询参数、参数约束 |
| 类型字段契约 | [contract/types.json](contract/types.json) | 85 个类型的字段清单，含 Go 字段名、json tag、可选性与注释 |
| 端点基线说明 | [docs/contract_baseline.md](docs/contract_baseline.md) | 上面那份 JSON 的人读版 |
| Go↔Python 字段映射清单 | [docs/field_map.md](docs/field_map.md) | 每个字段该叫什么 Python 名、要不要显式 alias |
| 契约抽取器 | [tools/extract_go_contract.py](tools/extract_go_contract.py) | 从 Go 源码抽取基线并与 Go 端点表对账 |
| 字段对照工具 | [tools/check_field_map.py](tools/check_field_map.py) | 对照 Go 契约与 Python 模型的别名集合 |
| 缓存键实现 | [src/qwx/_cachekey.py](src/qwx/_cachekey.py) | 键字面量与 Go 版逐字相同，有 golden 测试守着 |
| 坐标格式化 | [src/qwx/_coord.py](src/qwx/_coord.py) | 两位小数，负零归一 |
| 同步与异步客户端 | [src/qwx/client.py](src/qwx/client.py) | httpx 传输、缓存读写、重试退避、错误归类 |
| 认证 | [src/qwx/auth.py](src/qwx/auth.py) | 手写 EdDSA JWT 与 API KEY |
| 错误层级 | [src/qwx/errors.py](src/qwx/errors.py) | 两代错误体都解析，按状态码归类 |
| 缓存与 TTL | [src/qwx/cache.py](src/qwx/cache.py)、[src/qwx/ttl.py](src/qwx/ttl.py) | Cache 协议、内存实现、TTL 策略与单次覆盖 |
| 位置与语言 | [src/qwx/location.py](src/qwx/location.py)、[src/qwx/lang.py](src/qwx/lang.py) | 两代位置形态、31 种语言 |

## 契约基线怎么用

基线由工具从 Go 源码生成，不是手写的。改 Go 源码后重跑：

```bash
python tools/extract_go_contract.py --go-root ../qwx
```

只想知道有没有漂移，不改文件：

```bash
python tools/extract_go_contract.py --go-root ../qwx --check
```

抽取器会把结果与 Go 仓库的 `docs/endpoints.md` 逐项对账 —— 上游路径、默认
TTL、缓存键前缀任一处对不上就报错退出。

Python 侧每落一个模型，跑一次字段对照：

```bash
python tools/check_field_map.py
```

它比对 Go 契约里的 json tag 集合与 Python 模型的别名集合，少一个字段或多一个
字段都会报出来。

## 验收

```bash
uv sync --all-extras
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest -q
```

## 许可

MIT，与 Go 版一致。
