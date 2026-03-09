from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class SSHConfig:
    host: str
    port: int
    username: str
    password: str | None
    key_file: str | None
    timeout: int = 15


class ConfigError(ValueError):
    pass


def load_config_from_env() -> SSHConfig:
    host = os.getenv("PERFA_HOST", "").strip()
    username = os.getenv("PERFA_USER", "").strip()
    password = os.getenv("PERFA_PASSWORD")
    key_file = os.getenv("PERFA_KEY_FILE")

    if not host:
        raise ConfigError("缺少环境变量 PERFA_HOST")
    if not username:
        raise ConfigError("缺少环境变量 PERFA_USER")
    if not password and not key_file:
        raise ConfigError("PERFA_PASSWORD 和 PERFA_KEY_FILE 至少配置一个")

    port = int(os.getenv("PERFA_PORT", "22"))
    timeout = int(os.getenv("PERFA_TIMEOUT", "15"))

    return SSHConfig(
        host=host,
        port=port,
        username=username,
        password=password,
        key_file=key_file,
        timeout=timeout,
    )
