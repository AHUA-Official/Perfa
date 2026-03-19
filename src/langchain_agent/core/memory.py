"""
Perfa - LangChain Agent Module

@file: core/memory.py
@desc: 对话记忆管理
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import deque

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()


class ConversationMemory:
    """
    对话记忆管理器
    
    管理多轮对话上下文，支持会话隔离和自动清理
    """
    
    def __init__(self, max_turns: int = 10, max_age_hours: int = 24):
        """
        初始化记忆管理器
        
        Args:
            max_turns: 每个会话保留的最大轮数
            max_age_hours: 会话最大存活时间（小时）
        """
        self.max_turns = max_turns
        self.max_age_hours = max_age_hours
        self.conversations: Dict[str, deque] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"对话记忆管理器初始化完成，最大轮数: {max_turns}, 最大存活时间: {max_age_hours}小时")
    
    def add_message(self, session_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        添加消息到对话历史
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant/system/tool）
            content: 消息内容
            metadata: 额外元数据（可选）
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = deque()
            self.session_metadata[session_id] = {
                "created_at": datetime.now(),
                "last_active": datetime.now(),
                "message_count": 0
            }
            logger.debug(f"创建新会话: {session_id}")
        
        # 添加消息
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        }
        
        self.conversations[session_id].append(message)
        self.session_metadata[session_id]["last_active"] = datetime.now()
        self.session_metadata[session_id]["message_count"] += 1
        
        # 保持最近N轮对话（每轮包含user和assistant，所以*2）
        max_messages = self.max_turns * 2
        if len(self.conversations[session_id]) > max_messages:
            # 移除最旧的消息
            removed = len(self.conversations[session_id]) - max_messages
            for _ in range(removed):
                self.conversations[session_id].popleft()
            
            logger.debug(f"会话 {session_id} 超出最大轮数，移除 {removed} 条旧消息")
        
        logger.debug(f"添加消息到会话 {session_id}: {role} - {content[:50]}...")
    
    def get_history(self, session_id: str, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            last_n: 获取最近N条消息（可选）
        
        Returns:
            List[Dict]: 消息列表
        """
        if session_id not in self.conversations:
            logger.warning(f"会话不存在: {session_id}")
            return []
        
        messages = list(self.conversations[session_id])
        
        if last_n is not None:
            messages = messages[-last_n:]
        
        logger.debug(f"获取会话 {session_id} 历史，共 {len(messages)} 条消息")
        return messages
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的会话列表
        
        Args:
            limit: 返回的最大会话数
        
        Returns:
            List[Dict]: 会话信息列表
        """
        # 清理过期会话
        self._cleanup_expired_sessions()
        
        # 按最后活跃时间排序
        sorted_sessions = sorted(
            self.session_metadata.items(),
            key=lambda x: x[1]["last_active"],
            reverse=True
        )
        
        result = []
        for session_id, metadata in sorted_sessions[:limit]:
            message_count = len(self.conversations.get(session_id, []))
            result.append({
                "session_id": session_id,
                "message_count": message_count,
                "created_at": metadata["created_at"],
                "last_active": metadata["last_active"]
            })
        
        logger.info(f"获取最近 {len(result)} 个会话")
        return result
    
    def clear_session(self, session_id: str):
        """
        清理指定会话
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.conversations:
            del self.conversations[session_id]
            del self.session_metadata[session_id]
            logger.info(f"清理会话: {session_id}")
        else:
            logger.warning(f"尝试清理不存在的会话: {session_id}")
    
    def clear_all_sessions(self):
        """清理所有会话"""
        count = len(self.conversations)
        self.conversations.clear()
        self.session_metadata.clear()
        logger.info(f"清理所有会话，共 {count} 个")
    
    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        now = datetime.now()
        expired = []
        
        for session_id, metadata in self.session_metadata.items():
            age = now - metadata["last_active"]
            if age > timedelta(hours=self.max_age_hours):
                expired.append(session_id)
        
        for session_id in expired:
            self.clear_session(session_id)
        
        if expired:
            logger.info(f"清理 {len(expired)} 个过期会话")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        self._cleanup_expired_sessions()
        
        total_sessions = len(self.conversations)
        total_messages = sum(len(msgs) for msgs in self.conversations.values())
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "avg_messages_per_session": total_messages / total_sessions if total_sessions > 0 else 0,
            "max_turns": self.max_turns,
            "max_age_hours": self.max_age_hours
        }
