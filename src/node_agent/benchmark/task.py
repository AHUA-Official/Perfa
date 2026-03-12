"""
压测任务定义
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List
import subprocess
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"            # 等待执行
    PREPARING = "preparing"        # 准备中（检查工具、清理现场）
    RUNNING = "running"            # 执行中
    PAUSED = "paused"              # 已暂停
    COLLECTING = "collecting"      # 采集结果中
    CLEANING = "cleaning"          # 清理现场中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 失败
    CANCELLED = "cancelled"        # 已取消


@dataclass
class BenchmarkTask:
    """压测任务"""
    task_id: str                          # 任务ID
    test_name: str                        # 测试名称 (unixbench/superpi/stream/mlc/fio/hping3)
    params: Dict[str, Any]                # 测试参数（支持扩展）
    status: TaskStatus = TaskStatus.PENDING
    process: Optional[subprocess.Popen] = None  # 进程句柄
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None     # 测试结果
    error: Optional[str] = None                 # 错误信息
    
    # 文件路径
    working_dir: Optional[str] = None           # 工作目录
    output_file: Optional[str] = None           # 输出文件路径
    log_file: Optional[str] = None              # 日志文件路径
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.task_id:
            self.task_id = self._generate_task_id()
    
    @staticmethod
    def _generate_task_id() -> str:
        """生成任务ID"""
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "test_name": self.test_name,
            "params": self.params,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "result": self.result,
            "error": self.error,
            "working_dir": self.working_dir,
            "output_file": self.output_file,
            "log_file": self.log_file,
        }
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """计算运行时长"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def short_id(self) -> str:
        """短ID（用于日志文件名）"""
        return self.task_id[:6]


@dataclass
class BenchmarkParams:
    """
    压测参数基类
    不同工具可以继承此类定义自己的参数结构
    """
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            k: v for k, v in self.__dict__.items()
            if not k.startswith('_')
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BenchmarkParams':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})


# ========== 各工具参数定义 ==========

@dataclass
class StreamParams(BenchmarkParams):
    """STREAM 参数"""
    array_size: int = 100_000_000      # 数组大小（元素个数）
    ntimes: int = 10                    # 重复次数
    offset: int = 0                     # 偏移量
    nt: int = 1                         # 线程数


@dataclass
class SuperPiParams(BenchmarkParams):
    """SuperPi 参数"""
    digits: int = 20                    # 计算位数（百万位）


@dataclass
class UnixBenchParams(BenchmarkParams):
    """UnixBench 参数"""
    copies: Optional[int] = None        # 并行拷贝数，None表示自动（CPU核心数）
    tests: Optional[List[str]] = None   # 指定测试项，None表示全部


@dataclass
class MLCParams(BenchmarkParams):
    """MLC 参数"""
    test_type: str = "bandwidth"        # 测试类型
    max_data_size: str = "1G"           # 最大数据大小


@dataclass
class FioParams(BenchmarkParams):
    """FIO 参数（参数很多，支持扩展）"""
    filename: Optional[str] = None      # 测试文件路径
    size: str = "1G"                    # 测试数据大小
    bs: str = "4k"                      # 块大小
    ioengine: str = "libaio"            # IO引擎
    iodepth: int = 32                   # IO深度
    numjobs: int = 1                    # 并发任务数
    rw: str = "randread"                # 读写模式
    direct: int = 1                     # 直接IO
    runtime: Optional[int] = None       # 运行时间（秒）
    time_based: bool = False            # 是否基于时间
    # ... 更多参数可通过 params dict 扩展
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 额外参数


@dataclass
class Hping3Params(BenchmarkParams):
    """hping3 参数"""
    target: str = "127.0.0.1"           # 目标地址
    count: int = 100                    # 发送次数
    interval: str = "u1000"             # 发送间隔（微秒）
    data_size: int = 0                  # 数据大小
    mode: str = "icmp"                  # 模式（icmp/tcp/udp）
