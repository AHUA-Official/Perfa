"""
UnixBench CPU 测试运行器
"""
import re
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class UnixBenchRunner(BaseRunner):
    """
    UnixBench CPU 测试运行器
    
    UnixBench 是长时间测试（30-60分钟），采用异步执行
    """
    
    name = "unixbench"
    description = "UnixBench CPU performance benchmark"
    category = "cpu"
    typical_duration_seconds = 3600  # 1小时
    requires_async = True  # 异步执行

    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """准备测试环境"""
        tool = tool_manager.get_tool("unixbench")
        if not tool:
            return False
        
        status = tool.check()
        status_value = status.get("status")
        # 支持 Enum 和字符串两种格式
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        
        if status_value != "installed":
            return False

        # UnixBench wrapper 脚本路径
        self.binary_path = tool.binary_path
        return True

    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        使用 wrapper 脚本执行，wrapper 会自动 cd 到正确目录
        
        参数：
        - copies: 并行拷贝数，None 表示自动
        - tests: 指定测试项，None 表示全部
        """
        params = task.params or {}
        
        # 使用 wrapper 脚本（绝对路径）
        cmd = [self.binary_path]
        
        copies = params.get("copies")
        if copies:
            cmd.extend(["-c", str(copies)])
        
        tests = params.get("tests")
        if tests:
            cmd.extend(tests)
        
        return cmd

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 UnixBench 输出
        
        典型输出：
        System Benchmarks Index Values               BASELINE       RESULT    INDEX
        Dhrystone 2 using register variables         116700.0   87654321.0   7511.1
        Double-Precision Whetstone                       55.0      12345.6   2244.7
        ...
        
        System Benchmarks Index Score                                        1234.5
        
        System Benchmarks Index Score (Copy & Run)                          12345.6
        """
        metrics = {
            "single_core_score": None,
            "multi_core_score": None,
            "tests": {},
            "raw_output": output[-10000:]  # 保留最后部分输出
        }
        
        # 解析单核分数
        single_match = re.search(
            r"System Benchmarks Index Score\s+(\d+\.?\d*)\s*$",
            output, re.MULTILINE
        )
        if single_match:
            metrics["single_core_score"] = float(single_match.group(1))
        
        # 解析多核分数
        multi_match = re.search(
            r"System Benchmarks Index Score.*?(\d+\.?\d*)\s*$",
            output, re.MULTILINE
        )
        if multi_match:
            metrics["multi_core_score"] = float(multi_match.group(1))
        
        return metrics

    def get_cleanup_patterns(self) -> List[str]:
        return ["ubench_*", "*.log", "*.tmp"]

    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """UnixBench 超时时间：默认 2 小时"""
        return 7200
