"""Agent 返回的数据模型"""
from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional, Dict, Any


class AgentStatus(BaseModel):
    """Agent 状态"""
    agent_id: str
    status: str = "online"  # 默认 online，兼容 Agent 不返回此字段
    version: str
    uptime_seconds: int
    current_task: Optional[Dict[str, Any]] = None
    monitor_running: bool = False  # 兼容 Agent 额外返回的字段


class SystemInfo(BaseModel):
    """系统信息（静态）"""
    hostname: str
    os: str
    arch: str
    cpu_model: str
    cpu_cores: int
    memory_total_gb: float
    kernel: str
    machine_id: str


class SystemStatus(BaseModel):
    """系统状态（实时）- 支持扁平化和嵌套两种格式"""
    cpu_percent: Optional[float] = None
    cpu_freq_mhz: Optional[float] = None
    memory_percent: Optional[float] = None
    memory_available_gb: Optional[float] = None
    disk_percent: Optional[float] = None
    disk_free_gb: Optional[float] = None
    load_average_1min: Optional[float] = None
    uptime_seconds: Optional[int] = None

    @classmethod
    def from_agent_response(cls, data: Dict[str, Any]) -> "SystemStatus":
        """从 Agent 返回的嵌套格式解析"""
        # 支持扁平化格式（直接字段）
        if "cpu_percent" in data:
            return cls(**data)

        # 支持嵌套格式（Agent 实际返回）
        cpu = data.get("cpu", {})
        memory = data.get("memory", {})
        disk = data.get("disk", {})
        load_avg = data.get("load_average", {})

        return cls(
            cpu_percent=cpu.get("percent"),
            cpu_freq_mhz=cpu.get("freq_mhz"),
            memory_percent=memory.get("percent"),
            memory_available_gb=memory.get("available_gb"),
            disk_percent=disk.get("percent"),
            disk_free_gb=disk.get("free_gb"),
            load_average_1min=load_avg.get("1min"),
            uptime_seconds=data.get("uptime_seconds")
        )


class BenchmarkResult(BaseModel):
    """压测结果"""
    task_id: str
    test_name: str
    status: str  # completed/failed
    duration_seconds: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None  # 测试指标
    log_file: Optional[str] = None
    error: Optional[str] = None
