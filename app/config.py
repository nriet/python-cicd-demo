"""应用配置：全部来自环境变量，便于在容器中按环境覆盖。"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_APP_NAME = "python-cicd-demo"
DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
DEFAULT_ENV = "development"


def _env(name: str, default: str) -> str:
    """读取环境变量，空字符串视为未设置。"""
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
    """运行期设置。"""

    app_name: str
    version: str
    host: str
    port: int
    environment: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            app_name=_env("APP_NAME", DEFAULT_APP_NAME),
            version=_env("APP_VERSION", DEFAULT_VERSION),
            host=_env("APP_HOST", DEFAULT_HOST),
            port=int(_env("APP_PORT", str(DEFAULT_PORT))),
            environment=_env("APP_ENV", DEFAULT_ENV),
        )
