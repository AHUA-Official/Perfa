"""
工具管理路由
"""
from flask import Blueprint, request

from ..responses import success, error_response, ErrorCodes

bp = Blueprint('tool', __name__)


@bp.route('/api/tools', methods=['GET'])
def list_tools():
    """
    列出所有工具
    
    GET /api/tools?category=cpu
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.tool_manager:
        return error_response(ErrorCodes.INTERNAL_ERROR, "ToolManager not initialized")
    
    category = request.args.get('category')
    result = agent.tool_manager.list_tools(category)
    
    return success({
        "tools": result['tools'],
        "count": result['count']
    })


@bp.route('/api/tools/<tool_name>', methods=['GET'])
def get_tool(tool_name: str):
    """
    查询工具状态
    
    GET /api/tools/<tool_name>
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.tool_manager:
        return error_response(ErrorCodes.INTERNAL_ERROR, "ToolManager not initialized")
    
    result = agent.tool_manager.check_tool(tool_name)
    
    if not result.get('success'):
        return error_response(ErrorCodes.TOOL_NOT_FOUND, f"Tool '{tool_name}' not found")
    
    return success({
        "name": tool_name,
        "status": result.get('status'),
        "binary_path": result.get('binary_path'),
        "version": result.get('version'),
        "info": result.get('info')
    })


@bp.route('/api/tools/<tool_name>/install', methods=['POST'])
def install_tool(tool_name: str):
    """
    安装工具
    
    POST /api/tools/<tool_name>/install
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.tool_manager:
        return error_response(ErrorCodes.INTERNAL_ERROR, "ToolManager not initialized")
    
    result = agent.tool_manager.install_tool(tool_name)
    
    if not result.get('success'):
        return error_response(
            ErrorCodes.TOOL_INSTALL_FAILED,
            result.get('message', 'Installation failed'),
            {"tool": tool_name}
        )
    
    return success({
        "name": tool_name,
        "installed": True,
        "message": result.get('message')
    }, f"工具 {tool_name} 安装成功")


@bp.route('/api/tools/<tool_name>/uninstall', methods=['POST'])
def uninstall_tool(tool_name: str):
    """
    卸载工具
    
    POST /api/tools/<tool_name>/uninstall
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.tool_manager:
        return error_response(ErrorCodes.INTERNAL_ERROR, "ToolManager not initialized")
    
    result = agent.tool_manager.uninstall_tool(tool_name)
    
    if not result.get('success'):
        return error_response(
            ErrorCodes.INTERNAL_ERROR,
            result.get('message', 'Uninstallation failed'),
            {"tool": tool_name}
        )
    
    return success({
        "name": tool_name,
        "installed": False,
        "message": result.get('message')
    }, f"工具 {tool_name} 卸载成功")
