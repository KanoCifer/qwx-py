# P5 收尾规约

P5 是发布前的最后一程：文档、示例、联网冒烟、CI、发布配置、Redis 适配。
硬约束不变：与 Go 版语义对等；文档只写事实与结论，不写开场恭维与总结段。

## 1. 文档（docs/）

对齐 Go 仓库的八篇，写成中文，读者是 Python 用户：

| 文件 | 内容 |
| --- | --- |
| docs/endpoints.md | 26 个端点的路径、位置形态、默认 TTL、缓存键前缀。**生成物** |
| docs/contract.md | 每个端点的参数上限、返回类型、字段单位；Go 的 contract.md 改写成 Python API 表面 |
| docs/gotchas.md | 上游怪癖分诊表。Go 的 39 条逐条对照 Python 的等价物（方法名、模块路径改成 Python 的） |
| docs/errors.md | 异常层级与处理建议：哪些能重试、哪些要改请求 |
| docs/caching.md | 缓存键规则、TTL 优先级、缓存值格式、接 Redis |
| docs/logging.md | 日志字段名、级别、与标准库 logging 的接法 |
| docs/auth.md | JWT 与 API KEY 两种认证的配置与排障顺序 |
| docs/verification.md | 怎么跑测试、怎么跑联网冒烟、验收命令 |

Go 侧参照：/Users/liudetao/Code/qwx/docs/ 下的同名文件。

## 2. 端点表生成器

`tools/gen_endpoints.py`：

- 输入：`contract/endpoints.json`（从 Go 源码抽取、已与 Go 端点表对账的基线）。
- 输出：`docs/endpoints.md`（生成物，入库）。
- 用法：`python tools/gen_endpoints.py` 写文件；`--check` 只校验漂移。
- `tests/test_endpoints_doc.py` 必须包含：
  - 重新生成后与入库文件逐字相同（无漂移）；
  - **交叉校验**：扫描 Python 源码里的端点常量（`Endpoint... = Endpoint("...")`）与
    默认 TTL（`timedelta(seconds=N)`），与契约基线逐项比对 —— Python 侧改了
    端点常量值或 TTL 而没改契约，测试要红。

## 3. 示例与联网冒烟

- `examples/basic_sync.py`：API KEY 认证，取实时天气，打印关键字段。
- `examples/basic_async.py`：异步版。
- `examples/jwt_auth.py`：JWT 认证。
- `examples/cache_redis.py`：接 Redis 缓存。
- `live/live_test.py`：`pytest -m live` 标记的联网冒烟，需要真实凭据
  （环境变量 `QWX_API_KEY`、`QWX_API_HOST`、`QWX_JWT_*`）；没有凭据就 skip，
  不要让 CI 因缺凭据失败。

示例代码要能直接读懂：中文注释，说明每个参数的来历。

## 4. Redis 适配

- 位置：`src/qwx/redis_cache.py`，实现 `qwx.Cache` 协议（`get` / `set`）。
- redis-py 是可选依赖：在模块里延迟导入（`import redis` 放在函数内），
  没装 redis 时导入 `qwx` 不能报错。
- 缓存值存原始 JSON bytes，与 Go 版共享同一 Redis 时键和值都互通。
- `set` 的 ttl 是相对时长，转成 Redis 的 `ex=`。
- 暴露 `RedisCache(client)` 与 `from_url(url)` 两种构造方式。
- 依赖声明：`pyproject.toml` 里 `[project.optional-dependencies] redis = ["redis>=5.0"]`。
- 测试用假客户端（不连真 Redis）：断言 get/set 的调用参数、ttl 换算、异常透传。

## 5. CI 与发布

- `.github/workflows/ci.yml`：在 push 与 PR 上跑 —— 安装依赖、ruff format --check、
  ruff check、mypy、pytest、契约漂移检查（`extract_go_contract.py --check` 需要 Go
  仓库，CI 里没有 —— 让它 skip 即可，Go 侧漂移在 Go 仓库自己的 CI 里查）。
- `.github/workflows/release.yml`：打 tag 触发构建与发布到 PyPI。
- Python 版本矩阵：3.10、3.11、3.12、3.13（`pyproject.toml` 里
  `requires-python = ">=3.10"`）。
- `pyproject.toml` 补齐发布元数据：project.urls、keywords、classifiers、
  license、readme。

## 6. README

- `README.md`：中文，`README_EN.md`：英文，内容对等。
- 结构：简介 → 安装 → 快速开始（同步/异步）→ 支持的接口表（26 个端点）→
  缓存与 TTL → 错误处理 → 文档索引 → 许可。
- 「支持的接口」表要与 `docs/endpoints.md` 一致（26 行）。

## 7. 验收

```bash
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/python -m pytest tests/ -q
python3 tools/gen_endpoints.py --check
python3 tools/check_field_map.py
```

## 8. 边界

- 各人只改自己负责的文件（见派工说明），不要 git commit。
- 不要改端点族实现（src/qwx/v1/、src/qwx/v7/、src/qwx/geo/、src/qwx/console/），
  除非是明确授权的文件。
