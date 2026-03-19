"""
Perfa 端口配置模块

统一管理所有服务的端口配置
"""

import os
from dataclasses import dataclass


@dataclass
class PortConfig:
    """端口配置"""
    
    # Node Agent 端口
    NODE_AGENT_API_PORT: int = 8080
    NODE_AGENT_METRICS_PORT: int = 8000
    
    # MCP Server 端口
    MCP_PORT: int = 9000
    
    # LangChain Agent 端口
    LANGCHAIN_API_PORT: int = 10000
    
    # 数据库端口
    CHROMADB_PORT: int = 8001
    
    # Web UI 端口
    WEBUI_PORT: int = 3001
    
    # 可视化端口
    GRAFANA_PORT: int = 3000
    VICTORIAMETRICS_PORT: int = 8428
    
    @classmethod
    def from_env(cls) -> 'PortConfig':
        """从环境变量加载端口配置"""
        return cls(
            NODE_AGENT_API_PORT=int(os.getenv('NODE_AGENT_API_PORT', 8080)),
            NODE_AGENT_METRICS_PORT=int(os.getenv('NODE_AGENT_METRICS_PORT', 8000)),
            MCP_PORT=int(os.getenv('MCP_PORT', 9000)),
            LANGCHAIN_API_PORT=int(os.getenv('LANGCHAIN_API_PORT', 10000)),
            CHROMADB_PORT=int(os.getenv('CHROMADB_PORT', 8001)),
            WEBUI_PORT=int(os.getenv('WEBUI_PORT', 3001)),
            GRAFANA_PORT=int(os.getenv('GRAFANA_PORT', 3000)),
            VICTORIAMETRICS_PORT=int(os.getenv('VICTORIAMETRICS_PORT', 8428)),
        )
    
    def get_mcp_sse_url(self) -> str:
        """获取 MCP Server SSE URL"""
        return f"http://localhost:{self.MCP_PORT}/sse"
    
    def get_langchain_api_url(self) -> str:
        """获取 LangChain Agent API URL"""
        return f"http://localhost:{self.LANGCHAIN_API_PORT}"
    
    def get_webui_url(self) -> str:
        """获取 Web UI URL"""
        return f"http://localhost:{self.WEBUI_PORT}"


# 全局端口配置实例
port_config = PortConfig.from_env()
