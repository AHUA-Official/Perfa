"""
Pydantic Schemas for OpenAI Compatible API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: user/assistant/system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request (OpenAI compatible)"""
    model: str = Field(default="perfa-agent", description="Model name (ignored)")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    session_id: Optional[str] = Field(default=None, description="Session ID")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    stream: bool = Field(default=False, description="Enable streaming output")
    temperature: Optional[float] = Field(default=None, description="Temperature (ignored)")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens (ignored)")


class ChatChoice(BaseModel):
    """Chat choice"""
    index: int = Field(default=0)
    message: Optional[ChatMessage] = None
    delta: Optional[Dict[str, str]] = None
    finish_reason: Optional[str] = None


class ChatUsage(BaseModel):
    """Token usage"""
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class ChatResponse(BaseModel):
    """Chat completion response (OpenAI compatible)"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{datetime.now().timestamp()}")
    object: str = Field(default="chat.completion")
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = Field(default="perfa-agent")
    choices: List[ChatChoice]
    usage: Optional[ChatUsage] = None


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    owned_by: str = "perfa"


class ModelList(BaseModel):
    """Model list response"""
    object: str = "list"
    data: List[ModelInfo]


# ===== Extended API Schemas =====


class ServerInfo(BaseModel):
    """服务器信息"""
    server_id: str = Field(..., description="服务器唯一标识")
    ip: str = Field(..., description="服务器 IP")
    alias: Optional[str] = Field(None, description="服务器别名")
    status: str = Field("unknown", description="在线状态: online/offline/unknown")
    tags: List[str] = Field(default_factory=list, description="标签")
    hardware: Optional[Dict[str, Any]] = Field(None, description="硬件信息")
    agent_id: Optional[str] = Field(None, description="已部署的 Agent ID")
    agent_port: Optional[int] = Field(None, description="Agent 端口")
    agent_status: Optional[str] = Field(None, description="Agent 状态")
    agent_version: Optional[str] = Field(None, description="Agent 版本")
    current_task: Optional[Dict[str, Any]] = Field(None, description="当前任务")


class ServerListResponse(BaseModel):
    """服务器列表响应"""
    servers: List[ServerInfo] = Field(default_factory=list)


class WorkflowNodeStatus(BaseModel):
    """工作流节点状态"""
    name: str = Field(..., description="节点名称")
    status: str = Field("pending", description="节点状态: pending/running/completed/failed")
    display_name: Optional[str] = Field(None, description="节点显示名称")
    error: Optional[str] = Field(None, description="错误信息")


class WorkflowStatusResponse(BaseModel):
    """工作流状态响应"""
    scenario: str = Field(..., description="场景名称")
    session_id: str = Field(..., description="会话 ID")
    nodes: List[WorkflowNodeStatus] = Field(default_factory=list)
    current_node: Optional[str] = Field(None, description="当前执行节点")
    completed_nodes: List[str] = Field(default_factory=list, description="已完成节点列表")
    progress: float = Field(0.0, description="完成进度 0.0~1.0")


class ReportInfo(BaseModel):
    """报告摘要信息"""
    id: str = Field(..., description="报告 ID")
    type: str = Field(..., description="测试类型")
    server_id: str = Field(..., description="服务器 ID")
    created_at: str = Field(..., description="创建时间")
    status: str = Field("completed", description="报告状态")
    summary: Optional[str] = Field(None, description="摘要")


class ReportListResponse(BaseModel):
    """报告列表响应"""
    reports: List[ReportInfo] = Field(default_factory=list)


class ReportDetail(BaseModel):
    """报告详情"""
    id: str
    type: str
    server_id: str
    created_at: str
    status: str = "completed"
    summary: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    charts: Optional[List[Dict[str, Any]]] = None


class SessionSummary(BaseModel):
    """会话摘要"""
    session_id: str
    title: str = "新对话"
    message_count: int = 0
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    last_user_message: Optional[str] = None


class SessionListResponse(BaseModel):
    """会话列表响应"""
    sessions: List[SessionSummary] = Field(default_factory=list)


class SessionMessage(BaseModel):
    """会话消息"""
    role: str
    content: str
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionDetail(BaseModel):
    """会话详情"""
    session_id: str
    title: str = "新对话"
    message_count: int = 0
    created_at: Optional[str] = None
    last_active: Optional[str] = None
    last_user_message: Optional[str] = None
    messages: List[SessionMessage] = Field(default_factory=list)
