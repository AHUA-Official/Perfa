"""数据模型"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class Server(BaseModel):
    """服务器信息"""
    server_id: str
    ip: str
    port: int = 22
    alias: str = ""
    agent_id: Optional[str] = None
    agent_port: Optional[int] = None  # Agent 的 HTTP 端口
    ssh_user: str = ""
    ssh_password_encrypted: Optional[str] = None  # 加密后的 SSH 密码
    ssh_key_path: Optional[str] = None  # SSH 私钥路径
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class Agent(BaseModel):
    """Agent 信息"""
    agent_id: str
    server_id: str
    status: str = "offline"  # online/offline/degraded
    version: str = ""
    last_seen: Optional[datetime] = None
    created_at: datetime


class Task(BaseModel):
    """任务信息"""
    task_id: str
    server_id: str
    agent_id: str
    test_name: str  # unixbench/stream/fio/...
    params: dict
    status: str = "pending"  # pending/running/completed/failed/cancelled
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
