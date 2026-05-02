"""
Perfa - LangChain Agent Module

@file: core/config.py
@desc: 配置管理
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

# 第三方库导入
from langchain_agent.core.logger import get_logger
logger = get_logger()
from pydantic_settings import BaseSettings


class LLMConfig(BaseSettings):
    """
    LLM配置
    
    支持智谱AI GLM系列模型
    智谱AI的API兼容OpenAI格式，可以直接使用LangChain的ChatOpenAI
    """
    
    # 智谱AI配置
    zhipu_api_key: Optional[str] = field(default_factory=lambda: os.getenv("ZHIPU_API_KEY"))
    zhipu_model: str = field(default_factory=lambda: os.getenv("ZHIPU_MODEL", "glm-5"))
    zhipu_base_url: str = field(default_factory=lambda: os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))
    zhipu_temperature: float = field(default_factory=lambda: float(os.getenv("ZHIPU_TEMPERATURE", "0.1")))
    zhipu_max_tokens: int = field(default_factory=lambda: int(os.getenv("ZHIPU_MAX_TOKENS", "4096")))
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 忽略 .env 中非本类的变量
    
    def __post_init__(self):
        if self.zhipu_api_key:
            logger.info(f"智谱AI配置初始化完成，模型: {self.zhipu_model}")
            logger.info(f"API地址: {self.zhipu_base_url}")
        else:
            logger.warning("智谱AI API Key未配置，请在.env文件中设置ZHIPU_API_KEY")


@dataclass
class MCPConfig:
    """
    MCP配置
    
    MCP Server使用SSE协议
    """
    
    # MCP Server地址
    server_url: str = field(default_factory=lambda: os.getenv("MCP_SERVER_URL", "http://localhost:9000"))
    
    # SSE端点
    sse_endpoint: str = field(default_factory=lambda: os.getenv("MCP_SSE_ENDPOINT", "/sse"))
    
    # 超时设置
    connect_timeout: float = field(default_factory=lambda: float(os.getenv("MCP_CONNECT_TIMEOUT", "30.0")))
    read_timeout: float = field(default_factory=lambda: float(os.getenv("MCP_READ_TIMEOUT", "300.0")))
    
    # API Key（如果MCP Server需要认证）
    api_key: Optional[str] = field(default_factory=lambda: os.getenv("MCP_API_KEY"))
    
    # 重试设置
    max_retries: int = field(default_factory=lambda: int(os.getenv("MCP_MAX_RETRIES", "3")))
    retry_delay: float = field(default_factory=lambda: float(os.getenv("MCP_RETRY_DELAY", "1.0")))
    
    @property
    def sse_url(self) -> str:
        """获取完整的SSE URL（包含API key）"""
        base_url = self.server_url.rstrip("/")
        endpoint = self.sse_endpoint if self.sse_endpoint.startswith("/") else f"/{self.sse_endpoint}"
        
        # 如果有 API key，添加到 URL 中
        if self.api_key:
            return f"{base_url}{endpoint}?api_key={self.api_key}"
        else:
            return f"{base_url}{endpoint}"
    
    def __post_init__(self):
        logger.info(f"MCP配置初始化完成，Server地址: {self.server_url}")
        logger.info(f"SSE端点: {self.sse_endpoint}")
        logger.info(f"连接超时: {self.connect_timeout}秒，读取超时: {self.read_timeout}秒")


@dataclass
class ChromaConfig:
    """
    ChromaDB配置
    
    用于存储历史查询和测试结果
    
    注意：此配置为未来功能预留，当前版本暂未使用
    预计用于：
    - 历史测试结果持久化存储
    - 相似查询智能推荐
    - 测试结果向量检索
    """
    
    # ChromaDB地址
    host: str = field(default_factory=lambda: os.getenv("CHROMADB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("CHROMADB_PORT", "8001")))
    
    # 集合名称
    collection_name: str = field(default_factory=lambda: os.getenv("CHROMADB_COLLECTION", "perfa_history"))
    
    # 持久化设置
    persist_directory: Optional[str] = field(default_factory=lambda: os.getenv("CHROMADB_PERSIST_DIR"))
    
    # 相似度搜索参数
    search_top_k: int = field(default_factory=lambda: int(os.getenv("CHROMADB_SEARCH_TOP_K", "5")))
    search_score_threshold: float = field(default_factory=lambda: float(os.getenv("CHROMADB_SEARCH_THRESHOLD", "0.7")))
    
    # Embedding模型
    embedding_model: str = field(default_factory=lambda: os.getenv("CHROMADB_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
    
    @property
    def http_url(self) -> str:
        """获取HTTP URL"""
        return f"http://{self.host}:{self.port}"
    
    def __post_init__(self):
        logger.info(f"ChromaDB配置初始化完成，地址: {self.http_url}")
        logger.info(f"集合名称: {self.collection_name}")
        logger.info(f"Embedding模型: {self.embedding_model}")


@dataclass
class AgentConfig:
    """
    Agent配置
    """
    
    # 最大迭代次数
    max_iterations: int = field(default_factory=lambda: int(os.getenv("AGENT_MAX_ITERATIONS", "10")))
    
    # 超时设置（秒）
    execution_timeout: float = field(default_factory=lambda: float(os.getenv("AGENT_TIMEOUT", "300.0")))
    
    # 记忆设置
    memory_max_turns: int = field(default_factory=lambda: int(os.getenv("AGENT_MEMORY_MAX_TURNS", "10")))
    memory_max_age_hours: int = field(default_factory=lambda: int(os.getenv("AGENT_MEMORY_MAX_AGE", "24")))
    
    # 错误处理
    error_max_retries: int = field(default_factory=lambda: int(os.getenv("AGENT_ERROR_MAX_RETRIES", "3")))
    error_retry_delay: float = field(default_factory=lambda: float(os.getenv("AGENT_RETRY_DELAY", "1.0")))
    
    # 日志级别
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_file: Optional[str] = field(default_factory=lambda: os.getenv("LOG_FILE"))
    
    def __post_init__(self):
        logger.info(f"Agent配置初始化完成")
        logger.info(f"最大迭代次数: {self.max_iterations}")
        logger.info(f"执行超时: {self.execution_timeout}秒")
        logger.info(f"日志级别: {self.log_level}")


class ConfigManager:
    """
    配置管理器
    
    统一管理所有配置
    """
    
    def __init__(self):
        self.llm = LLMConfig()
        self.mcp = MCPConfig()
        self.chroma = ChromaConfig()
        self.agent = AgentConfig()
        
        logger.info("配置管理器初始化完成")
    
    def get_all_configs(self) -> Dict[str, Any]:
        """获取所有配置"""
        return {
            "llm": self.llm.__dict__,
            "mcp": self.mcp.__dict__,
            "chroma": self.chroma.__dict__,
            "agent": self.agent.__dict__
        }
    
    def validate_configs(self) -> Dict[str, List[str]]:
        """
        验证配置
        
        Returns:
            Dict: 包含警告和错误信息
        """
        warnings = []
        errors = []
        
        # 验证智谱AI配置
        if not self.llm.zhipu_api_key:
            errors.append("智谱AI API Key未配置，请在.env文件中设置ZHIPU_API_KEY")
        
        # 验证MCP配置
        if not self.mcp.server_url:
            errors.append("MCP Server URL未配置")
        
        # 验证ChromaDB配置
        if not self.chroma.host or not self.chroma.port:
            warnings.append("ChromaDB配置不完整")
        
        # 验证Agent配置
        if self.agent.max_iterations < 1:
            errors.append("最大迭代次数必须大于0")
        
        if errors:
            logger.error(f"配置验证发现 {len(errors)} 个错误")
        if warnings:
            logger.warning(f"配置验证发现 {len(warnings)} 个警告")
        
        return {"warnings": warnings, "errors": errors}
