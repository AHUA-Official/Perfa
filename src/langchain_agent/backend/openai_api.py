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
    ReportInfo, ReportListResponse, ReportDetail,
    SessionSummary, SessionListResponse, SessionDetail, SessionMessage
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
        session_id = request.session_id
        conversation_id = request.conversation_id or session_id
        
        # Streaming mode
        if request.stream:
            return StreamingResponse(
                stream_chat_response(
                    user_query,
                    session_id=session_id,
                    conversation_id=conversation_id,
                    server_id=request.server_id,
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                }
            )
        
        # Sync mode
        orchestrator = await get_orchestrator()
        result = await orchestrator.process_query(
            user_query,
            session_id=session_id,
            conversation_id=conversation_id,
            server_id=request.server_id,
        )

        if not result.get("success", result.get("is_success", False)):
            raise HTTPException(
                status_code=502,
                detail=result.get("error") or "Query processing failed"
            )
        
        # Format response
        content = format_response_markdown(result)
        
        return ChatResponse(
            choices=[ChatChoice(
                message=ChatMessage(role="assistant", content=content),
                finish_reason="stop"
            )]
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completion error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(
    query: str,
    session_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    server_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream chat response using SSE (Server-Sent Events)
    
    双通道架构：
    - delta.content: 只承载用户最终看到的回答正文
    - metadata: 承载思考、工具调用、工作流进度、统计等过程事件
    """
    import asyncio
    import re
    
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
    
    def push_delta(text: str) -> str:
        """推送正文 chunk — 只承载最终答案文本"""
        return format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": text}, "index": 0}]
        })
    
    def push_meta(event_type: str, payload: dict) -> str:
        """推送元事件 — 不污染正文，供前端过程面板消费"""
        data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {}, "index": 0}],
            "metadata": {"type": event_type, **payload},
        }
        return format_sse(data)
    
    def push_finish(trace_id: str | None, jaeger_url: str | None,
                     workflow: dict | None = None) -> str:
        """推送结束 chunk"""
        finish_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
        }
        if trace_id:
            finish_data["trace_id"] = trace_id
            finish_data["jaeger_url"] = jaeger_url
        if workflow:
            finish_data["workflow"] = workflow
        return format_sse(finish_data)
    
    def _summarize_tool_result(result: dict) -> str:
        """精简工具结果为一句可读摘要"""
        if not result.get("success", True):
            return f"失败: {result.get('error', '未知错误')}"
        data = result.get("data", result)
        if isinstance(data, dict):
            if "task_id" in data:
                return f"task_id: {data['task_id']}"
            if "servers" in data:
                return f"找到 {len(data.get('servers', []))} 台服务器"
            if "status" in data:
                return f"状态: {data['status']}"
            preview = json.dumps(data, ensure_ascii=False)[:200]
            return preview
        return str(data)[:150]
    
    try:
        orchestrator = await get_orchestrator()
        
        # Stream header with trace_id
        header_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"role": "assistant"}, "index": 0}]
        }
        if session_id:
            header_data["session_id"] = session_id
        if conversation_id:
            header_data["conversation_id"] = conversation_id
        if trace_id_hex:
            header_data["trace_id"] = trace_id_hex
            header_data["jaeger_url"] = f"/api/jaeger/trace/{trace_id_hex}"
        yield format_sse(header_data)
        
        try:
            async for event in orchestrator.process_query_stream(
                query,
                session_id=session_id,
                conversation_id=conversation_id,
                server_id=server_id,
            ):
                event_type = event.get("type")
                if event.get("session_id"):
                    session_id = event.get("session_id")
                if event.get("conversation_id"):
                    conversation_id = event.get("conversation_id")
                
                # ---- 过程事件 → metadata 通道 ----
                if event_type == "thinking_start":
                    yield push_meta("thinking_start", {
                        "iteration": event.get("iteration", 1),
                    })
                
                elif event_type == "thinking_result":
                    iteration = event.get("iteration", 1)
                    reasoning = event.get("reasoning", "")
                    decision = event.get("decision", {})
                    
                    yield push_meta("thinking_result", {
                        "iteration": iteration,
                        "reasoning_preview": reasoning[:300] if reasoning else "",
                        "is_final": decision.get("is_final", False),
                        "tool_name": decision.get("tool_name"),
                        "tool_args": decision.get("tool_args"),
                    })
                
                elif event_type == "tool_result":
                    tool_name = event.get("tool_name", "")
                    tool_result = event.get("result", {})
                    exec_time = event.get("execution_time", 0)
                    success = tool_result.get("success", True)
                    
                    yield push_meta("tool_result", {
                        "tool_name": tool_name,
                        "success": success,
                        "summary": _summarize_tool_result(tool_result),
                        "execution_time": round(exec_time, 2),
                    })
                
                elif event_type == "workflow_progress":
                    yield push_meta("workflow_progress", {
                        "current_node": event.get("current_node", ""),
                        "status": event.get("status", ""),
                        "scenario": event.get("scenario", ""),
                    })
                
                # ---- 答案流 → delta.content 通道 ----
                elif event_type == "answer_start":
                    # 答案即将开始，前端可做 UI 切换
                    yield push_meta("answer_start", {})
                
                elif event_type == "answer_delta":
                    # 真正的答案文本增量
                    yield push_delta(event.get("content", ""))
                
                elif event_type == "answer_done":
                    yield push_meta("answer_done", {})
                
                # ---- 完成 ----
                elif event_type == "done":
                    result = event.get("result", {})
                    
                    if not trace_id_hex and result.get("trace_id"):
                        trace_id_hex = result.get("trace_id")
                    if result.get("session_id"):
                        session_id = result.get("session_id")
                    if result.get("conversation_id"):
                        conversation_id = result.get("conversation_id")
                    
                    # 性能统计 → metadata（不进正文）
                    execution_time = result.get("execution_time", 0)
                    tool_calls = result.get("tool_calls", [])
                    mode = result.get("mode", "react")
                    
                    yield push_meta("summary", {
                        "mode": mode,
                        "execution_time": round(execution_time, 2),
                        "tool_calls_count": len(tool_calls),
                        "is_success": result.get("is_success", False),
                    })
                    
                    # workflow 元信息
                    workflow_data = None
                    if result.get("node_statuses"):
                        workflow_data = {
                            "scenario": result.get("scenario", ""),
                            "node_statuses": result.get("node_statuses", {}),
                            "completed_nodes": result.get("completed_nodes", []),
                            "current_node": result.get("current_node"),
                        }
                    
                    finish_chunk = {
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
                    }
                    if trace_id_hex:
                        finish_chunk["trace_id"] = trace_id_hex
                        finish_chunk["jaeger_url"] = f"/api/jaeger/trace/{trace_id_hex}"
                    if workflow_data:
                        finish_chunk["workflow"] = workflow_data
                    if session_id:
                        finish_chunk["session_id"] = session_id
                    if conversation_id:
                        finish_chunk["conversation_id"] = conversation_id
                    yield format_sse(finish_chunk)
                    yield "data: [DONE]\n\n"
                    return
        
        except AttributeError:
            # 降级：如果 orchestrator 没有 process_query_stream，走同步模式
            logger.warning("process_query_stream 不可用，降级到同步流式")
            result = await orchestrator.process_query(
                query,
                session_id=session_id,
                server_id=getattr(request, "server_id", None),
            )
            
            if not trace_id_hex and result.get("trace_id"):
                trace_id_hex = result.get("trace_id")
            if result.get("session_id"):
                session_id = result.get("session_id")
            if result.get("conversation_id"):
                conversation_id = result.get("conversation_id")
            
            # 直接推送答案正文
            final_content = result.get("result", "")
            if final_content:
                # 按段落切片输出，让前端看起来是渐进的
                paragraphs = re.split(r'(\n\n+)', final_content)
                for para in paragraphs:
                    if para.strip():
                        yield push_delta(para)
            
            # 统计 → metadata
            yield push_meta("summary", {
                "mode": result.get("mode", "react"),
                "execution_time": round(result.get("execution_time", 0), 2),
                "tool_calls_count": len(result.get("tool_calls", [])),
                "is_success": result.get("is_success", False),
            })
            
            workflow_data = None
            if result.get("node_statuses"):
                workflow_data = {
                    "scenario": result.get("scenario", ""),
                    "node_statuses": result.get("node_statuses", {}),
                    "completed_nodes": result.get("completed_nodes", []),
                    "current_node": result.get("current_node"),
                }
            
            finish_chunk = {
                "id": chat_id,
                "object": "chat.completion.chunk",
                "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
            }
            if trace_id_hex:
                finish_chunk["trace_id"] = trace_id_hex
                finish_chunk["jaeger_url"] = f"/api/jaeger/trace/{trace_id_hex}"
            if workflow_data:
                finish_chunk["workflow"] = workflow_data
            if session_id:
                finish_chunk["session_id"] = session_id
            if conversation_id:
                finish_chunk["conversation_id"] = conversation_id
            yield format_sse(finish_chunk)
            yield "data: [DONE]\n\n"
            return
    
    except Exception as e:
        logger.error(f"Stream error: {str(e)}")
        yield push_delta(f"❌ 错误：{str(e)}")
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


def _iso(value):
    """datetime -> isoformat，None 原样返回"""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


@router.get("/models", response_model=ModelList)
async def list_models():
    """List available models"""
    return ModelList(
        data=[
            ModelInfo(id="perfa-agent"),
            ModelInfo(id="perfa-react"),
        ]
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(limit: int = 20):
    """获取真实会话列表"""
    try:
        orchestrator = await get_orchestrator()
        sessions = orchestrator.get_recent_sessions(limit=limit)
        return SessionListResponse(
            sessions=[
                SessionSummary(
                    session_id=item["session_id"],
                    title=item.get("title", "新对话"),
                    message_count=item.get("message_count", 0),
                    created_at=_iso(item.get("created_at")),
                    last_active=_iso(item.get("last_active")),
                    last_user_message=item.get("last_user_message"),
                )
                for item in sessions
            ]
        )
    except Exception as e:
        logger.error(f"List sessions error: {e}")
        return SessionListResponse(sessions=[])


@router.get("/sessions/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str):
    """获取单个会话完整历史"""
    try:
        orchestrator = await get_orchestrator()
        detail = orchestrator.memory.get_session_detail(session_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionDetail(
            session_id=detail["session_id"],
            title=detail.get("title", "新对话"),
            message_count=detail.get("message_count", 0),
            created_at=_iso(detail.get("created_at")),
            last_active=_iso(detail.get("last_active")),
            last_user_message=detail.get("last_user_message"),
            messages=[
                SessionMessage(
                    role=message.get("role", ""),
                    content=message.get("content", ""),
                    timestamp=_iso(message.get("timestamp")),
                    metadata=message.get("metadata") or {},
                )
                for message in detail.get("messages", [])
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """删除单个会话"""
    try:
        orchestrator = await get_orchestrator()
        detail = orchestrator.memory.get_session_detail(session_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Session not found")
        orchestrator.clear_session(session_id)
        return {"success": True, "session_id": session_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
            import asyncio

            raw_servers = [s for s in (result.get("servers", result if isinstance(result, list) else [])) if isinstance(s, dict)]

            async def _resolve_server(s: dict) -> ServerInfo:
                server_id = s.get("server_id", s.get("id", ""))
                status = "unknown"
                status_result = {}

                if check_status_tool and server_id:
                    try:
                        status_result = await asyncio.wait_for(
                            check_status_tool.ainvoke({"server_id": server_id}),
                            timeout=8,
                        )
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

                if status == "unknown":
                    agent_status = s.get("agent_status", "")
                    if agent_status in ("online", "running", "deployed"):
                        status = "online"
                    elif agent_status in ("offline", "stopped", "error"):
                        status = "offline"

                return ServerInfo(
                    server_id=server_id,
                    ip=s.get("ip", s.get("host", "")),
                    alias=s.get("alias", s.get("name")),
                    status=status,
                    tags=s.get("tags", []),
                    hardware=s.get("hardware", s.get("system_info")),
                    agent_id=s.get("agent_id"),
                    agent_port=s.get("agent_port"),
                    agent_status=status_result.get("agent_status") if isinstance(status_result, dict) else s.get("agent_status"),
                    agent_version=status_result.get("version") if isinstance(status_result, dict) else None,
                    current_task=status_result.get("current_task") if isinstance(status_result, dict) else None,
                )

            servers = await asyncio.gather(*[_resolve_server(s) for s in raw_servers])

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
    privilege_mode: str = Field("root", description="提权模式: root/sudo_nopasswd/sudo_password/none")
    sudo_password: Optional[str] = Field(None, description="sudo 密码")
    alias: Optional[str] = Field(None, description="服务器别名")
    tags: List[str] = Field(default_factory=list, description="标签")


class AgentDeployRequest(BaseModel):
    """Agent 部署请求"""
    force_reinstall: bool = Field(default=False, description="是否强制重装")
    agent_only: bool = Field(default=True, description="是否仅重装 node_agent")
    install_dir: Optional[str] = Field(default=None, description="远端安装目录")


class AgentUninstallRequest(BaseModel):
    """Agent 卸载请求"""
    keep_data: bool = Field(default=True, description="是否保留数据")


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
        if req.privilege_mode:
            args["privilege_mode"] = req.privilege_mode
        if req.sudo_password:
            args["sudo_password"] = req.sudo_password
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


@router.post("/servers/{server_id}/agent/deploy")
async def deploy_server_agent(server_id: str, req: AgentDeployRequest):
    """安装或重装指定服务器的 Agent"""
    try:
        orchestrator = await get_orchestrator()
        deploy_tool = orchestrator.tools_dict.get("deploy_agent")

        if not deploy_tool:
            raise HTTPException(status_code=501, detail="deploy_agent 工具不可用")

        result = await deploy_tool.ainvoke({
            "server_id": server_id,
            "force_reinstall": req.force_reinstall,
            "agent_only": req.agent_only,
            **({"install_dir": req.install_dir} if req.install_dir else {}),
        })

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                result = {"raw": result}

        if isinstance(result, dict) and not result.get("success", True):
            return {"success": False, "error": result.get("error", "Agent 部署失败"), "data": result}

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Deploy agent error: {e}")
        return {"success": False, "error": str(e)}


@router.post("/servers/{server_id}/agent/uninstall")
async def uninstall_server_agent(server_id: str, req: AgentUninstallRequest):
    """卸载指定服务器上的 Agent"""
    try:
        orchestrator = await get_orchestrator()
        uninstall_tool = orchestrator.tools_dict.get("uninstall_agent")

        if not uninstall_tool:
            raise HTTPException(status_code=501, detail="uninstall_agent 工具不可用")

        result = await uninstall_tool.ainvoke({
            "server_id": server_id,
            "keep_data": req.keep_data,
        })

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                result = {"raw": result}

        if isinstance(result, dict) and not result.get("success", True):
            return {"success": False, "error": result.get("error", "Agent 卸载失败"), "data": result}

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Uninstall agent error: {e}")
        return {"success": False, "error": str(e)}


@router.get("/servers/{server_id}/agent/status")
async def get_server_agent_status(server_id: str):
    """获取指定服务器的 Agent 实时状态"""
    try:
        orchestrator = await get_orchestrator()
        status_tool = orchestrator.tools_dict.get("check_agent_status")

        if not status_tool:
            raise HTTPException(status_code=501, detail="check_agent_status 工具不可用")

        result = await status_tool.ainvoke({"server_id": server_id})

        if isinstance(result, str):
            import json as _json
            try:
                result = _json.loads(result)
            except _json.JSONDecodeError:
                result = {"raw": result}

        if isinstance(result, dict) and not result.get("success", True):
            return {"success": False, "error": result.get("error", "获取 Agent 状态失败"), "data": result}

        return {"success": True, "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get agent status error: {e}")
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
        list_servers_tool = tools_dict.get("list_servers")
        list_reports_tool = tools_dict.get("list_benchmark_history")

        if not list_servers_tool or not list_reports_tool:
            return ReportListResponse(reports=[])

        servers_result = await list_servers_tool.ainvoke({})
        if isinstance(servers_result, str):
            import json as _json
            try:
                servers_result = _json.loads(servers_result)
            except _json.JSONDecodeError:
                servers_result = []

        servers = servers_result if isinstance(servers_result, list) else servers_result.get("servers", [])
        reports = []

        for server in servers:
            if not isinstance(server, dict):
                continue
            server_id = server.get("server_id")
            if not server_id:
                continue

            result = await list_reports_tool.ainvoke({"server_id": server_id})
            if isinstance(result, str):
                import json as _json
                try:
                    result = _json.loads(result)
                except _json.JSONDecodeError:
                    result = {}

            if not isinstance(result, dict) or not result.get("success", True):
                continue

            for r in result.get("results", []):
                if isinstance(r, dict):
                    reports.append(ReportInfo(
                        id=r.get("task_id", r.get("id", "")),
                        type=r.get("type", r.get("benchmark_type", "unknown")),
                        server_id=r.get("server_id", server_id),
                        created_at=r.get("created_at", r.get("start_time", "")),
                        status=r.get("status", "completed"),
                        summary=r.get("summary"),
                    ))

        reports.sort(key=lambda report: report.created_at or "", reverse=True)
        return ReportListResponse(reports=reports)
    except Exception as e:
        logger.error(f"List reports error: {e}")
        return ReportListResponse(reports=[])


@router.get("/reports/{report_id}", response_model=ReportDetail)
async def get_report(report_id: str):
    """获取报告详情"""
    try:
        orchestrator = await get_orchestrator()
        tools_dict = orchestrator.tools_dict
        list_servers_tool = tools_dict.get("list_servers")
        get_result_tool = tools_dict.get("get_benchmark_result")

        if list_servers_tool and get_result_tool:
            servers_result = await list_servers_tool.ainvoke({})
            if isinstance(servers_result, str):
                import json as _json
                try:
                    servers_result = _json.loads(servers_result)
                except _json.JSONDecodeError:
                    servers_result = []

            servers = servers_result if isinstance(servers_result, list) else servers_result.get("servers", [])

            for server in servers:
                if not isinstance(server, dict):
                    continue
                server_id = server.get("server_id")
                if not server_id:
                    continue

                result = await get_result_tool.ainvoke({"server_id": server_id, "task_id": report_id})
                if isinstance(result, str):
                    import json as _json
                    try:
                        result = _json.loads(result)
                    except _json.JSONDecodeError:
                        result = {}

                if isinstance(result, dict) and result.get("success", True) and (
                    result.get("task_id") == report_id or result.get("id") == report_id
                ):
                    return ReportDetail(
                        id=report_id,
                        type=result.get("type", result.get("benchmark_type", "unknown")),
                        server_id=result.get("server_id", server_id),
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
