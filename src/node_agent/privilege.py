"""
Node Agent 权限配置
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class PrivilegeConfig:
    """运行时提权配置"""
    mode: str = "root"  # root / sudo_nopasswd / sudo_password / none
    sudo_password: Optional[str] = None

    @classmethod
    def from_env(cls) -> "PrivilegeConfig":
        return cls(
            mode=os.getenv("NODE_AGENT_PRIVILEGE_MODE", "root"),
            sudo_password=os.getenv("NODE_AGENT_SUDO_PASSWORD") or None,
        )


_config = PrivilegeConfig.from_env()


def get_privilege_config() -> PrivilegeConfig:
    return _config


def update_privilege_config(
    mode: Optional[str] = None,
    sudo_password: Optional[str] = None,
) -> PrivilegeConfig:
    global _config
    if mode is not None:
        _config.mode = mode
    if sudo_password is not None:
        _config.sudo_password = sudo_password or None
    return _config


def build_privileged_command(cmd: List[str], require_privilege: bool = True) -> Tuple[List[str], Optional[str]]:
    """
    根据运行时权限模式构建命令

    Returns:
        (final_cmd, stdin_text)
    """
    if not require_privilege:
        return cmd, None

    config = get_privilege_config()

    if config.mode == "root":
        return cmd, None

    if config.mode == "sudo_nopasswd":
        return ["sudo", "-n", *cmd], None

    if config.mode == "sudo_password":
        return ["sudo", "-S", "-p", "", *cmd], f"{config.sudo_password or ''}\n"

    return cmd, None


def check_privilege_capability(require_privilege: bool = True) -> Tuple[bool, Optional[str]]:
    """
    预检查当前权限模式是否足以执行需要提权的命令
    """
    if not require_privilege:
        return True, None

    config = get_privilege_config()

    if config.mode == "root":
        return True, None

    if config.mode == "sudo_nopasswd":
        result = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, None
        return False, "当前服务器声明为 sudo_nopasswd，但 sudo -n true 执行失败"

    if config.mode == "sudo_password":
        if not config.sudo_password:
            return False, "当前服务器需要 sudo 密码，但 Node Agent 未配置 sudo_password"
        result = subprocess.run(
            ["sudo", "-S", "-p", "", "true"],
            input=f"{config.sudo_password}\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return True, None
        return False, "当前服务器配置了 sudo_password，但 sudo 校验失败，请检查密码是否正确"

    return False, "当前服务器未配置可用提权方式，无法执行需要 root/sudo 的操作"
