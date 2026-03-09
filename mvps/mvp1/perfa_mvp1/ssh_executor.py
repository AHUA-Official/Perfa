from __future__ import annotations

import paramiko

from .config import SSHConfig


class SSHExecutor:
    def __init__(self, config: SSHConfig) -> None:
        self.config = config
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def __enter__(self) -> "SSHExecutor":
        connect_kwargs = {
            "hostname": self.config.host,
            "port": self.config.port,
            "username": self.config.username,
            "timeout": self.config.timeout,
            "banner_timeout": self.config.timeout,
            "auth_timeout": self.config.timeout,
        }
        if self.config.key_file:
            connect_kwargs["key_filename"] = self.config.key_file
        else:
            connect_kwargs["password"] = self.config.password

        self.client.connect(**connect_kwargs)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.close()

    def run(self, command: str, timeout: int = 120) -> tuple[int, str, str]:
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, stdout.read().decode("utf-8", errors="ignore"), stderr.read().decode("utf-8", errors="ignore")
