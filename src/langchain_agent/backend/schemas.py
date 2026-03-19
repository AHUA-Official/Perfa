"""
Pydantic Schemas for OpenAI Compatible API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """Chat message"""
    role: str = Field(..., description="Message role: user/assistant/system")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Chat completion request (OpenAI compatible)"""
    model: str = Field(default="perfa-agent", description="Model name (ignored)")
    messages: List[ChatMessage] = Field(..., description="Chat messages")
    stream: bool = Field(default=False, description="Enable streaming output")
    temperature: Optional[float] = Field(default=None, description="Temperature (ignored)")
    max_tokens: Optional[int] = Field(default=None, description="Max tokens (ignored)")


class ChatChoice(BaseModel):
    """Chat choice"""
    index: int = Field(default=0)
    message: Optional[ChatMessage] = None
    delta: Optional[Dict[str, str]] = None
    finish_reason: Optional[str] = None


class ChatUsage(BaseModel):
    """Token usage"""
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)


class ChatResponse(BaseModel):
    """Chat completion response (OpenAI compatible)"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{datetime.now().timestamp()}")
    object: str = Field(default="chat.completion")
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    model: str = Field(default="perfa-agent")
    choices: List[ChatChoice]
    usage: Optional[ChatUsage] = None


class ModelInfo(BaseModel):
    """Model information"""
    id: str
    object: str = "model"
    created: int = Field(default_factory=lambda: int(datetime.now().timestamp()))
    owned_by: str = "perfa"


class ModelList(BaseModel):
    """Model list response"""
    object: str = "list"
    data: List[ModelInfo]
