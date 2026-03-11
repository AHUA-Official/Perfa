"""
磁盘压力测试工具
"""
import tempfile
import os
from typing import Dict
import logging

from .base import BaseTool, ToolStatus


logger = logging.getLogger(__name__)


class FioTool(BaseTool):
    """FIO 磁盘I/O性能测试工具"""
    
    def __init__(self):
        super().__init__(
            name="fio",
            description="FIO - 灵活的I/O测试工具",
            category="disk"
        )
        self.apt_package = "fio"
    
    def install(self) -> bool:
        """安装FIO"""
        logger.info(f"Installing {self.name}...")
        
        # FIO可以通过apt安装
        if self._apt_install(self.apt_package):
            self.binary_path = "/usr/bin/fio"
            logger.info(f"Successfully installed {self.name}")
            return True
        
        return False
    
    def check(self) -> Dict:
        """检查FIO状态"""
        # 检查系统PATH中是否存在
        if self._check_command_exists("fio"):
            self.binary_path = self._run_command(["which", "fio"])[1].strip()
            
            # 获取版本
            returncode, stdout, stderr = self._run_command(["fio", "--version"])
            version = stdout.strip() if returncode == 0 else "unknown"
            
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": version,
                "message": "FIO is installed and ready"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "FIO is not installed"
        }
    
    def verify(self) -> bool:
        """验证 FIO 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查命令是否存在
        if not self._check_command_exists("fio"):
            return False
        
        # 快速测试：最小化 I/O 测试
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 创建最小化测试配置
                config_file = os.path.join(tmpdir, "test.fio")
                with open(config_file, 'w') as f:
                    f.write(f"""[global]
size=1M
directory={tmpdir}
name=test

[quick-test]
rw=read
bs=4k
iodepth=1
numjobs=1
""")
                
                returncode, stdout, stderr = self._run_command(
                    ["fio", config_file],
                    timeout=3
                )
                
                # FIO 成功运行会输出 "READ" 或 "WRITE"
                return returncode == 0 and ("READ" in stdout or "WRITE" in stdout)
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载FIO"""
        logger.info(f"Uninstalling {self.name}...")
        
        if self._apt_remove(self.apt_package):
            self.binary_path = None
            logger.info(f"Successfully uninstalled {self.name}")
            return True
        
        return False
