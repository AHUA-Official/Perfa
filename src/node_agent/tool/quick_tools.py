"""
短时基准测试工具
"""
from typing import Dict
import logging

from .base import BaseTool, ToolStatus


logger = logging.getLogger(__name__)


class PackageTool(BaseTool):
    """基于系统包管理器安装的通用工具"""

    package_name: str = ""
    command_name: str = ""
    version_args: list[str] = ["--version"]

    def install(self) -> bool:
        logger.info(f"Installing {self.name}...")
        if self._install_package(self.package_name):
            self.binary_path = self.command_name
            return True
        return False

    def check(self) -> Dict:
        if self._check_command_exists(self.command_name):
            self.binary_path = self._run_command(["which", self.command_name])[1].strip() or self.command_name
            returncode, stdout, stderr = self._run_command([self.command_name, *self.version_args], timeout=5)
            version = (stdout or stderr).strip().splitlines()[0] if returncode == 0 and (stdout or stderr) else "unknown"
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": version,
                "message": f"{self.name} is installed and ready",
            }

        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": f"{self.name} is not installed",
        }

    def verify(self) -> bool:
        if not self._check_command_exists(self.command_name):
            return False
        returncode, stdout, stderr = self._run_command([self.command_name, *self.version_args], timeout=5)
        return returncode == 0 and bool((stdout or stderr).strip())

    def uninstall(self) -> bool:
        logger.info(f"Uninstalling {self.name}...")
        if self._remove_package(self.package_name):
            self.binary_path = None
            return True
        return False


class SysbenchTool(PackageTool):
    def __init__(self):
        super().__init__(
            name="sysbench",
            description="sysbench - modular benchmark tool",
            category="cpu",
        )
        self.package_name = "sysbench"
        self.command_name = "sysbench"


class OpenSSLTool(PackageTool):
    def __init__(self):
        super().__init__(
            name="openssl_speed",
            description="OpenSSL speed - crypto performance benchmark",
            category="cpu",
        )
        self.package_name = "openssl"
        self.command_name = "openssl"

    def check(self) -> Dict:
        result = super().check()
        if result["status"] == ToolStatus.INSTALLED:
            result["message"] = "OpenSSL is installed and speed benchmark is ready"
        return result


class StressNgTool(PackageTool):
    def __init__(self):
        super().__init__(
            name="stress_ng",
            description="stress-ng - system stress and micro-benchmark tool",
            category="cpu",
        )
        self.package_name = "stress-ng"
        self.command_name = "stress-ng"


class Iperf3Tool(PackageTool):
    def __init__(self):
        super().__init__(
            name="iperf3",
            description="iperf3 - network throughput benchmark tool",
            category="net",
        )
        self.package_name = "iperf3"
        self.command_name = "iperf3"


class SevenZipTool(PackageTool):
    def __init__(self):
        super().__init__(
            name="7z_b",
            description="7-Zip benchmark mode",
            category="cpu",
        )
        self.package_name = "p7zip-full"
        self.command_name = "7z"
        self.version_args = []

    def verify(self) -> bool:
        if not self._check_command_exists(self.command_name):
            return False
        returncode, stdout, stderr = self._run_command([self.command_name], timeout=5)
        text = f"{stdout}\n{stderr}".lower()
        return returncode == 0 and "7-zip" in text
