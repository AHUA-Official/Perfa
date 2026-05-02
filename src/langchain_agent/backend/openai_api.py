"""
OpenAI Compatible API Implementation
"""

import json
import uuid
from typing import Optional, AsyncGenerator, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from langchain_agent.core.logger import get_logger
logger = get_logger()

from .schemas import (
    ChatRequest, ChatResponse, ChatChoice, ChatMessage,
    ModelInfo, ModelList,
    ServerInfo, ServerListResponse,
    WorkflowStatusResponse, WorkflowNodeStatus,
    ReportInfo, ReportListResponse, ReportDetail
)

router = APIRouter()

# Global Orchestrator instance
_orchestrator = None


async def get_orchestrator():
    """Get or create Orchestrator singleton"""
    global _orchestrator
    
    if _orchestrator is None:
        from langchain_agent.core.orchestrator import AgentOrchestrator
        from langchain_agent.tools.mcp_adapter import MCPToolAdapter
        from langchain_agent.core.config import ConfigManager
        
        logger.info("Initializing Orchestrator...")
        
        # Load config
        config = ConfigManager()
        
        # Create MCP adapter
        mcp_adapter = MCPToolAdapter(config.mcp.sse_url, config.mcp.api_key)
        await mcp_adapter.connect()
        
        # Create Orchestrator
        _orchestrator = AgentOrchestrator(
            mcp_adapter=mcp_adapter,
            memory_max_turns=config.agent.memory_max_turns,
            memory_max_age_hours=config.agent.memory_max_age_hours
        )
        
        logger.info("Orchestrator initialized successfully")
    
    return _orchestrator


@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """
    Chat completion endpoint (OpenAI compatible)
    
    Supports both sync and streaming (SSE) output
    """
    try:
        # Get user query from last message
        user_query = request.messages[-1].content if request.messages else ""
        
        if not user_query:
            raise HTTPException(status_code=400, detail="No user message provided")
        
        logger.info(f"Received chat request: {user_query[:100]}...")
        
        # Streaming mode
        if request.stream:
            return StreamingResponse(
                stream_chat_response(user_query),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        # Sync mode
        orchestrator = await get_orchestrator()
        result = await orchestrator.process_query(user_query)
        
        # Format response
        content = format_response_markdown(result)
        
        return ChatResponse(
            choices=[ChatChoice(
                message=ChatMessage(role="assistant", content=content),
                finish_reason="stop"
            )]
        )
    
    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(query: str) -> AsyncGenerator[str, None]:
    """
    Stream chat response using SSE (Server-Sent Events)
    
    真流式：边生成边推送，来一个字展示一个字
    """
    import asyncio
    
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    # 获取当前 trace_id
    trace_id_hex = None
    try:
        from opentelemetry import trace
        current_span = trace.get_current_span()
        if current_span and current_span.is_recording():
            ctx = current_span.get_span_context()
            trace_id_hex = format(ctx.trace_id, '032x')
    except Exception:
        pass
    
    try:
        orchestrator = await get_orchestrator()
        
        # Stream header with trace_id
        header_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"role": "assistant"}, "index": 0}]
        }
        if trace_id_hex:
            header_data["trace_id"] = trace_id_hex
            header_data["jaeger_url"] = f"/api/jaeger/trace/{trace_id_hex}"
        yield format_sse(header_data)
        
        # 先推一个"正在思考"提示
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": "⏳ 正在分析您的请求...\n\n"}, "index": 0}]
        })
        
        # Process query (后台执行)
        result = await orchestrator.process_query(query)
        
        # 如果之前没拿到 trace_id，尝试从结果中获取
        if not trace_id_hex and result.get("trace_id"):
            trace_id_hex = result.get("trace_id")
        
        # 清除"正在思考"提示 → 用 Markdown 分隔覆盖
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": "\r\r"}, "index": 0}]
        })
        
        # 逐字符流式推送内容（打字机效果）
        async def stream_text(text: str, chunk_size: int = 3):
            """将文本按小段推送，模拟打字机效果"""
            i = 0
            while i < len(text):
                chunk = text[i:i + chunk_size]
                yield format_sse({
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": chunk}, "index": 0}]
                })
                i += chunk_size
                # 小段间极短延迟，让浏览器能渲染
                if i % 60 == 0:
                    await asyncio.sleep(0.01)
        
        # Stream thinking process
        thinking = result.get("thinking_process", "")
        if thinking:
            async for chunk in stream_text("## 💭 思考过程\n\n"):
                yield chunk
            async for chunk in stream_text(thinking):
                yield chunk
            async for chunk in stream_text("\n\n---\n\n"):
                yield chunk
        
        # Stream result
        async for chunk in stream_text("## ✅ 执行结果\n\n"):
            yield chunk
        content = result.get("result", "")
        async for chunk in stream_text(content):
            yield chunk
        
        # Stream performance stats + trace link
        execution_time = result.get("execution_time", 0)
        tool_calls = result.get("tool_calls", [])
        
        stats_content = f"\n\n---\n\n⏱️ **性能统计**\n- 总耗时：{execution_time:.2f}秒\n- 工具调用：{len(tool_calls)}次\n"
        if trace_id_hex:
            stats_content += f"- 🔗 [查看 Trace 链路](/api/jaeger/trace/{trace_id_hex})\n"
        
        async for chunk in stream_text(stats_content):
            yield chunk
        
        # Stream finish with metadata
        finish_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
        }
        if trace_id_hex:
            finish_data["trace_id"] = trace_id_hex
            finish_data["jaeger_url"] = f"/api/jaeger/trace/{trace_id_hex}"
        
        if result.get("node_statuses"):
            finish_data["workflow"] = {
                "scenario": result.get("scenario", ""),
                "node_statuses": result.get("node_statuses", {}),
                "completed_nodes": result.get("completed_nodes", []),
                "current_node": result.get("current_node"),
            }
        
        yield format_sse(finish_data)
        
        # End stream
        yield "data: [DONE]\n\n"
    
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{
                "delta": {"content": f"\n\n❌ 错误：{str(e)}"},
                "index": 0
            }]
        })
        yield "data: [DONE]\n\n"


def format_sse(data: dict) -> str:
    """Format data as SSE"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def format_response_markdown(result: dict) -> str:
    """Format response as Markdown"""
    parts = []
    
    # Thinking process
    thinking = result.get("thinking_process")
    if thinking:
        parts.append("## 💭 思考过程\n\n")
        parts.append(thinking)
        parts.append("\n\n---\n\n")
    
    # Result
    parts.append("## ✅ 执行结果\n\n")
    parts.append(result.get("result", ""))
    
    # Performance stats
    execution_time = result.get("execution_time", 0)
    tool_calls = result.get("tool_calls", [])
    
    parts.append(f"\n\n---\n\n⏱️ **性能统计**\n")
    parts.append(f"- 总耗时：{execution_time:.2f}秒\n")
    parts.append(f"- 工具调用：{len(tool_calls)}次\n")
    
    return "".join(parts)


@router.get("/models", response_model=ModelList)
async def list_models():
    """List available models"""
    return ModelList(
        data=[
            ModelInfo(id="perfa-agent"),
            ModelInfo(id="perfa-react"),
        ]
    )


# ===== Extended API Endpoints =====


@router.get("/servers", response_model=ServerListResponse)
async def list_servers():
    """获取已注册的服务器列表"""
    try:
        orchestrator = await get_orchestrator()
        # 通过 MCP 工具获取服务器列表
        tools_dict = orchestrator.tools_dict
        list_servers_tool = tools_dict.get("list_servers")

        if list_servers_tool:
            result = await list_servers_tool.ainvoke({})
            # 解析 MCP 工具返回
            if isinstance(result, str):
                import json as _json
                try:
                    result = _json.loads(result)
                except _json.JSONDecodeError:
                    result = {"servers": []}

            # 获取 check_agent_status 工具用于实时状态查询
            check_status_tool = tools_dict.get("check_agent_status")

            servers = []
            for s in result.get("servers", result if isinstance(result, list) else []):
                if isinstance(s, dict):
                    # 尝试获取实时状态
                    server_id = s.get("server_id", s.get("id", ""))
                    status = "unknown"
                    if check_status_tool and server_id:
                        try:
                            status_result = await check_status_tool.ainvoke({"server_id": server_id})
                            if isinstance(status_result, str):
                                import json as _json2
                                try:
                                    status_result = _json2.loads(status_result)
                                except _json2.JSONDecodeError:
                                    status_result = {}
                            if isinstance(status_result, dict):
                                agent_st = status_result.get("agent_status", "")
                                if agent_st in ("online", "running"):
                                    status = "online"
                                elif agent_st in ("offline", "stopped", "error"):
                                    status = "offline"
                        except Exception:
                            pass  # 查询失败则回退到静态状态

                    # 回退: 从 list_servers 返回的 agent_status 字段推断
                    if status == "unknown":
                        agent_status = s.get("agent_status", "")
                        if agent_status in ("online", "running", "deployed"):
                            status = "online"
                        elif agent_status in ("offline", "stopped", "error"):
                            status = "offline"

                    servers.append(ServerInfo(
                        server_id=server_id,
                        ip=s.get("ip", s.get("host", "")),
                        alias=s.get("alias", s.get("name")),
                        status=status,
                        tags=s.get("tags", []),
                        hardware=s.get("hardware", s.get("system_info")),
                    ))

            return ServerListResponse(servers=servers)

        return ServerListResponse(servers=[])
    except Exception as e:
        logger.error(f"List servers error: {e}")
        return ServerListResponse(servers=[])


class RegisterServerRequest(BaseModel):
    """注册服务器请求"""
    ip: str = Field(..., description="服务器 IP")
    port: int = Field(22, description="SSH 端口")
    ssh_user: str = Field(..., description="SSH 用户名")
    ssh_password: Optional[str] = Field(None, description="SSH 密码")
    ssh_key_path: Optional[str] = Field(None, description="SSH 密钥路径")
    alias: Optional[str] = Field(None, description="服务器别名")
    tags: List[str] = Field(default_factory=list, description="标签")


@router.post("/servers/register")
async def register_server(req: RegisterServerRequest):
    """注册新服务器（通过 MCP 工具）"""
    try:
        orchestrator = await get_orchestrator()
        tools_dict = orchestrator.tools_dict
        register_tool = tools_dict.get("register_server")

        if not register_tool:
            raise HTTPException(status_code=501, detail="register_server 工具不可用")

        # 构造 MCP 工具参数（严格过滤 None 值，MCP Server 不接受 null）
        args: dict = {"ip": req.ip, "ssh_user": req.ssh_user}
        if req.port != 22:
            args["port"] = req.port
        if req.ssh_password:
            args["ssh_password"] = req.ssh_password
        if req.ssh_key_path:
            args["ssh_key_path"] = req.ssh_key_path
        if req.alias:
            args["alias"] = req.alias
        if req.tags:
            args["tags"] = req.tags

        # 调用 MCP 工具（MCPAdapter 已自动过滤 None 参数）
        result = await register_tool.ainvoke(args)

        # 解析结果
        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                result = {"raw": result}

        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"]}

        return {"success": True, "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register server error: {e}")
        return {"success": False, "error": str(e)}


@router.delete("/servers/{server_id}")
async def remove_server(server_id: str):
    """移除已注册的服务器"""
    try:
        orchestrator = await get_orchestrator()
        tools_dict = orchestrator.tools_dict
        remove_tool = tools_dict.get("remove_server")

        if not remove_tool:
            raise HTTPException(status_code=501, detail="remove_server 工具不可用")

        result = await remove_tool.ainvoke({"server_id": server_id})

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                result = {"raw": result}

        if isinstance(result, dict) and result.get("error"):
            return {"success": False, "error": result["error"]}

        return {"success": True, "data": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remove server error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/workflows/status/{session_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(session_id: str):
    """获取工作流执行状态"""
    try:
        orchestrator = await get_orchestrator()
        # 从内存中获取该 session 的最后一条助手消息
        history = orchestrator.memory.get_history(session_id, last_n=5)
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                metadata = msg.get("metadata", {})
                if metadata and metadata.get("scenario"):
                    node_statuses = metadata.get("node_statuses", {})
                    completed_nodes = metadata.get("completed_nodes", [])
                    nodes = [
                        WorkflowNodeStatus(
                            name=n,
                            status=s,
                            display_name=n.replace("_", " ").title(),
                        )
                        for n, s in node_statuses.items()
                    ]
                    total = len(node_statuses) if node_statuses else 1
                    done = len(completed_nodes)
                    return WorkflowStatusResponse(
                        scenario=metadata["scenario"],
                        session_id=session_id,
                        nodes=nodes,
                        current_node=metadata.get("current_node"),
                        completed_nodes=completed_nodes,
                        progress=done / total if total > 0 else 0,
                    )

        return WorkflowStatusResponse(
            scenario="unknown",
            session_id=session_id,
            nodes=[],
            progress=0,
        )
    except Exception as e:
        logger.error(f"Workflow status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports", response_model=ReportListResponse)
async def list_reports():
    """获取测试报告列表"""
    try:
        orchestrator = await get_orchestrator()
        tools_dict = orchestrator.tools_dict
        list_reports_tool = tools_dict.get("list_benchmark_history")

        if list_reports_tool:
            result = await list_reports_tool.ainvoke({})
            if isinstance(result, str):
                import json as _json
                try:
                    result = _json.loads(result)
                except _json.JSONDecodeError:
                    result = []

            reports = []
            for r in (result if isinstance(result, list) else result.get("reports", [])):
                if isinstance(r, dict):
                    reports.append(ReportInfo(
                        id=r.get("task_id", r.get("id", "")),
                        type=r.get("type", r.get("benchmark_type", "unknown")),
                        server_id=r.get("server_id", r.get("server", "")),
                        created_at=r.get("created_at", r.get("start_time", "")),
                        status=r.get("status", "completed"),
                        summary=r.get("summary"),
                    ))
            return ReportListResponse(reports=reports)

        return ReportListResponse(reports=[])
    except Exception as e:
        logger.error(f"List reports error: {e}")
        return ReportListResponse(reports=[])


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    """获取报告详情"""
    try:
        orchestrator = await get_orchestrator()
        tools_dict = orchestrator.tools_dict
        get_result_tool = tools_dict.get("get_benchmark_result")

        if get_result_tool:
            result = await get_result_tool.ainvoke({"task_id": report_id})
            if isinstance(result, str):
                import json as _json
                try:
                    result = _json.loads(result)
                except _json.JSONDecodeError:
                    pass

            if isinstance(result, dict):
                return ReportDetail(
                    id=report_id,
                    type=result.get("type", result.get("benchmark_type", "unknown")),
                    server_id=result.get("server_id", result.get("server", "")),
                    created_at=result.get("created_at", result.get("start_time", "")),
                    status=result.get("status", "completed"),
                    summary=result.get("summary"),
                    content=result.get("result", result.get("metrics")),
                    charts=result.get("charts"),
                )

        raise HTTPException(status_code=404, detail="Report not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
