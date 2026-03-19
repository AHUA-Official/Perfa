"""
Perfa - LangChain Agent Module

@file: core/logger.py
@desc: 统一日志配置模块
@author: Perfa Team
@date: 2026-03-19

使用方式：
    from langchain_agent.core.logger import logger
    
    logger.info("信息日志")
    logger.error("错误日志")
"""

import os
import sys
from pathlib import Path
from loguru import logger

# ============ 日志配置 ============

# 是否已初始化
_initialized = False


def setup_logger(
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True,
    log_file: str = None,
    retention_days: int = 1
):
    """
    初始化统一日志系统
    
    Args:
        log_level: 日志级别 (DEBUG, INFO, WARNING, ERROR)
        log_to_file: 是否写入文件
        log_to_console: 是否输出到控制台
        log_file: 日志文件路径（默认自动检测）
        retention_days: 日志保留天数
    """
    global _initialized
    
    if _initialized:
        return logger
    
    # 移除默认处理器
    logger.remove()
    
    # 日志目录
    if log_file is None:
        # 自动检测项目根目录
        project_root = Path(__file__).parent.parent.parent.parent
        log_dir = project_root / 'logs'
    else:
        log_dir = Path(log_file).parent
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / 'langchain_agent.log'
    
    # 控制台输出格式（彩色）
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    
    # 文件输出格式（无颜色）
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    
    # 1. 控制台输出
    if log_to_console:
        logger.add(
            sink=sys.stderr,
            level=log_level,
            format=console_format,
            colorize=True,
            enqueue=True
        )
    
    # 2. 文件输出
    if log_to_file:
        logger.add(
            sink=str(log_file_path),
            level="DEBUG",  # 文件记录更详细的日志
            format=file_format,
            rotation="10 MB",           # 单文件最大 10MB
            retention=f"{retention_days} days",  # 保留天数
            compression="zip",          # 压缩旧日志
            encoding="utf-8",
            enqueue=True
        )
    
    _initialized = True
    
    logger.info("=" * 50)
    logger.info("日志系统初始化完成")
    logger.info(f"日志级别: {log_level}")
    logger.info(f"日志文件: {log_file_path}")
    logger.info(f"保留天数: {retention_days} 天")
    logger.info("=" * 50)
    
    return logger


def get_logger():
    """
    获取 logger 实例
    
    如果未初始化，自动使用默认配置初始化
    """
    global _initialized
    
    if not _initialized:
        setup_logger()
    
    return logger


# 导出 logger 实例（懒加载）
__all__ = ['logger', 'setup_logger', 'get_logger']
