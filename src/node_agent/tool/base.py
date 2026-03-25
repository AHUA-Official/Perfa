"""
工具基类定义
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional
import subprocess
import shutil
import logging
from pathlib import Path


logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """工具状态枚举"""
    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    AVAILABLE = "available"
    ERROR = "error"


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self, name: str, description: str, category: str):
        """
        初始化工具
        
        Args:
            name: 工具名称
            description: 工具描述
            category: 工具类别 (cpu/mem/disk/net)
        """
        self.name = name
        self.description = description
        self.category = category
        self.binary_path: Optional[str] = None
        self.version: Optional[str] = None
        
        # 二进制文件存储路径
        self.binaries_dir = Path(__file__).parent / "binaries" / category
        self.binaries_dir.mkdir(parents=True, exist_ok=True)
    
    @abstractmethod
    def install(self) -> bool:
        """
        安装工具
        
        Returns:
            安装是否成功
        """
        pass
    
    @abstractmethod
    def check(self) -> Dict:
        """
        检查工具状态
        
        Returns:
            包含状态信息的字典:
            {
                "status": ToolStatus,
                "binary_path": str or None,
                "version": str or None,
                "message": str
            }
        """
        pass
    
    @abstractmethod
    def uninstall(self) -> bool:
        """
        卸载工具
        
        Returns:
            卸载是否成功
        """
        pass
    
    def get_info(self) -> Dict:
        """
        获取工具信息
        
        Returns:
            工具基本信息字典
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "binary_path": self.binary_path,
            "version": self.version
        }
    
    def _run_command(self, cmd: list, timeout: int = 300, cwd: Optional[str] = None) -> tuple:
        """
        执行命令
        
        Args:
            cmd: 命令列表
            timeout: 超时时间（秒）
            cwd: 工作目录
        
        Returns:
            (return_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {' '.join(cmd)}")
            return -1, "", "Command timeout"
        except Exception as e:
            logger.error(f"Command failed: {e}")
            return -1, "", str(e)
    
    def _check_command_exists(self, cmd: str) -> bool:
        """
        检查命令是否存在
        
        Args:
            cmd: 命令名称
        
        Returns:
            命令是否存在
        """
        return shutil.which(cmd) is not None
    
    def _get_package_manager(self) -> str:
        """
        检测系统包管理器
        
        Returns:
            'apt', 'yum', 'dnf' 或 None
        """
        if shutil.which("apt-get"):
            return "apt"
        elif shutil.which("dnf"):
            return "dnf"
        elif shutil.which("yum"):
            return "yum"
        return None

    def _wait_for_apt_lock(self, timeout: int = 60) -> bool:
        """
        等待 apt 锁释放
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否成功获取锁
        """
        import time
        
        lock_files = [
            "/var/lib/dpkg/lock-frontend",
            "/var/lib/dpkg/lock",
            "/var/lib/apt/lists/lock",
            "/var/cache/apt/archives/lock"
        ]
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            # 检查是否所有锁都可用
            locks_held = []
            for lock_file in lock_files:
                if os.path.exists(lock_file):
                    try:
                        # 尝试获取锁信息
                        result = subprocess.run(
                            ["lsof", lock_file],
                            capture_output=True, text=True, timeout=2
                        )
                        if result.returncode == 0 and result.stdout.strip():
                            locks_held.append(lock_file)
                    except Exception:
                        pass
            
            if not locks_held:
                return True
            
            logger.info(f"Waiting for apt lock... (held by other process)")
            time.sleep(2)
        
        return False

    def _install_package(self, package: str) -> bool:
        """
        使用系统包管理器安装包
        
        Args:
            package: 包名
        
        Returns:
            安装是否成功
        """
        pm = self._get_package_manager()
        if not pm:
            logger.error("No supported package manager found (apt/yum/dnf)")
            return False
        
        logger.info(f"Installing {package} via {pm}...")
        
        # apt 需要等待锁
        if pm == "apt":
            if not self._wait_for_apt_lock():
                logger.error(f"Failed to acquire apt lock after timeout. Another package manager is running. Please wait and try again.")
                return False
            
            returncode, stdout, stderr = self._run_command(
                ["sudo", "apt-get", "install", "-y", package]
            )
        elif pm == "dnf":
            returncode, stdout, stderr = self._run_command(
                ["sudo", "dnf", "install", "-y", package]
            )
        else:  # yum
            returncode, stdout, stderr = self._run_command(
                ["sudo", "yum", "install", "-y", package]
            )
        
        if returncode == 0:
            logger.info(f"Successfully installed {package}")
            return True
        else:
            # 提供更友好的错误提示
            error_msg = stderr.strip() if stderr else "Unknown error"
            if "lock" in error_msg.lower():
                error_msg = "Package manager is locked by another process. Please wait and try again."
            logger.error(f"Failed to install {package}: {error_msg}")
            return False

    def _remove_package(self, package: str) -> bool:
        """
        使用系统包管理器卸载包
        
        Args:
            package: 包名
        
        Returns:
            卸载是否成功
        """
        pm = self._get_package_manager()
        if not pm:
            logger.error("No supported package manager found (apt/yum/dnf)")
            return False
        
        logger.info(f"Removing {package} via {pm}...")
        
        # apt 需要等待锁
        if pm == "apt":
            if not self._wait_for_apt_lock():
                logger.error(f"Failed to acquire apt lock after timeout. Another package manager is running. Please wait and try again.")
                return False
            
            returncode, stdout, stderr = self._run_command(
                ["sudo", "apt-get", "remove", "-y", package]
            )
        elif pm == "dnf":
            returncode, stdout, stderr = self._run_command(
                ["sudo", "dnf", "remove", "-y", package]
            )
        else:  # yum
            returncode, stdout, stderr = self._run_command(
                ["sudo", "yum", "remove", "-y", package]
            )
        
        if returncode == 0:
            logger.info(f"Successfully removed {package}")
            return True
        else:
            # 提供更友好的错误提示
            error_msg = stderr.strip() if stderr else "Unknown error"
            if "lock" in error_msg.lower():
                error_msg = "Package manager is locked by another process. Please wait and try again."
            logger.error(f"Failed to remove {package}: {error_msg}")
            return False
    
    def _make_executable(self, file_path: Path):
        """
        设置文件为可执行
        
        Args:
            file_path: 文件路径
        """
        file_path.chmod(0o755)
    
    def verify(self) -> bool:
        """
        验证工具是否真的可用（子类可重写）
        
        Returns:
            工具是否可用
        """
        if not self.binary_path:
            return False
        
        # 默认检查：文件存在且可执行
        binary = Path(self.binary_path)
        if not binary.exists():
            return False
        
        if not os.access(binary, os.X_OK):
            return False
        
        return True
