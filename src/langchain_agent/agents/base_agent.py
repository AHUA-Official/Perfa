"""
Perfa - LangChain Agent Module

@file: agents/base_agent.py
@desc: Agent基类定义
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()


@dataclass
class ToolCall:
    """工具调用记录"""
    tool_name: str
    arguments: Dict[str, Any]
    result: Any
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResponse:
    """Agent响应"""
    query: str
    result: str
    tool_calls: List[ToolCall]
    execution_time: float
    tokens_used: int
    is_success: bool
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    thinking_process: Optional[str] = None  # Agent的思考过程
    reasoning_time: Optional[float] = None  # LLM推理耗时


class IAgent(ABC):
    """
    Agent接口定义
    
    所有Agent必须实现此接口
    """
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        logger.info(f"初始化Agent: {name} - {description}")
    
    @abstractmethod
    async def run(self, query: str, **kwargs) -> AgentResponse:
        """
        执行查询
        
        Args:
            query: 用户查询
            **kwargs: 额外参数（如session_id, context等）
        
        Returns:
            AgentResponse: 执行结果
        """
        pass
    
    @abstractmethod
    def reset(self):
        """重置Agent状态"""
        pass
    
    @abstractmethod
    def get_execution_logs(self) -> List[Dict[str, Any]]:
        """获取执行日志"""
        pass


class BaseAgent(IAgent):
    """
    Agent基类
    
    提供通用功能和日志记录
    """
    
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.execution_logs: List[Dict[str, Any]] = []
        self.start_time: Optional[datetime] = None
        logger.info(f"Agent基类初始化完成: {name}")
    
    def _log_execution(self, level: str, message: str, **kwargs):
        """记录执行日志"""
        log_entry = {
            "timestamp": datetime.now(),
            "level": level,
            "message": message,
            **kwargs
        }
        self.execution_logs.append(log_entry)
        
        # 同时记录到主日志
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        elif level == "debug":
            logger.debug(message)
    
    def reset(self):
        """重置执行日志"""
        logger.info(f"重置Agent执行日志: {self.name}")
        self.execution_logs.clear()
        self.start_time = None
    
    def get_execution_logs(self) -> List[Dict[str, Any]]:
        """获取执行日志"""
        return self.execution_logs
    
    def _calculate_execution_time(self) -> float:
        """计算执行时间"""
        if self.start_time is None:
            return 0.0
        return (datetime.now() - self.start_time).total_seconds()
