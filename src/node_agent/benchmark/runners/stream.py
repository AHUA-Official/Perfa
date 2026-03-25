"""
STREAM 内存带宽测试运行器
"""
import re
import os
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class StreamRunner(BaseRunner):
    """
    STREAM 内存带宽测试运行器
    
    STREAM 是短时间测试（1-5分钟），采用同步执行
    """
    
    name = "stream"
    description = "STREAM memory bandwidth benchmark"
    category = "mem"
    typical_duration_seconds = 300  # 5分钟
    requires_async = False  # 同步执行

    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """
        准备测试环境
        
        检查 stream 工具是否安装
        """
        tool = tool_manager.get_tool("stream")
        if not tool:
            return False
        
        status = tool.check()
        status_value = status.get("status")
        # 支持 Enum 和字符串两种格式
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        
        if status_value != "installed":
            return False

        # 设置二进制路径
        self.binary_path = tool.binary_path
        return True

    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        STREAM 参数通过环境变量传递：
        - STREAM_ARRAY_SIZE: 数组大小
        - NTIMES: 重复次数
        - OFFSET: 偏移量
        """
        params = task.params or {}
        
        cmd = [self.binary_path]
        
        # STREAM 通过环境变量或命令行参数接收配置
        # 这里我们在运行时设置环境变量
        env = os.environ.copy()
        
        array_size = params.get("array_size", 100_000_000)
        ntimes = params.get("ntimes", 10)
        offset = params.get("offset", 0)
        nt = params.get("nt", 1)  # 线程数，通过 OMP 控制
        
        # 设置环境变量
        env["STREAM_ARRAY_SIZE"] = str(array_size)
        env["NTIMES"] = str(ntimes)
        env["OFFSET"] = str(offset)
        env["OMP_NUM_THREADS"] = str(nt)
        
        # 保存环境变量到 task，供执行时使用
        task._env = env
        
        return cmd

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 STREAM 输出
        
        典型输出：
        -------------------------------------------------------------
        This system uses 8 bytes per array element.
        -------------------------------------------------------------
        Array size = 100000000 (elements), Offset = 0 (elements)
        Memory per array = 762.9 MiB (= 0.7 GiB).
        Total memory required = 2288.8 MiB (= 2.2 GiB).
        Each kernel will be executed 10 times.
        -------------------------------------------------------------
        Your timer granularity appears to be 1 nanoseconds.
        -------------------------------------------------------------
        Function    Best Rate MB/s  Avg time     Min time     Max time
        Copy:           45000.5     0.035600     0.035555     0.035700
        Scale:          42000.3     0.038100     0.038095     0.038110
        Add:            48000.2     0.050000     0.049998     0.050010
        Triad:          47000.1     0.051100     0.051063     0.051200
        -------------------------------------------------------------
        """
        metrics = {
            "copy_rate_mbs": None,
            "scale_rate_mbs": None,
            "add_rate_mbs": None,
            "triad_rate_mbs": None,
            "threads": task.params.get("nt", 1),
        }
        
        # 解析每个操作的带宽
        patterns = {
            "copy": r"Copy:\s+(\d+\.?\d*)",
            "scale": r"Scale:\s+(\d+\.?\d*)",
            "add": r"Add:\s+(\d+\.?\d*)",
            "triad": r"Triad:\s+(\d+\.?\d*)"
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                rate = float(match.group(1))
                metrics[f"{key}_rate_mbs"] = rate
        
        # 计算平均带宽
        rates = [v for k, v in metrics.items() if k.endswith("_rate_mbs") and v is not None]
        if rates:
            metrics["avg_rate_mbs"] = sum(rates) / len(rates)
        
        return metrics

    def get_cleanup_patterns(self) -> List[str]:
        """获取需要清理的文件模式"""
        return ["stream_*", "*.tmp"]

    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """
        获取超时时间
        
        根据 array_size 估算超时时间
        """
        array_size = params.get("array_size", 100_000_000)
        ntimes = params.get("ntimes", 10)
        
        # 基本时间估算：每 100M 元素 * 10 次 约 1 分钟
        base_minutes = (array_size / 100_000_000) * ntimes
        
        # 最小 5 分钟，最大 30 分钟
        timeout = max(300, min(1800, int(base_minutes * 60 * 3)))
        
        return timeout

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数"""
        errors = []
        
        array_size = params.get("array_size", 100_000_000)
        if array_size < 1000:
            errors.append("array_size must be at least 1000")
        if array_size > 1_000_000_000:
            errors.append("array_size too large, max 1,000,000,000")
        
        ntimes = params.get("ntimes", 10)
        if ntimes < 1 or ntimes > 1000:
            errors.append("ntimes must be between 1 and 1000")
        
        nt = params.get("nt", 1)
        if nt < 1:
            errors.append("nt (threads) must be at least 1")
        
        return errors
