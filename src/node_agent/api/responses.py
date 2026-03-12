"""
统一响应格式
"""
from typing import Any, Dict, Optional
from flask import jsonify


def success(data: Any = None, message: str = "操作成功") -> Dict:
    """
    成功响应
    
    Args:
        data: 响应数据
        message: 消息
    
    Returns:
        响应字典
    """
    response = {
        "success": True,
        "message": message
    }
    if data is not None:
        response["data"] = data
    return jsonify(response)


def error(code: str, message: str, details: Optional[Dict] = None, 
          status_code: int = 400) -> tuple:
    """
    错误响应
    
    Args:
        code: 错误码
        message: 错误消息
        details: 详细信息
        status_code: HTTP状态码
    
    Returns:
        (响应字典, HTTP状态码)
    """
    response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        response["error"]["details"] = details
    return jsonify(response), status_code


# 错误码定义
class ErrorCodes:
    """错误码常量"""
    
    # 通用错误
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"
    NOT_FOUND = "NOT_FOUND"
    
    # 任务相关
    TASK_RUNNING = "TASK_RUNNING"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    TASK_NOT_RUNNING = "TASK_NOT_RUNNING"
    TASK_CANNOT_CANCEL = "TASK_CANNOT_CANCEL"
    
    # 工具相关
    TOOL_NOT_INSTALLED = "TOOL_NOT_INSTALLED"
    TOOL_INSTALL_FAILED = "TOOL_INSTALL_FAILED"
    TOOL_NOT_FOUND = "TOOL_NOT_FOUND"
    
    # 监控相关
    MONITOR_ALREADY_RUNNING = "MONITOR_ALREADY_RUNNING"
    MONITOR_NOT_RUNNING = "MONITOR_NOT_RUNNING"


# HTTP 状态码映射
ERROR_STATUS_CODES = {
    ErrorCodes.INTERNAL_ERROR: 500,
    ErrorCodes.INVALID_PARAMS: 400,
    ErrorCodes.NOT_FOUND: 404,
    ErrorCodes.TASK_RUNNING: 409,  # Conflict
    ErrorCodes.TASK_NOT_FOUND: 404,
    ErrorCodes.TASK_NOT_RUNNING: 400,
    ErrorCodes.TASK_CANNOT_CANCEL: 400,
    ErrorCodes.TOOL_NOT_INSTALLED: 400,
    ErrorCodes.TOOL_INSTALL_FAILED: 500,
    ErrorCodes.TOOL_NOT_FOUND: 404,
    ErrorCodes.MONITOR_ALREADY_RUNNING: 409,
    ErrorCodes.MONITOR_NOT_RUNNING: 400,
}


def error_response(code: str, message: str, details: Optional[Dict] = None) -> tuple:
    """
    便捷错误响应（自动获取状态码）
    
    Args:
        code: 错误码
        message: 错误消息
        details: 详细信息
    
    Returns:
        (响应字典, HTTP状态码)
    """
    status_code = ERROR_STATUS_CODES.get(code, 400)
    return error(code, message, details, status_code)
