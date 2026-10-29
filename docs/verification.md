# 验证

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

`ruff` 的配置在 `pyproject.toml`：`line-length = 100`，`target-version = "py310"`，选中的规则集是 `E F I UP B SIM RUF N`。`docs/` 目录被排除在格式化之外 —— 里面的代码块是给人看的示例，不参与格式化。

`mypy` 是 strict 模式，只检查 `src/qwx`（`files = ["src/qwx"]`），Python 版本目标 3.10。

## 测试分档

只跑与本次改动直接相关的最小测试集。

| 档 | 改动 | 跑什么 |
| --- | --- | --- |
| 1 | 单个端点族 / 单个文件 | 该模块对应的 `tests/test_*.py` + `ruff format --check .` + `mypy` |
| 2 | 跨模块（`client.py`、`auth.py`、`cache.py`、`location.py`） | 涉及模块 + 直接依赖模块的测试 |
| 3 | 核心重构（缓存键、位置解析、请求执行） | `.venv/bin/python -m pytest tests/ -q` 全量 |

## 联网冒烟

`live/live_test.py` 带 `live` 标记，默认不参与 `pytest tests/`（测试路径只含 `tests/`）。需要真实凭据，缺任一项即 skip，不会让 CI 因缺凭据失败。

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_API_KEY=YOUR_API_KEY \
.venv/bin/python -m pytest live/ -q -m live
```

或者走 JWT（私钥是 PEM 内容，也接受含字面量 `\n` 转义的写法）：

```bash
QWX_API_HOST=your-host.qweatherapi.com \
QWX_JWT_PRIVATE_KEY="$(cat ed25519-private.pem)" \
QWX_KEY_ID=YOUR_KEY_ID \
QWX_PROJECT_ID=YOUR_PROJECT_ID \
QWX_JWT_DEVELOPER_ID=YOUR_DEVELOPER_ID \
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
| `QWX_JWT_DEVELOPER_ID` | Developer ID |

JWT 凭据齐全就走 JWT，缺了就退到 API KEY。两种都没配齐时整个模块 skip。

改了上游行为、端点字段或请求参数后跑它，验证真实响应。

## 契约漂移检查

三件工具，用途不同：

```bash
# 1. 端点表生成物漂移：docs/endpoints.md 与 contract/endpoints.json 对账
.venv/bin/python tools/gen_endpoints.py --check

# 2. 字段对照：Go 契约里的 json tag 集合与 Python 模型的别名集合逐项比对
.venv/bin/python tools/check_field_map.py

# 3. 契约基线抽取：需要 Go 仓库，CI 里没有这个仓库
.venv/bin/python tools/extract_go_contract.py --go-root ../qwx --check
```

第 3 条依赖 Go 仓库（默认路径 `../qwx`），只在本地跑。CI 里不跑它 —— Go 侧的漂移在 Go 仓库自己的 CI 里查。第 1、2 条只读仓库内的 `contract/`，CI 里跑。

抽取器把结果与 Go 仓库的 `docs/endpoints.md` 逐项对账：上游路径、默认 TTL、缓存键前缀任一处对不上就报错退出。

## 完成判定

- `ruff format --check .` 无输出，`ruff check .` 无告警，`mypy` 通过。
- 涉及改动的模块测试通过，错误分支也有覆盖。
- 端点行为变化时，`docs/contract.md`、`docs/endpoints.md`、`docs/caching.md` 与 `README.md` 的对应段落同步更新。
- `python tools/gen_endpoints.py --check` 与 `python tools/check_field_map.py` 通过。
