"""
Perfa - LangChain Agent Module

@file: core/error_handler.py
@desc: 错误处理和重试机制
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from enum import Enum

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()


class ErrorType(Enum):
    """错误类型枚举"""
    CONNECTION_ERROR = "ConnectionError"
    TIMEOUT_ERROR = "TimeoutError"
    AGENT_OFFLINE = "AgentOffline"
    TOOL_NOT_FOUND = "ToolNotFound"
    INVALID_PARAMS = "InvalidParams"
    EXECUTION_ERROR = "ExecutionError"
    UNKNOWN_ERROR = "UnknownError"


class ErrorHandler:
    """
    错误处理器
    
    处理工具调用失败、重试、降级策略
    """
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0, exponential_backoff: bool = True):
        """
        初始化错误处理器
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            exponential_backoff: 是否使用指数退避
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.exponential_backoff = exponential_backoff
        self.error_stats: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"错误处理器初始化完成，最大重试次数: {max_retries}, 延迟: {retry_delay}秒")
    
    def handle_tool_error(self, error: Exception, tool_name: str) -> Dict[str, Any]:
        """
        处理工具调用错误
        
        Args:
            error: 异常对象
            tool_name: 工具名称
        
        Returns:
            Dict: 包含是否重试、错误信息等
        """
        error_type = self._classify_error(error)
        error_message = str(error)
        
        # 记录错误统计
        if tool_name not in self.error_stats:
            self.error_stats[tool_name] = {
                "count": 0,
                "errors": [],
                "last_error": None
            }
        
        self.error_stats[tool_name]["count"] += 1
        error_record = {
            "type": error_type.value,
            "message": error_message,
            "timestamp": datetime.now()
        }
        self.error_stats[tool_name]["errors"].append(error_record)
        self.error_stats[tool_name]["last_error"] = error_record
        
        # 判断是否应重试
        should_retry = self._should_retry(error_type, tool_name)
        retry_count = self.error_stats[tool_name]["count"]
        
        logger.warning(f"工具调用错误: {tool_name} - {error_type.value}: {error_message}")
        
        if should_retry and retry_count <= self.max_retries:
            logger.info(f"准备重试: {tool_name} (第{retry_count}次)")
        else:
            logger.error(f"工具调用失败: {tool_name}，已达到最大重试次数或错误不可重试")
        
        return {
            "should_retry": should_retry,
            "error_type": error_type.value,
            "error_message": error_message,
            "retry_count": retry_count,
            "max_retries": self.max_retries
        }
    
    async def retry_with_backoff(self, func: Callable, *args, tool_name: str = "unknown", **kwargs) -> Dict[str, Any]:
        """
        带指数退避的重试执行
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            tool_name: 工具名称
            **kwargs: 关键字参数
        
        Returns:
            Dict: 执行结果
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                
                # 如果成功，重置错误统计
                if tool_name in self.error_stats:
                    self.error_stats[tool_name]["count"] = 0
                
                logger.info(f"工具执行成功: {tool_name}")
                return {
                    "success": True,
                    "data": result,
                    "attempts": attempt
                }
                
            except Exception as e:
                error_result = self.handle_tool_error(e, tool_name)
                
                if not error_result["should_retry"] or attempt >= self.max_retries:
                    return {
                        "success": False,
                        "error": error_result["error_message"],
                        "error_type": error_result["error_type"],
                        "attempts": attempt
                    }
                
                # 计算退避时间
                if self.exponential_backoff:
                    backoff_delay = self.retry_delay * (2 ** (attempt - 1))
                else:
                    backoff_delay = self.retry_delay
                
                logger.info(f"等待 {backoff_delay:.1f} 秒后重试: {tool_name}")
                await asyncio.sleep(backoff_delay)
        
        return {
            "success": False,
            "error": "达到最大重试次数",
            "attempts": self.max_retries
        }
    
    def _classify_error(self, error: Exception) -> ErrorType:
        """分类错误类型"""
        error_class = error.__class__.__name__
        error_message = str(error).lower()
        
        # 连接错误
        if any(keyword in error_message for keyword in ["connection", "connect", "network"]):
            return ErrorType.CONNECTION_ERROR
        
        # 超时错误
        if "timeout" in error_message or error_class.endswith("TimeoutError"):
            return ErrorType.TIMEOUT_ERROR
        
        # Agent离线
        if any(keyword in error_message for keyword in ["offline", "unreachable", "refused"]):
            return ErrorType.AGENT_OFFLINE
        
        # 工具未找到
        if "not found" in error_message or error_class == "KeyError":
            return ErrorType.TOOL_NOT_FOUND
        
        # 参数错误
        if any(keyword in error_message for keyword in ["parameter", "argument", "invalid", "missing"]):
            return ErrorType.INVALID_PARAMS
        
        # 执行错误
        if "execution" in error_message or error_class.endswith("ExecutionError"):
            return ErrorType.EXECUTION_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    def _should_retry(self, error_type: ErrorType, tool_name: str) -> bool:
        """判断是否应重试"""
        # 可重试的错误类型
        retryable_errors = [
            ErrorType.CONNECTION_ERROR,
            ErrorType.TIMEOUT_ERROR,
            ErrorType.AGENT_OFFLINE
        ]
        
        # 当前重试次数
        retry_count = self.error_stats.get(tool_name, {}).get("count", 0)
        
        if error_type in retryable_errors and retry_count < self.max_retries:
            return True
        
        return False
    
    def get_error_summary(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取错误统计摘要
        
        Args:
            tool_name: 指定工具名称，None则返回所有工具
        
        Returns:
            Dict: 错误统计信息
        """
        if tool_name:
            if tool_name not in self.error_stats:
                return {}
            
            stats = self.error_stats[tool_name]
            return {
                tool_name: {
                    "total_errors": stats["count"],
                    "recent_errors": stats["errors"][-5:],  # 最近5个错误
                    "last_error": stats["last_error"]
                }
            }
        else:
            # 返回所有工具的错误统计
            return {
                tool: {
                    "total_errors": stats["count"],
                    "last_error": stats["last_error"]
                }
                for tool, stats in self.error_stats.items()
            }
    
    def get_overall_stats(self) -> Dict[str, Any]:
        """获取总体错误统计"""
        total_errors = sum(stats["count"] for stats in self.error_stats.values())
        tools_with_errors = len(self.error_stats)
        
        # 按错误类型统计
        error_type_count: Dict[str, int] = {}
        for stats in self.error_stats.values():
            for error in stats["errors"]:
                error_type = error["type"]
                error_type_count[error_type] = error_type_count.get(error_type, 0) + 1
        
        return {
            "total_errors": total_errors,
            "tools_with_errors": tools_with_errors,
            "error_type_distribution": error_type_count,
            "max_retries_config": self.max_retries,
            "exponential_backoff": self.exponential_backoff
        }
    
    def reset_stats(self, tool_name: Optional[str] = None):
        """
        重置错误统计
        
        Args:
            tool_name: 指定工具，None则重置所有
        """
        if tool_name:
            if tool_name in self.error_stats:
                del self.error_stats[tool_name]
                logger.info(f"重置工具错误统计: {tool_name}")
        else:
            self.error_stats.clear()
            logger.info("重置所有工具错误统计")
