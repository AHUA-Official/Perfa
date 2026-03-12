"""
MLC (Memory Latency Checker) 内存延迟和带宽测试运行器
"""
import re
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class MlcRunner(BaseRunner):
    """
    MLC 内存延迟和带宽测试运行器
    
    MLC 是 Intel 提供的内存延迟测试工具，测试时间较短（1-3分钟）
    """
    
    name = "mlc"
    description = "Intel MLC - Memory Latency Checker"
    category = "mem"
    typical_duration_seconds = 180  # 3分钟
    requires_async = False
    
    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """准备测试环境"""
        tool = tool_manager.get_tool("mlc")
        if not tool:
            return False
        
        status = tool.check()
        if status.get("status") != "installed":
            return False
        
        self.binary_path = tool.binary_path
        return True
    
    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        MLC 常用测试模式：
        - --idle_latency: 空闲延迟测试
        - --loaded_latency: 负载延迟测试
        - --bandwidth_matrix: 带宽矩阵测试
        - --peak_injection_bandwidth: 峰值注入带宽
        """
        params = task.params or {}
        test_mode = params.get("mode", "idle_latency")
        
        cmd = [self.binary_path]
        
        if test_mode == "idle_latency":
            cmd.append("--idle_latency")
        elif test_mode == "loaded_latency":
            cmd.extend(["--loaded_latency", "-X"])
        elif test_mode == "bandwidth":
            cmd.append("--peak_injection_bandwidth")
        else:
            cmd.append("--idle_latency")
        
        return cmd
    
    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 MLC 输出
        
        典型 idle_latency 输出：
        Intel(R) Memory Latency Checker - v3.12
        Command line parameters: --idle_latency
        
        Measuring idle latencies (ns)...
                Numa node
        Numa node      0
           0        67.8
        
        典型 loaded_latency 输出：
        Intel(R) Memory Latency Checker - v3.12
        Using buffer size of 200.000MiB
        
        Measuring idle latencies (ns)...
        ...
        """
        metrics = {
            "test_mode": task.params.get("mode", "idle_latency"),
            "idle_latency_ns": None,
            "loaded_latency_ns": None,
            "bandwidth_gbs": None,
        }
        
        # 解析 idle latency
        # 格式: 数字 + 数字 + 数字.数字 (如 "   0        67.8")
        idle_match = re.search(r"^\s+\d+\s+([\d.]+)\s*$", output, re.MULTILINE)
        if idle_match:
            metrics["idle_latency_ns"] = float(idle_match.group(1))
        
        # 解析 loaded latency (取平均值)
        loaded_matches = re.findall(r"^\s+\d+\s+([\d.]+)\s*$", output, re.MULTILINE)
        if loaded_matches and len(loaded_matches) > 1:
            latencies = [float(m) for m in loaded_matches[1:]]  # 跳过表头行
            if latencies:
                metrics["loaded_latency_ns"] = sum(latencies) / len(latencies)
        
        # 解析 bandwidth
        bw_match = re.search(r"([\d.]+)\s+GB/s", output)
        if bw_match:
            metrics["bandwidth_gbs"] = float(bw_match.group(1))
        
        return metrics
    
    def get_cleanup_patterns(self) -> List[str]:
        """获取需要清理的文件模式"""
        return ["mlc_*", "*.mlc"]
    
    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """获取超时时间"""
        mode = params.get("mode", "idle_latency")
        if mode == "bandwidth":
            return 600  # 10分钟
        return 300  # 5分钟
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数"""
        errors = []
        
        mode = params.get("mode", "idle_latency")
        valid_modes = ["idle_latency", "loaded_latency", "bandwidth"]
        if mode not in valid_modes:
            errors.append(f"Invalid mode: {mode}, must be one of {valid_modes}")
        
        return errors
