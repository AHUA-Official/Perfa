"""
网络压力测试工具
"""
from typing import Dict
import logging

from .base import BaseTool, ToolStatus


logger = logging.getLogger(__name__)


class Hping3Tool(BaseTool):
    """hping3 网络测试工具"""
    
    def __init__(self):
        super().__init__(
            name="hping3",
            description="hping3 - 网络探测和压力测试工具",
            category="net"
        )
        self.apt_package = "hping3"
    
    def install(self) -> bool:
        """安装hping3"""
        logger.info(f"Installing {self.name}...")
        
        # hping3可以通过apt安装
        if self._apt_install(self.apt_package):
            self.binary_path = "/usr/sbin/hping3"
            logger.info(f"Successfully installed {self.name}")
            return True
        
        return False
    
    def check(self) -> Dict:
        """检查hping3状态"""
        # 检查系统PATH中是否存在
        if self._check_command_exists("hping3"):
            self.binary_path = self._run_command(["which", "hping3"])[1].strip()
            
            # 获取版本
            returncode, stdout, stderr = self._run_command(["hping3", "--version"])
            version = stdout.strip().split('\n')[0] if returncode == 0 else "unknown"
            
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": version,
                "message": "hping3 is installed and ready"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "hping3 is not installed"
        }
    
    def verify(self) -> bool:
        """验证 hping3 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查命令是否存在
        if not self._check_command_exists("hping3"):
            return False
        
        # 快速测试：检查版本信息
        try:
            returncode, stdout, stderr = self._run_command(
                ["hping3", "--version"],
                timeout=2
            )
            # hping3 会输出版本信息
            return "hping" in stdout or "hping" in stderr
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载hping3"""
        logger.info(f"Uninstalling {self.name}...")
        
        if self._apt_remove(self.apt_package):
            self.binary_path = None
            logger.info(f"Successfully uninstalled {self.name}")
            return True
        
        return False
