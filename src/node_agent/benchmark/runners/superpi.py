"""
SuperPi CPU浮点计算性能测试运行器
"""
import re
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class SuperPiRunner(BaseRunner):
    """
    SuperPi CPU浮点计算性能测试运行器
    
    SuperPi 计算圆周率到指定位数，用于测试CPU浮点性能
    测试时间根据位数而定，通常1-10分钟
    """
    
    name = "superpi"
    description = "SuperPi - CPU floating-point performance test"
    category = "cpu"
    typical_duration_seconds = 300  # 5分钟
    requires_async = False
    
    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """准备测试环境"""
        tool = tool_manager.get_tool("superpi")
        if not tool:
            return False
        
        status = tool.check()
        status_value = status.get("status")
        # 支持 Enum 和字符串两种格式
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        
        if status_value != "installed":
            return False
        
        self.binary_path = tool.binary_path
        return True
    
    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        SuperPi 参数：计算的位数 (1000, 10000, 100000, 1000000 等)
        """
        params = task.params or {}
        digits = params.get("digits", 1000000)  # 默认计算到100万位
        
        cmd = [self.binary_path, str(digits)]
        
        return cmd
    
    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 SuperPi 输出
        
        典型输出：
        Calculation of PI up to 1000000 decimal digits
        
        Start of PI calculation...
        End of PI calculation.
        
        Total calculation time: 12.345 seconds.
        Total verification time: 1.234 seconds.
        
        PI = 3.14159265358979323846...
        """
        metrics = {
            "digits": task.params.get("digits", 1000000),
            "calculation_time_sec": None,
            "verification_time_sec": None,
            "total_time_sec": None,
            "raw_output": output  # 添加原始输出
        }
        
        # 解析计算时间
        calc_match = re.search(r"calculation time[:\s]+([\d.]+)\s*seconds?", output, re.IGNORECASE)
        if calc_match:
            metrics["calculation_time_sec"] = float(calc_match.group(1))
        
        # 解析验证时间
        verify_match = re.search(r"verification time[:\s]+([\d.]+)\s*seconds?", output, re.IGNORECASE)
        if verify_match:
            metrics["verification_time_sec"] = float(verify_match.group(1))
        
        # 解析总时间
        total_match = re.search(r"total[^:]*time[:\s]+([\d.]+)\s*seconds?", output, re.IGNORECASE)
        if total_match:
            metrics["total_time_sec"] = float(total_match.group(1))
        elif metrics["calculation_time_sec"]:
            # 如果没有total，用calculation代替
            metrics["total_time_sec"] = metrics["calculation_time_sec"]
        
        return metrics
    
    def get_cleanup_patterns(self) -> List[str]:
        """获取需要清理的文件模式"""
        return ["pi_*.txt", "*.tmp"]
    
    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """
        获取超时时间
        
        根据计算位数估算超时时间
        """
        digits = int(params.get("digits", 1000000))
        
        # 经验估算：每100万位约需30-60秒
        # 设置为估算时间的5倍
        base_seconds = (digits / 1000000) * 60
        timeout = max(120, min(3600, int(base_seconds * 5)))
        
        return timeout
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数"""
        errors = []
        
        try:
            digits = int(params.get("digits", 1000000))
        except (ValueError, TypeError):
            errors.append("digits must be a valid integer")
            return errors
        
        if digits < 1000:
            errors.append("digits must be at least 1000")
        if digits > 100000000:  # 1亿位
            errors.append("digits too large, max 100,000,000")
        
        return errors
