"""
OpenAI Compatible API Implementation
"""

import json
import uuid
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_agent.core.logger import get_logger
logger = get_logger()

from .schemas import (
    ChatRequest, ChatResponse, ChatChoice, ChatMessage,
    ModelInfo, ModelList
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
    
    Yields SSE formatted strings
    """
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    
    try:
        orchestrator = await get_orchestrator()
        
        # Stream header
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"role": "assistant"}, "index": 0}]
        })
        
        # Process query
        result = await orchestrator.process_query(query)
        
        # Stream thinking process
        thinking = result.get("thinking_process", "")
        if thinking:
            yield format_sse({
                "id": chat_id,
                "object": "chat.completion.chunk",
                "choices": [{"delta": {"content": "## 💭 思考过程\n\n"}, "index": 0}]
            })
            
            for line in thinking.split("\n"):
                if line.strip():
                    yield format_sse({
                        "id": chat_id,
                        "object": "chat.completion.chunk",
                        "choices": [{"delta": {"content": line + "\n"}, "index": 0}]
                    })
        
        # Stream result
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {"content": "\n---\n\n## ✅ 执行结果\n\n"}, "index": 0}]
        })
        
        content = result.get("result", "")
        for line in content.split("\n"):
            if line.strip():
                yield format_sse({
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "choices": [{"delta": {"content": line + "\n"}, "index": 0}]
                })
        
        # Stream performance stats
        execution_time = result.get("execution_time", 0)
        tool_calls = result.get("tool_calls", [])
        
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{
                "delta": {
                    "content": f"\n---\n\n⏱️ **性能统计**\n- 总耗时：{execution_time:.2f}秒\n- 工具调用：{len(tool_calls)}次\n"
                },
                "index": 0
            }]
        })
        
        # Stream finish
        yield format_sse({
            "id": chat_id,
            "object": "chat.completion.chunk",
            "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
        })
        
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
