"""
压力测试模块
负责执行压力测试并收集测试结果

主要组件：
- BenchmarkExecutor: 任务执行器（核心）
- BenchmarkTask: 任务定义
- ResultCollector: 结果采集器
- Cleaner: 现场清理器
- Runners: 各工具的运行器

使用示例：
    from node_agent.benchmark import BenchmarkExecutor
    from node_agent.benchmark.runners import StreamRunner
    from node_agent.tool import ToolManager
    
    # 创建执行器
    tool_manager = ToolManager()
    executor = BenchmarkExecutor(tool_manager)
    
    # 注册运行器
    executor.register_runner(StreamRunner())
    
    # 执行测试
    result = executor.run_benchmark("stream", {"array_size": 100_000_000})
"""

from .task import (
    BenchmarkTask,
    TaskStatus,
    BenchmarkParams,
    StreamParams,
    SuperPiParams,
    UnixBenchParams,
    MLCParams,
    FioParams,
    Hping3Params,
)

from .result import ResultCollector, BenchmarkResult
from .cleaner import Cleaner
from .executor import BenchmarkExecutor, BenchmarkError, ToolNotInstalledError, TaskRunningError

from . import runners

__all__ = [
    # 核心类
    'BenchmarkExecutor',
    'BenchmarkTask',
    'ResultCollector',
    'Cleaner',
    
    # 状态和参数
    'TaskStatus',
    'BenchmarkParams',
    'StreamParams',
    'SuperPiParams',
    'UnixBenchParams',
    'MLCParams',
    'FioParams',
    'Hping3Params',
    
    # 结果
    'BenchmarkResult',
    
    # 异常
    'BenchmarkError',
    'ToolNotInstalledError',
    'TaskRunningError',
    
    # 运行器模块
    'runners',
]