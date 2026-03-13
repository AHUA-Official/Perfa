"""配置管理"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """MCP Server 配置"""
    
    # MCP Server
    host: str = "0.0.0.0"
    port: int = 9000
    
    # 认证
    api_key: str = ""
    
    # 数据库
    db_path: str = "/var/lib/mcp/mcp.db"
    
    # Agent
    agent_timeout: int = 30  # 秒
    
    # 回调
    callback_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """从环境变量加载配置"""
        return cls(
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=int(os.getenv("MCP_PORT", "9000")),
            api_key=os.getenv("MCP_API_KEY", ""),
            db_path=os.getenv("MCP_DB_PATH", "/var/lib/mcp/mcp.db"),
            agent_timeout=int(os.getenv("MCP_AGENT_TIMEOUT", "30")),
            callback_enabled=os.getenv("MCP_CALLBACK_ENABLED", "true").lower() == "true",
        )
