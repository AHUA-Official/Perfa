"""服务器管理工具"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import paramiko
from .base import BaseTool
from storage import Database, Server
from agent_client import AgentClient

# 配置日志
logger = logging.getLogger(__name__)


class RegisterServerTool(BaseTool):
    """注册服务器"""
    
    name = "register_server"
    description = "注册压测服务器"
    input_schema = {
        "type": "object",
        "properties": {
            "ip": {
                "type": "string",
                "description": "服务器 IP 地址"
            },
            "port": {
                "type": "integer",
                "description": "SSH 端口",
                "default": 22
            },
            "ssh_user": {
                "type": "string",
                "description": "SSH 用户名"
            },
            "ssh_password": {
                "type": "string",
                "description": "SSH 密码（可选，如果使用密钥认证）"
            },
            "ssh_key_path": {
                "type": "string",
                "description": "SSH 私钥路径（可选）"
            },
            "alias": {
                "type": "string",
                "description": "服务器别名"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "标签列表"
            }
        },
        "required": ["ip", "ssh_user"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, ip: str, ssh_user: str, port: int = 22,
                ssh_password: Optional[str] = None,
                ssh_key_path: Optional[str] = None,
                alias: str = "", tags: list = None, **kwargs) -> Dict[str, Any]:
        """执行注册"""
        # 1. 测试 SSH 连接
        logger.info(f"[注册服务器] 开始测试SSH连接: {ip}:{port} (用户: {ssh_user})")
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if ssh_key_path:
                logger.info(f"[注册服务器] 使用密钥认证: {ssh_key_path}")
                client.connect(
                    ip, 
                    port=port, 
                    username=ssh_user, 
                    key_filename=ssh_key_path, 
                    timeout=10,
                    banner_timeout=10
                )
            else:
                logger.info(f"[注册服务器] 使用密码认证（禁用公钥和agent）")
                client.connect(
                    ip, 
                    port=port, 
                    username=ssh_user, 
                    password=ssh_password, 
                    timeout=10,
                    banner_timeout=10,
                    allow_agent=False,      # 禁用SSH agent
                    look_for_keys=False     # 禁用自动查找密钥文件
                )
            logger.info(f"[注册服务器] SSH连接测试成功: {ip}:{port}")
            client.close()
        except paramiko.AuthenticationException as e:
            logger.error(f"[注册服务器] 认证失败 - {ip}:{port}: {str(e)}")
            logger.error(f"[注册服务器] 认证方式: {'密钥' if ssh_key_path else '密码'}")
            logger.error(f"[注册服务器] 用户名: {ssh_user}")
            if not ssh_key_path:
                logger.error(f"[注册服务器] 密码长度: {len(ssh_password) if ssh_password else 0}")
            return {
                "success": False,
                "error": f"SSH 认证失败: {str(e)}"
            }
        except paramiko.SSHException as e:
            logger.error(f"[注册服务器] SSH协议错误 - {ip}:{port}: {str(e)}")
            return {
                "success": False,
                "error": f"SSH 协议错误: {str(e)}"
            }
        except Exception as e:
            logger.error(f"[注册服务器] SSH连接失败 - {ip}:{port}: {type(e).__name__}: {str(e)}")
            logger.error(f"[注册服务器] 异常详情", exc_info=True)
            return {
                "success": False,
                "error": f"SSH 连接失败: {str(e)}"
            }
        
        # 2. 检查是否已注册
        existing = self.db.get_server_by_ip(ip)
        if existing:
            return {
                "success": False,
                "error": f"服务器 {ip} 已注册",
                "server_id": existing.server_id
            }
        
        # 3. 创建服务器记录
        now = datetime.now()
        server_id = str(uuid.uuid4())
        
        server = Server(
            server_id=server_id,
            ip=ip,
            port=port,
            alias=alias,
            ssh_user=ssh_user,
            ssh_password_encrypted=ssh_password,  # TODO: 加密
            ssh_key_path=ssh_key_path,
            tags=tags or [],
            created_at=now,
            updated_at=now
        )
        
        self.db.create_server(server)
        
        return {
            "success": True,
            "server_id": server_id,
            "message": f"服务器 {ip} 注册成功"
        }


class ListServersTool(BaseTool):
    """列出服务器"""
    
    name = "list_servers"
    description = "列出已注册的服务器"
    input_schema = {
        "type": "object",
        "properties": {}
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """执行查询"""
        servers = self.db.list_servers()
        
        return {
            "success": True,
            "servers": [
                {
                    "server_id": s.server_id,
                    "ip": s.ip,
                    "port": s.port,
                    "alias": s.alias,
                    "agent_id": s.agent_id,
                    "agent_status": "deployed" if s.agent_id else "not_deployed",
                    "tags": s.tags,
                    "created_at": s.created_at.isoformat()
                }
                for s in servers
            ],
            "count": len(servers)
        }


class RemoveServerTool(BaseTool):
    """移除服务器"""
    
    name = "remove_server"
    description = "移除服务器注册"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, **kwargs) -> Dict[str, Any]:
        """执行删除"""
        server = self.db.get_server(server_id)
        if not server:
            return {
                "success": False,
                "error": f"服务器 {server_id} 不存在"
            }
        
        # TODO: 检查是否有正在运行的任务
        
        self.db.delete_server(server_id)
        
        return {
            "success": True,
            "message": f"服务器 {server.ip} 已移除"
        }


class GetServerInfoTool(BaseTool):
    """获取服务器信息"""
    
    name = "get_server_info"
    description = "获取服务器硬件信息和实时状态"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, **kwargs) -> Dict[str, Any]:
        """执行查询"""
        server = self.db.get_server(server_id)
        if not server:
            return {
                "success": False,
                "error": f"服务器 {server_id} 不存在"
            }
        
        result = {
            "success": True,
            "server": {
                "server_id": server.server_id,
                "ip": server.ip,
                "port": server.port,
                "alias": server.alias,
                "agent_id": server.agent_id,
                "tags": server.tags
            },
            "hardware": None,
            "status": None,
            "agent_status": "not_deployed"
        }
        
        # 如果有 Agent，获取实时信息
        if server.agent_id and server.agent_port:
            try:
                agent_url = f"http://{server.ip}:{server.agent_port}"
                client = AgentClient(agent_url)
                
                # 获取硬件信息
                hardware = client.get_system_info()
                result["hardware"] = hardware.model_dump()
                
                # 获取实时状态
                status = client.get_system_status()
                result["status"] = status.model_dump()
                
                result["agent_status"] = "online"
            except Exception as e:
                result["agent_status"] = "offline"
                result["error"] = f"Agent 离线: {str(e)}"
        
        return result


class UpdateServerInfoTool(BaseTool):
    """更新服务器信息"""
    
    name = "update_server_info"
    description = "更新服务器信息（别名、标签等）"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "alias": {
                "type": "string",
                "description": "服务器别名"
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "标签列表"
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, alias: Optional[str] = None,
                tags: Optional[list] = None, **kwargs) -> Dict[str, Any]:
        """执行更新"""
        server = self.db.get_server(server_id)
        if not server:
            return {
                "success": False,
                "error": f"服务器 {server_id} 不存在"
            }
        
        # 更新字段
        if alias is not None:
            server.alias = alias
        if tags is not None:
            server.tags = tags
        
        server.updated_at = datetime.now()
        self.db.update_server(server)
        
        return {
            "success": True,
            "message": f"服务器 {server.ip} 信息已更新"
        }
