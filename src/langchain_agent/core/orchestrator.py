"""
Perfa - LangChain Agent Module

@file: core/orchestrator.py
@desc: Agent编排器
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
from typing import List, Dict, Any, Optional

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()
from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseLLM
from langchain_core.tools import BaseTool

# 本地模块导入
from langchain_agent.agents import ReActAgent
from langchain_agent.core.memory import ConversationMemory
from langchain_agent.core.error_handler import ErrorHandler
from langchain_agent.core.config import LLMConfig, MCPConfig, AgentConfig


class AgentOrchestrator:
    """
    Agent编排器
    
    负责协调不同Agent和工具，处理用户查询
    """
    
    def __init__(
        self,
        mcp_adapter,
        llm_config: Optional[LLMConfig] = None,
        agent_config: Optional[AgentConfig] = None,
        memory_max_turns: int = 10,
        memory_max_age_hours: int = 24
    ):
        """
        初始化Agent编排器
        
        Args:
            mcp_adapter: MCP工具适配器
            llm_config: LLM配置（可选）
            agent_config: Agent配置（可选）
            memory_max_turns: 记忆最大轮数
            memory_max_age_hours: 记忆最大存活时间（小时）
        """
        self.mcp_adapter = mcp_adapter
        self.llm_config = llm_config or LLMConfig()
        self.agent_config = agent_config or AgentConfig()
        
        # 初始化组件
        self.memory = ConversationMemory(max_turns=memory_max_turns, max_age_hours=memory_max_age_hours)
        self.error_handler = ErrorHandler(
            max_retries=self.agent_config.error_max_retries,
            retry_delay=self.agent_config.error_retry_delay
        )
        self.llm = self._create_llm()
        self.tools = self.mcp_adapter.list_tools()
        self.agent = ReActAgent(
            llm=self.llm,
            tools=self.tools,
            max_iterations=self.agent_config.max_iterations
        )
        
        logger.info(f"Agent编排器初始化完成，使用智谱AI GLM-5")
        logger.info(f"可用工具数: {len(self.tools)}")
    
    def _create_llm(self) -> BaseLLM:
        """
        创建LLM实例
        
        使用智谱AI GLM-5模型
        智谱AI的API兼容OpenAI格式，可以直接使用ChatOpenAI
        """
        if not self.llm_config.zhipu_api_key:
            raise ValueError("智谱AI API Key未配置，请在.env文件中设置ZHIPU_API_KEY")
        
        logger.info(f"创建智谱AI LLM，模型: {self.llm_config.zhipu_model}")
        
        # 使用LangChain的ChatOpenAI连接智谱AI
        # 智谱AI的API兼容OpenAI格式，只需设置base_url
        return ChatOpenAI(
            api_key=self.llm_config.zhipu_api_key,
            base_url=self.llm_config.zhipu_base_url,
            model=self.llm_config.zhipu_model,
            temperature=self.llm_config.zhipu_temperature,
            max_tokens=self.llm_config.zhipu_max_tokens
        )
    
    async def process_query(self, query: str, session_id: Optional[str] = None, mode: str = "auto") -> Dict[str, Any]:
        """
        处理用户查询
        
        Args:
            query: 用户查询
            session_id: 会话ID（可选）
            mode: 执行模式（目前只支持auto/react，未来可扩展其他模式）
        
        Returns:
            Dict: 处理结果
        """
        if not session_id:
            import uuid
            session_id = f"session_{uuid.uuid4().hex[:16]}"
        
        # mode 参数预留用于未来扩展（如 planning, chain-of-thought 等）
        if mode not in ["auto", "react"]:
            logger.warning(f"未知的执行模式 '{mode}'，使用默认模式 'auto'")
        
        logger.info(f"开始处理查询，会话ID: {session_id}")
        logger.info(f"用户查询: {query}")
        
        try:
            # 记录用户消息到记忆
            self.memory.add_message(session_id, "user", query)
            
            # 获取会话历史作为上下文传给Agent
            session_history = self.memory.get_history(session_id, last_n=10)
            
            # 调用Agent执行
            logger.info("调用ReAct Agent执行查询")
            response = await self.agent.run(
                query, 
                session_id=session_id,
                context={"session_history": session_history}
            )
            
            # 记录助手消息到记忆
            self.memory.add_message(session_id, "assistant", response.result)
            
            # 记录工具调用到记忆
            for tool_call in response.tool_calls:
                self.memory.add_message(
                    session_id,
                    "tool",
                    f"工具: {tool_call.tool_name}，结果: {str(tool_call.result)[:100]}...",
                    metadata={
                        "tool_name": tool_call.tool_name,
                        "arguments": tool_call.arguments,
                        "execution_time": tool_call.execution_time
                    }
                )
            
            logger.info(f"查询处理完成，耗时: {response.execution_time:.2f}秒，工具调用: {len(response.tool_calls)}次")
            
            return {
                "success": True,
                "session_id": session_id,
                "query": query,
                "result": response.result,
                "tool_calls": [
                    {
                        "tool_name": tc.tool_name,
                        "arguments": tc.arguments,
                        "result": tc.result,
                        "execution_time": tc.execution_time
                    }
                    for tc in response.tool_calls
                ],
                "execution_time": response.execution_time,
                "is_success": response.is_success,
                "thinking_process": response.thinking_process if hasattr(response, 'thinking_process') else None,
                "reasoning_time": response.reasoning_time if hasattr(response, 'reasoning_time') else 0
            }
            
        except Exception as e:
            error_msg = f"处理查询失败: {str(e)}"
            logger.error(error_msg)
            
            return {
                "success": False,
                "session_id": session_id,
                "query": query,
                "error": error_msg,
                "tool_calls": [],
                "execution_time": 0,
                "is_success": False
            }
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], max_retries: Optional[int] = None) -> Dict[str, Any]:
        """
        执行指定工具（带重试机制）
        
        Args:
            tool_name: 工具名称
            arguments: 工具参数
            max_retries: 最大重试次数（可选）
        
        Returns:
            Dict: 执行结果
        """
        if tool_name not in self.mcp_adapter.get_tool_names():
            error_msg = f"工具不存在: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        tool = self.mcp_adapter.get_tool(tool_name)
        if not tool:
            error_msg = f"获取工具失败: {tool_name}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # 使用错误处理器的重试机制
        result = await self.error_handler.retry_with_backoff(
            tool.ainvoke,
            arguments,
            tool_name=tool_name
        )
        
        return result
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """
        获取可用工具列表
        
        Returns:
            List[Dict]: 工具信息列表
        """
        tools = []
        for tool_name in self.mcp_adapter.get_tool_names():
            tool = self.mcp_adapter.get_tool(tool_name)
            if tool:
                tools.append({
                    "name": tool_name,
                    "description": tool.description or "无描述"
                })
        
        return tools
    
    def get_session_history(self, session_id: str, last_n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话ID
            last_n: 获取最近N条消息
        
        Returns:
            List[Dict]: 消息列表
        """
        return self.memory.get_history(session_id, last_n)
    
    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的会话列表
        
        Args:
            limit: 返回的最大会话数
        
        Returns:
            List[Dict]: 会话信息
        """
        return self.memory.get_recent_sessions(limit)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        memory_stats = self.memory.get_session_stats()
        error_stats = self.error_handler.get_overall_stats()
        
        return {
            "memory": memory_stats,
            "errors": error_stats,
            "tool_count": len(self.tools),
            "max_iterations": self.agent_config.max_iterations
        }
    
    def clear_session(self, session_id: str):
        """清理指定会话"""
        self.memory.clear_session(session_id)
        logger.info(f"清理会话: {session_id}")
    
    def clear_all_sessions(self):
        """清理所有会话"""
        self.memory.clear_all_sessions()
        logger.info("清理所有会话")
    
    def reset_error_stats(self, tool_name: Optional[str] = None):
        """
        重置错误统计
        
        Args:
            tool_name: 指定工具，None则重置所有
        """
        self.error_handler.reset_stats(tool_name)
        logger.info(f"重置错误统计: {tool_name or 'all'}")
