"""JWT 认证示例。

官方推荐 JWT 作为首选认证方式：API KEY 从 2027 年 1 月 1 日起限制每日
请求量。

运行前设置四个环境变量：

    QWX_JWT_PRIVATE_KEY_PATH  Ed25519 私钥的 PEM 文件路径
    QWX_KEY_ID               控制台分配的 Key ID
    QWX_PROJECT_ID           控制台分配的项目 ID
    QWX_DEVELOPER_ID         控制台分配的开发者 ID

    python examples/jwt_auth.py

私钥怎么生成：

    # 生成 PKCS#8 编码的 Ed25519 私钥
    openssl genpkey -algorithm ED25519 -out ed25519-private.pem

    # 看一眼内容（与控制台上传的公钥是一对）
    cat ed25519-private.pem

私钥只留在本地，不要提交到代码仓库。控制台「设置」页要填的是同一对密钥
的**公钥**（`openssl pkey -in ed25519-private.pem -pubout`）。

token 由 SDK 自动签发并在过期前续期，调用方不用管。
"""

from __future__ import annotations

import os
from pathlib import Path

import qwx
from qwx.v1.weather import Options, WeatherService


def main() -> None:
    key_path = os.environ.get("QWX_JWT_PRIVATE_KEY_PATH", "")
    key_id = os.environ.get("QWX_KEY_ID", "")
    project_id = os.environ.get("QWX_PROJECT_ID", "")
    developer_id = os.environ.get("QWX_DEVELOPER_ID", "")
    api_host = os.environ.get("QWX_API_HOST", "")

    if not key_path:
        raise SystemExit("请设置环境变量 QWX_JWT_PRIVATE_KEY_PATH（Ed25519 私钥的 PEM 文件路径）")
    if not key_id or not project_id or not developer_id:
        raise SystemExit("请设置 QWX_KEY_ID / QWX_PROJECT_ID / QWX_DEVELOPER_ID")
    if not api_host:
        raise SystemExit("请设置环境变量 QWX_API_HOST（控制台设置页的专属 API Host）")

    # 读私钥文件。SDK 接受 PKCS#8 的 PEM，也接受含字面量 \n 转义的字符串
    # （环境变量里常见这种写法）。
    private_key_pem = Path(key_path).read_text(encoding="utf-8")

    # 四项都必填，缺任一项抛 InvalidConfigError。developer_id 对应 JWT 的
    # iss，上游按它校验凭据归属，缺失会导致 401。
    auth = qwx.JWTAuth(
        private_key_pem=private_key_pem,
        key_id=key_id,
        project_id=project_id,
        developer_id=developer_id,
    )

    client = qwx.Client(auth, api_host, cache=qwx.MemoryCache())
    weather = WeatherService(client)

    # 北京的坐标。新一代接口只认坐标，纬度在前。
    loc = qwx.Location(lat=39.92, lon=116.41)

    current = weather.current(loc, Options(lang=qwx.Lang.ZH, local_time=True))

    print(f"天气：{current.condition.text}")
    print(f"温度：{current.temperature.value}{current.temperature.unit}")
    print(f"湿度：{current.humidity * 100:.0f}%")

    client.close()


if __name__ == "__main__":
    main()
