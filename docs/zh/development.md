# 开发与验证

参考文档：本地依赖安装、门禁命令、测试分档与联网冒烟。

## 装依赖

```bash
python -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

要跑 Redis 适配的测试再装 Redis extra：

```bash
.venv/bin/pip install -e ".[dev,redis]"
```

用 uv 的话：

```bash
uv sync --all-extras
uv run pytest -q
```

## 门禁命令

```bash
.venv/bin/ruff format --check .   # 必须无输出
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
```

`ruff` 的配置在 `pyproject.toml`：`line-length = 100`，`target-version = "py310"`，选中的规则集是 `E F I UP B SIM RUF N`。

`mypy` 是 strict 模式，只检查 `src/qwx`（`files = ["src/qwx"]`），Python 版本目标 3.10。

## 测试分档

只跑与本次改动直接相关的最小测试集。

| 档 | 改动 | 跑什么 |
| --- | --- | --- |
| 1 | 单个端点族 / 单个文件 | 该模块对应的 `tests/test_*.py` + `ruff format --check .` + `mypy` |
| 2 | 跨模块（`client.py`、`auth.py`、`cache.py`、`location.py`） | 涉及模块 + 直接依赖模块的测试 |
| 3 | 核心重构（缓存键、位置解析、请求执行） | `.venv/bin/python -m pytest tests/ -q` 全量 |

## 联网冒烟

`live/` 下有四个测试文件和一个共用装置，带 `live` 标记，默认不参与 `pytest tests/`（测试路径只含 `tests/`）。需要真实凭据，缺任一项即 skip，不会让 CI 因缺凭据失败。

| 文件 | 覆盖 |
| --- | --- |
| `live/conftest.py` | 共用装置：读环境变量、造客户端、缺凭据时的 skip 标记 |
| `live/test_live_v1.py` | 新一代：天气、空气质量、预警、太阳辐射 |
| `live/test_live_v7.py` | 旧一代：天文、历史天气、生活指数、分钟级降水、台风、潮汐 |
| `live/test_live_geo.py` | GeoAPI：城市检索、POI 检索、POI 范围、城市榜 |
| `live/test_live_console.py` | 控制台：财务汇总、请求量统计 |

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_API_KEY=YOUR_API_KEY \
.venv/bin/python -m pytest live/ -q -m live
```

或者走 JWT，私钥是 PEM 内容，也接受含字面量 `\n` 转义的写法：

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)" \
QWX_KEY_ID=YOUR_KEY_ID \
QWX_PROJECT_ID=YOUR_PROJECT_ID \
QWX_DEVELOPER_ID=YOUR_DEVELOPER_ID \
.venv/bin/python -m pytest live/ -q -m live
```

环境变量：

| 变量 | 说明 |
| --- | --- |
| `QWX_API_HOST` | 控制台分配的专属 API Host，必填 |
| `QWX_API_KEY` | API KEY，与 JWT 二选一 |
| `QWX_JWT_PRIVATE_KEY` | Ed25519 私钥 PEM 内容 |
| `QWX_KEY_ID` | Key ID |
| `QWX_PROJECT_ID` | Project ID |
| `QWX_DEVELOPER_ID` | Developer ID |

JWT 凭据齐全就走 JWT，缺了就退到 API KEY。两种都没配齐时整个模块 skip。

改了上游行为、端点字段或请求参数后跑它，验证真实响应。

## 完成判定

- `ruff format --check .` 无输出，`ruff check .` 无告警，`mypy` 通过。
- 涉及改动的模块测试通过，错误分支也有覆盖。
- 端点行为变化时，[端点契约](endpoints.md)、[支持的接口](endpoints.md#支持的接口)、[缓存与 TTL](cache.md)对应段落同步更新。
- `.venv/bin/python -m pytest tests/ -q` 全绿。
