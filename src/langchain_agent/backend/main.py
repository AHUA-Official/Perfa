"""
FastAPI Application Entry Point

@file: backend/main.py
@desc: FastAPI 应用入口（Web API 模式）
@author: Perfa Team
@date: 2026-03-19
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 使用统一日志模块
from langchain_agent.core.logger import get_logger

# 初始化日志
logger = get_logger()

from .openai_api import router as openai_router

# 从环境变量获取端口，默认 10000
API_PORT = int(os.getenv('LANGCHAIN_API_PORT', 10000))


# ============ FastAPI 应用 ============
app = FastAPI(
    title="Perfa Agent API",
    description="OpenAI Compatible API for Perfa LangChain Agent",
    version="0.1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(openai_router, prefix="/v1")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("=" * 60)
    logger.info(f"Perfa Agent API (Web 模式) 启动，端口: {API_PORT}")
    logger.info("=" * 60)
    
    # Initialize Orchestrator (singleton)
    from .openai_api import get_orchestrator
    orchestrator = await get_orchestrator()
    logger.info(f"Orchestrator 初始化完成，工具数量: {len(orchestrator.tools)}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Perfa Agent API 关闭中...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Perfa Agent API",
        "version": "0.1.0",
        "port": API_PORT,
        "docs": "/docs",
        "openai_compatible": "/v1/chat/completions"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "port": API_PORT}
