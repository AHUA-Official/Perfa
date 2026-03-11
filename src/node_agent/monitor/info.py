"""
系统静态信息采集
收集机器架构、CPU型号等静态信息，用于 Prometheus 标签
"""

import platform
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class SystemInfo:
    """系统静态信息采集器"""
    
    _instance = None
    _info: Dict[str, str] = {}
    
    def __new__(cls):
        """单例模式，只采集一次"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._collect()
        return cls._instance
    
    def _collect(self):
        """采集系统静态信息"""
        self._info = {
            'hostname': self._get_hostname(),
            'os': self._get_os(),
            'arch': self._get_arch(),
            'cpu_model': self._get_cpu_model(),
            'cpu_cores': str(self._get_cpu_cores()),
            'memory_total_gb': f"{self._get_memory_total():.1f}",
            'kernel': self._get_kernel(),
            'machine_id': self._get_machine_id(),
        }
        
        logger.info(f"系统信息采集完成: {self._info}")
    
    def _get_hostname(self) -> str:
        """获取主机名"""
        return platform.node()
    
    def _get_os(self) -> str:
        """获取操作系统"""
        return f"{platform.system()} {platform.release()}"
    
    def _get_arch(self) -> str:
        """获取架构"""
        return platform.machine()
    
    def _get_cpu_model(self) -> str:
        """获取 CPU 型号"""
        try:
            # Linux: 从 /proc/cpuinfo 获取
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'model name' in line:
                        return line.split(':')[1].strip()
            # macOS
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return "unknown"
    
    def _get_cpu_cores(self) -> int:
        """获取 CPU 核心数"""
        import os
        return os.cpu_count() or 1
    
    def _get_memory_total(self) -> float:
        """获取内存总量 (GB)"""
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        return kb / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    def _get_kernel(self) -> str:
        """获取内核版本"""
        return platform.release()
    
    def _get_machine_id(self) -> str:
        """获取机器唯一标识"""
        try:
            # Linux: /etc/machine-id
            with open('/etc/machine-id', 'r') as f:
                return f.read().strip()[:12]
        except Exception:
            # 回退: 使用 hostname
            import hashlib
            return hashlib.md5(platform.node().encode()).hexdigest()[:12]
    
    @property
    def info(self) -> Dict[str, str]:
        """获取系统信息字典"""
        return self._info.copy()
    
    def get_labels(self) -> Dict[str, str]:
        """获取 Prometheus 标签格式（仅用于指标标签）"""
        return {
            'hostname': self._info['hostname'],
            'machine_id': self._info['machine_id'],
        }


# 全局实例
system_info = SystemInfo()


if __name__ == "__main__":
    # 测试
    info = SystemInfo()
    print("系统信息:")
    for k, v in info.info.items():
        print(f"  {k}: {v}")
    print("\nPrometheus 标签:")
    for k, v in info.get_labels().items():
        print(f"  {k}={v}")
