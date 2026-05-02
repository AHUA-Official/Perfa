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
        
        # Agent 生命周期管理工具
        from tools.agent_tools import (
            DeployAgentTool, CheckAgentStatusTool, GetAgentLogsTool,
            ConfigureAgentTool, UninstallAgentTool
        )
        
        self.register_tool(DeployAgentTool(self.db))
        self.register_tool(CheckAgentStatusTool(self.db))
        self.register_tool(GetAgentLogsTool(self.db))
        self.register_tool(ConfigureAgentTool(self.db))
        self.register_tool(UninstallAgentTool(self.db))
        
        # 压测工具管理
        from tools.tool_tools import (
            InstallToolTool, UninstallToolTool, ListToolsTool, VerifyToolTool
        )
        
        self.register_tool(InstallToolTool(self.db))
        self.register_tool(UninstallToolTool(self.db))
        self.register_tool(ListToolsTool(self.db))
        self.register_tool(VerifyToolTool(self.db))
        
        # Benchmark 压测管理
        from tools.benchmark_tools import (
            RunBenchmarkTool, GetBenchmarkStatusTool, CancelBenchmarkTool,
            GetBenchmarkResultTool, ListBenchmarkHistoryTool
        )
        
        self.register_tool(RunBenchmarkTool(self.db))
        self.register_tool(GetBenchmarkStatusTool(self.db))
        self.register_tool(CancelBenchmarkTool(self.db))
        self.register_tool(GetBenchmarkResultTool(self.db))
        self.register_tool(ListBenchmarkHistoryTool(self.db))
        
        # 智能分析
        from tools.report_tools import GenerateReportTool
        
        self.register_tool(GenerateReportTool(self.db))
    
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
        
        # OTel: 注入 Starlette 自动 Instrumentation
        try:
            from langchain_agent.observability.instrument_server import (
                setup_server_tracing, instrument_starlette_app
            )
            setup_server_tracing(service_name="perfa-mcp-server")
            instrument_starlette_app(app)
        except ImportError:
            logger.warning("⚠️ OTel instrumentation 不可用（依赖缺失），跳过")
        except Exception as e:
            logger.warning(f"⚠️ OTel instrumentation 失败: {e}")
        
        # 启动服务器
        import uvicorn
        logger.info(f"MCP Server starting on {self.config.host}:{self.config.port}")
        uvicorn.run(app, host=self.config.host, port=self.config.port)
