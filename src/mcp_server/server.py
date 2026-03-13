"""MCP Server 核心实现"""
import logging
from typing import Dict, Any, List
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from config import Config
from storage import Database
from tools.base import BaseTool


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Server"""
    
    def __init__(self, config: Config):
        self.config = config
        self.db = Database(config.db_path)
        self.server = Server("mcp-perfa")
        self.tools: Dict[str, BaseTool] = {}
        
        # 注册工具
        self._register_tools()
    
    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Tool registered: {tool.name}")
    
    def _register_tools(self):
        """注册所有工具"""
        # 服务器管理工具
        from tools.server_tools import (
            RegisterServerTool, ListServersTool, RemoveServerTool,
            GetServerInfoTool, UpdateServerInfoTool
        )
        
        self.register_tool(RegisterServerTool(self.db))
        self.register_tool(ListServersTool(self.db))
        self.register_tool(RemoveServerTool(self.db))
        self.register_tool(GetServerInfoTool(self.db))
        self.register_tool(UpdateServerInfoTool(self.db))
        
        # TODO: 注册其他工具
        # Agent 管理工具
        # 工具管理工具
        # Benchmark 管理工具
        # 智能分析工具
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有工具"""
        return [tool.to_mcp_tool() for tool in self.tools.values()]
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用工具"""
        if name not in self.tools:
            return {
                "success": False,
                "error": f"Tool {name} not found"
            }
        
        tool = self.tools[name]
        
        try:
            result = tool.execute(**arguments)
            return result
        except Exception as e:
            logger.error(f"Tool {name} failed: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def run(self):
        """启动服务器"""
        from starlette.applications import Starlette
        from starlette.routing import Route, Mount
        from starlette.responses import JSONResponse, Response
        
        # 创建 SSE 传输
        sse = SseServerTransport("/messages/")
        
        # 注册 MCP 处理器（必须在 run 之前注册）
        @self.server.list_tools()
        async def list_tools():
            return self.list_tools()
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self.call_tool(name, arguments)
        
        async def handle_sse(request):
            """处理 SSE 连接"""
            # 验证 API Key
            api_key = request.query_params.get("api_key") or request.headers.get("Authorization", "").replace("Bearer ", "")
            
            if self.config.api_key and api_key != self.config.api_key:
                return JSONResponse({"error": "Unauthorized"}, status_code=401)
            
            
            # 正确的 SSE 连接处理方式
            async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self.server.run(
                    streams[0], streams[1], self.server.create_initialization_options()
                )
            # 返回空响应避免 NoneType 错误
            return Response()
        
        # 创建 Starlette 应用
        app = Starlette(
            routes=[
                Route("/sse", endpoint=handle_sse),
                Mount("/messages/", app=sse.handle_post_message),
            ]
        )
        
        # 启动服务器
        import uvicorn
        logger.info(f"MCP Server starting on {self.config.host}:{self.config.port}")
        uvicorn.run(app, host=self.config.host, port=self.config.port)
