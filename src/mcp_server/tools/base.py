"""Tool 基类"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from mcp.types import Tool


class BaseTool(ABC):
    """MCP Tool 基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """参数 Schema"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        pass
    
    def to_mcp_tool(self) -> Tool:
        """转换为 MCP Tool 定义"""
        return Tool(name=self.name, description=self.description, inputSchema=self.input_schema)
