"""压测工具管理工具"""
from typing import Dict, Any, Optional
from .base import BaseTool
from storage import Database
from agent_client import AgentClient

TOOL_ENUM = [
    "unixbench", "stream", "superpi", "mlc", "fio", "hping3",
    "sysbench", "openssl_speed", "stress_ng", "iperf3", "7z_b",
]

CATEGORY_MAP = {
    "cpu": ["unixbench", "superpi", "sysbench", "openssl_speed", "stress_ng", "7z_b"],
    "mem": ["stream", "mlc"],
    "disk": ["fio"],
    "network": ["hping3", "iperf3"],
}


class InstallToolTool(BaseTool):
    """安装压测工具"""
    
    name = "install_tool"
    description = "在目标服务器的 Agent 上安装压测工具（含短时 benchmark 工具）"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "tool_name": {
                "type": "string",
                "description": "工具名称",
                "enum": TOOL_ENUM
            }
        },
        "required": ["server_id", "tool_name"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/tools/<tool_name>/install API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent，请先部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=300)
            
            # 检查 Agent 是否在线
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            # 调用安装 API
            result = client.install_tool(
                tool_name,
                privilege_mode=server.privilege_mode,
                sudo_password=server.sudo_password_encrypted,
            )
            
            return {
                "success": True,
                "message": f"工具 {tool_name} 安装成功",
                "tool_name": tool_name,
                "details": result,
                "privilege_mode": server.privilege_mode,
            }
            
        except Exception as e:
            error_msg = str(e)
            # 解析常见错误
            if "not installed" in error_msg.lower():
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 安装失败，请检查依赖",
                    "details": error_msg
                }
            return {
                "success": False,
                "error": f"安装失败: {error_msg}",
                "privilege_mode": server.privilege_mode,
                "hint": "如果目标机不是 root，请确认 privilege_mode 和 sudo_password 配置正确"
            }


class UninstallToolTool(BaseTool):
    """卸载压测工具"""
    
    name = "uninstall_tool"
    description = "卸载目标服务器 Agent 上的压测工具"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "tool_name": {
                "type": "string",
                "description": "工具名称",
                "enum": TOOL_ENUM
            }
        },
        "required": ["server_id", "tool_name"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/tools/<tool_name>/uninstall API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=60)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            result = client.uninstall_tool(
                tool_name,
                privilege_mode=server.privilege_mode,
                sudo_password=server.sudo_password_encrypted,
            )
            
            return {
                "success": True,
                "message": f"工具 {tool_name} 已卸载",
                "tool_name": tool_name,
                "details": result,
                "privilege_mode": server.privilege_mode,
            }
            
        except Exception as e:
            return {"success": False, "error": f"卸载失败: {str(e)}"}


class ListToolsTool(BaseTool):
    """列出压测工具状态"""
    
    name = "list_tools"
    description = "列出目标服务器 Agent 上所有压测工具的安装状态"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "category": {
                "type": "string",
                "description": "按类别筛选（cpu, mem, disk, network）",
                "enum": ["cpu", "mem", "disk", "network"]
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, category: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/tools API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            # 获取工具列表
            tools = client.list_tools()
            
            # 按类别筛选
            if category:
                tools = [t for t in tools if t.get("name") in CATEGORY_MAP.get(category, [])]
            
            return {
                "success": True,
                "server_id": server_id,
                "tools": tools,
                "count": len(tools)
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取工具列表失败: {str(e)}"}


class VerifyToolTool(BaseTool):
    """验证压测工具可用性"""
    
    name = "verify_tool"
    description = "验证目标服务器 Agent 上的压测工具是否可用"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "tool_name": {
                "type": "string",
                "description": "工具名称",
                "enum": TOOL_ENUM
            }
        },
        "required": ["server_id", "tool_name"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/tools/<tool_name> API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            # 获取工具信息
            tool_info = client.get_tool(tool_name)
            
            # 判断是否可用
            is_installed = tool_info.get("status") == "installed"
            binary_path = tool_info.get("binary_path")
            version = tool_info.get("version")
            
            return {
                "success": True,
                "tool_name": tool_name,
                "installed": is_installed,
                "available": is_installed and binary_path is not None,
                "binary_path": binary_path,
                "version": version,
                "info": tool_info.get("info")
            }
            
        except Exception as e:
            return {
                "success": True,
                "tool_name": tool_name,
                "installed": False,
                "available": False,
                "error": str(e)
            }
