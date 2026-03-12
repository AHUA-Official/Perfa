"""
压测运行器基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import subprocess

from ..task import BenchmarkTask


@dataclass
class RunnerInfo:
    """运行器信息"""
    name: str
    description: str
    category: str
    typical_duration_seconds: int    # 典型运行时间
    requires_async: bool             # 是否需要异步执行


class BaseRunner(ABC):
    """压测工具运行器基类"""

    # 子类必须定义
    name: str = ""
    description: str = ""
    category: str = ""
    typical_duration_seconds: int = 60
    requires_async: bool = True

    @property
    def info(self) -> RunnerInfo:
        """获取运行器信息"""
        return RunnerInfo(
            name=self.name,
            description=self.description,
            category=self.category,
            typical_duration_seconds=self.typical_duration_seconds,
            requires_async=self.requires_async
        )

    @abstractmethod
    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """
        准备测试环境
        
        Args:
            task: 任务对象
            tool_manager: 工具管理器
        
        Returns:
            准备是否成功
        """
        pass

    @abstractmethod
    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        Args:
            task: 任务对象
        
        Returns:
            命令列表
        """
        pass

    @abstractmethod
    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        收集和解析测试结果
        
        Args:
            task: 任务对象
            output: 命令输出
        
        Returns:
            解析后的指标字典
        """
        pass

    @abstractmethod
    def get_cleanup_patterns(self) -> List[str]:
        """
        获取需要清理的文件/目录模式
        
        Returns:
            glob模式列表
        """
        pass

    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """
        获取超时时间（秒）
        
        Args:
            params: 测试参数
        
        Returns:
            超时时间，None表示不限制
        """
        return self.typical_duration_seconds * 3  # 默认3倍典型时间

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """
        验证参数
        
        Args:
            params: 测试参数
        
        Returns:
            错误消息列表，空列表表示验证通过
        """
        return []  # 默认不验证

    def get_working_subdir(self, task: BenchmarkTask) -> str:
        """
        获取工作子目录名
        
        Args:
            task: 任务对象
        
        Returns:
            子目录名
        """
        return f"{task.test_name}_{task.short_id}"
