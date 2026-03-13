"""Agent 返回的数据模型"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any


class AgentStatus(BaseModel):
    """Agent 状态"""
    agent_id: str
    status: str  # online/offline/degraded
    version: str
    uptime_seconds: int
    current_task: Optional[Dict[str, Any]] = None


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
    """系统状态（实时）"""
    cpu_percent: float
    cpu_freq_mhz: float
    memory_percent: float
    memory_available_gb: float
    disk_percent: float
    disk_free_gb: float
    load_average_1min: float
    uptime_seconds: int


class BenchmarkResult(BaseModel):
    """压测结果"""
    task_id: str
    test_name: str
    status: str  # completed/failed
    duration_seconds: Optional[float] = None
    metrics: Optional[Dict[str, Any]] = None  # 测试指标
    log_file: Optional[str] = None
    error: Optional[str] = None
