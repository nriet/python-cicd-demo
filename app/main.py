"""python-cicd-demo 示例服务。

一个依赖极少的 Flask 服务，用来验证 GitHub Actions 流水线：
代码质量检查 -> 测试 -> 多架构镜像构建 -> 推送 Docker Hub。

`/api/v1/info` 会返回当前进程的真实 CPU 架构，可直接用来验证
linux/amd64 与 linux/arm64 两个镜像变体都能正常工作。
"""

from __future__ import annotations

import os
import platform
import time

from flask import Flask, jsonify, request

from app.config import Settings

_STARTED_AT = time.monotonic()


def create_app(settings: Settings | None = None) -> Flask:
    """应用工厂，便于测试与多实例部署。"""
    settings = settings or Settings.from_env()
    app = Flask(settings.app_name)
    app.config["SETTINGS"] = settings

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": settings.app_name,
                "version": settings.version,
                "environment": settings.environment,
                "message": "python-cicd-demo is running",
            }
        )

    @app.get("/healthz")
    def healthz():
        return jsonify(
            {
                "status": "ok",
                "version": settings.version,
                "uptime_seconds": round(time.monotonic() - _STARTED_AT, 3),
            }
        )

    @app.get("/api/v1/info")
    def info():
        return jsonify(
            {
                "python_version": platform.python_version(),
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "pid": os.getpid(),
                "version": settings.version,
            }
        )

    @app.post("/api/v1/echo")
    def echo():
        payload = request.get_json(silent=True)
        if payload is None or not isinstance(payload, dict):
            return jsonify({"error": "body must be a JSON object"}), 400
        return jsonify({"echo": payload, "keys": sorted(payload)})

    return app


app = create_app()


def main() -> None:
    """本地开发入口；容器内由 gunicorn 启动。"""
    settings: Settings = app.config["SETTINGS"]
    app.run(host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
