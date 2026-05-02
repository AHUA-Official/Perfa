"""Agent 生命周期管理工具"""
import uuid
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import subprocess
import paramiko
from .base import BaseTool
from storage import Database
from agent_client import AgentClient

# 配置日志
logger = logging.getLogger(__name__)

# 本地 Perfa 项目路径
LOCAL_PERFA_DIR = "/home/ubuntu/Perfa"
# 目标服务器默认安装路径
DEFAULT_INSTALL_DIR = "/opt/perfa"


REMOTE_INFRA_START_SCRIPT = "ops/scripts/start-local-infra.sh"
REMOTE_INFRA_STOP_SCRIPT = "ops/scripts/stop-local-infra.sh"


class DeployAgentTool(BaseTool):
    """部署 Agent - 传输项目并调用本地基础设施启动脚本"""
    
    name = "deploy_agent"
    description = "部署完整监控栈到目标服务器（传输代码、检查环境、调用统一基础设施脚本启动 VM + Grafana + Agent）"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "install_dir": {
                "type": "string",
                "description": "Perfa 安装目录",
                "default": "/opt/perfa"
            },
            "force_reinstall": {
                "type": "boolean",
                "description": "已部署时是否强制重装 Agent",
                "default": False
            },
            "agent_only": {
                "type": "boolean",
                "description": "仅重装 node_agent，不重启 VM/Grafana",
                "default": False
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db

    def _sync_agent_privilege_config(self, server) -> tuple[bool, Optional[str]]:
        """将服务器权限配置同步到远端 Agent 运行时"""
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port or 8080}", timeout=15)
            if not client.health_check():
                return False, "Agent 离线，无法同步权限配置"
            payload = {
                "privilege_mode": server.privilege_mode,
                "sudo_password": server.sudo_password_encrypted,
            }
            client.update_config(payload)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def _ssh_connect(self, server) -> paramiko.SSHClient:
        """建立 SSH 连接"""
        logger.info(f"[SSH] 开始连接服务器: {server.ip}:{server.port} (用户: {server.ssh_user})")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if server.ssh_key_path:
                logger.info(f"[SSH] 使用密钥认证: {server.ssh_key_path}")
                client.connect(
                    server.ip, 
                    port=server.port,
                    username=server.ssh_user, 
                    key_filename=server.ssh_key_path, 
                    timeout=30,
                    banner_timeout=30
                )
            else:
                logger.info(f"[SSH] 使用密码认证（禁用公钥和agent）")
                client.connect(
                    server.ip, 
                    port=server.port,
                    username=server.ssh_user, 
                    password=server.ssh_password_encrypted, 
                    timeout=30,
                    banner_timeout=30,
                    allow_agent=False,      # 禁用SSH agent
                    look_for_keys=False     # 禁用自动查找密钥文件
                )
            
            logger.info(f"[SSH] 连接成功: {server.ip}:{server.port}")
            return client
            
        except paramiko.AuthenticationException as e:
            logger.error(f"[SSH] 认证失败 - {server.ip}:{server.port}: {str(e)}")
            logger.error(f"[SSH] 认证方式: {'密钥' if server.ssh_key_path else '密码'}")
            logger.error(f"[SSH] 用户名: {server.ssh_user}")
            if not server.ssh_key_path:
                logger.error(f"[SSH] 密码长度: {len(server.ssh_password_encrypted) if server.ssh_password_encrypted else 0}")
            raise
        except paramiko.SSHException as e:
            logger.error(f"[SSH] SSH协议错误 - {server.ip}:{server.port}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[SSH] 连接异常 - {server.ip}:{server.port}: {type(e).__name__}: {str(e)}")
            logger.error(f"[SSH] 异常详情", exc_info=True)
            raise
    
    def _check_runtime(self, client: paramiko.SSHClient) -> Dict[str, Any]:
        """检查目标服务器运行时环境"""
        checks = {}
        errors = []
        
        # Python3
        stdin, stdout, stderr = client.exec_command("python3 --version 2>/dev/null")
        checks["python3"] = stdout.read().decode().strip()
        if not checks["python3"]:
            errors.append("缺少 Python3")
        
        # pip3
        stdin, stdout, stderr = client.exec_command("pip3 --version 2>/dev/null")
        checks["pip3"] = stdout.read().decode().strip()
        if not checks["pip3"]:
            errors.append("缺少 pip3")
        
        # Docker (VM 和 Grafana 需要)
        stdin, stdout, stderr = client.exec_command("docker --version 2>/dev/null")
        checks["docker"] = stdout.read().decode().strip()
        if not checks["docker"]:
            errors.append("缺少 Docker (VM 和 Grafana 依赖)")
        
        # Docker Compose (Grafana 需要)
        stdin, stdout, stderr = client.exec_command("docker compose version 2>/dev/null || docker-compose --version 2>/dev/null")
        checks["docker_compose"] = stdout.read().decode().strip()
        if not checks["docker_compose"]:
            errors.append("缺少 Docker Compose (Grafana 依赖)")
        
        return {"checks": checks, "errors": errors}
    
    def _rsync_project(self, server, install_dir: str) -> tuple:
        """通过 rsync 传输必要的项目文件"""
        import shutil
        
        # 构建 SSH 命令
        if server.ssh_key_path:
            ssh_cmd = f"ssh -i {server.ssh_key_path} -p {server.port} -o StrictHostKeyChecking=no"
        elif server.ssh_password_encrypted:
            # 使用 sshpass 支持密码认证
            if not shutil.which("sshpass"):
                return False, "缺少 sshpass 工具，请安装: apt install sshpass -y"
            ssh_cmd = f"sshpass -p '{server.ssh_password_encrypted}' ssh -p {server.port} -o StrictHostKeyChecking=no"
        else:
            ssh_cmd = f"ssh -p {server.port} -o StrictHostKeyChecking=no"
        
        # 传输整个项目，排除不必要的文件
        rsync_cmd = [
            "rsync", "-avz",
            "--exclude=*.pyc",
            "--exclude=__pycache__",
            "--exclude=venv",
            "--exclude=*.log",
            "--exclude=.git",
            "--exclude=data/vm-storage",
            "--exclude=benchmark/work",
            "--exclude=*.db",
            "--exclude=.idea",
            "--exclude=.vscode",
            f"-e", ssh_cmd,
            f"{LOCAL_PERFA_DIR}/",
            f"{server.ssh_user}@{server.ip}:{install_dir}/"
        ]
        
        result = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0, result.stderr

    def _restart_agent_only(self, client: paramiko.SSHClient, install_dir: str) -> tuple[int, str, str]:
        """仅重装并重启 node_agent，避免每次带上整套监控栈"""
        command = (
            f"cd {install_dir}/src/node_agent && "
            f"pip3 install -q -r requirements.txt 2>/dev/null || "
            f"pip3 install -q flask prometheus-client psutil pydantic requests && "
            f"pkill -f '[p]ython3 main.py' || true && "
            f"sleep 2 && "
            f"setsid python3 main.py >/tmp/agent.log 2>&1 < /dev/null &"
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=180)
        output = stdout.read().decode()
        error_output = stderr.read().decode()
        exit_code = stdout.channel.recv_exit_status()
        return exit_code, output, error_output

    def _wait_for_agent_health(self, server, attempts: int = 12, interval_sec: int = 5) -> bool:
        """轮询等待 Agent 健康检查通过，避免重启后短暂未就绪就误判失败"""
        client = AgentClient(f"http://{server.ip}:8080", timeout=10)
        for attempt in range(1, attempts + 1):
            if client.health_check():
                logger.info(f"[部署Agent] Agent 健康检查通过 (attempt={attempt})")
                return True
            logger.warning(f"[部署Agent] Agent 尚未就绪，{interval_sec}秒后重试 (attempt={attempt}/{attempts})")
            time.sleep(interval_sec)
        return False
    
    def execute(
        self,
        server_id: str,
        install_dir: str = DEFAULT_INSTALL_DIR,
        force_reinstall: bool = False,
        agent_only: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """部署监控栈"""
        logger.info(f"[部署Agent] 开始部署 - 服务器ID: {server_id}, 安装目录: {install_dir}")
        
        server = self.db.get_server(server_id)
        if not server:
            logger.error(f"[部署Agent] 服务器不存在: {server_id}")
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        is_reinstall = bool(server.agent_id)
        if is_reinstall and not force_reinstall:
            logger.warning(f"[部署Agent] 服务器已部署: {server_id}, agent_id: {server.agent_id}")
            return {
                "success": False,
                "error": f"服务器已部署 (agent_id: {server.agent_id})，如需重装请传 force_reinstall=true",
                "agent_id": server.agent_id,
                "can_reinstall": True
            }
        
        agent_id = server.agent_id or str(uuid.uuid4())
        logger.info(f"[部署Agent] 生成Agent ID: {agent_id}")
        
        try:
            # 1. 建立 SSH 连接
            logger.info(f"[部署Agent] 步骤1: 建立SSH连接")
            client = self._ssh_connect(server)
            
            # 2. 检查运行时环境
            logger.info(f"[部署Agent] 步骤2: 检查运行时环境")
            runtime = self._check_runtime(client)
            if runtime["errors"]:
                logger.error(f"[部署Agent] 环境检查失败: {', '.join(runtime['errors'])}")
                client.close()
                return {
                    "success": False,
                    "error": "环境检查失败: " + ", ".join(runtime["errors"]),
                    "runtime": runtime["checks"]
                }
            logger.info(f"[部署Agent] 环境检查通过: {runtime['checks']}")
            
            # 3. 创建安装目录
            logger.info(f"[部署Agent] 步骤3: 创建安装目录 {install_dir}")
            client.exec_command(f"mkdir -p {install_dir}")[1].channel.recv_exit_status()
            client.close()
            
            # 4. rsync 传输项目
            logger.info(f"[部署Agent] 步骤4: 使用rsync传输项目文件")
            success, error = self._rsync_project(server, install_dir)
            if not success:
                logger.error(f"[部署Agent] 代码传输失败: {error}")
                return {"success": False, "error": f"代码传输失败: {error}"}
            logger.info(f"[部署Agent] 代码传输成功")
            
            # 5. 安装 Python 依赖
            logger.info(f"[部署Agent] 步骤5: 安装Python依赖")
            client = self._ssh_connect(server)
            client.exec_command(
                f"cd {install_dir}/src/node_agent && "
                f"pip3 install -q -r requirements.txt 2>/dev/null || "
                f"pip3 install -q flask prometheus-client psutil pydantic requests"
            )[1].channel.recv_exit_status()
            
            if agent_only:
                logger.info(f"[部署Agent] 步骤6: 仅重装并重启 node_agent")
                exit_code, output, error_output = self._restart_agent_only(client, install_dir)
            else:
                logger.info(f"[部署Agent] 步骤6: 调用启动脚本 {REMOTE_INFRA_START_SCRIPT}")
                stdin, stdout, stderr = client.exec_command(
                    f"cd {install_dir} && "
                    f"sed -i 's|/home/ubuntu/Perfa|{install_dir}|g' {REMOTE_INFRA_START_SCRIPT} && "
                    f"chmod +x {REMOTE_INFRA_START_SCRIPT} && "
                    f"bash {REMOTE_INFRA_START_SCRIPT}",
                    timeout=180
                )
                output = stdout.read().decode()
                error_output = stderr.read().decode()
                exit_code = stdout.channel.recv_exit_status()
            logger.info(f"[部署Agent] 启动脚本执行完成, 退出码: {exit_code}")
            logger.debug(f"[部署Agent] 启动脚本输出: {output[:500]}")
            client.close()
            
            if exit_code != 0:
                logger.error(f"[部署Agent] 启动脚本执行失败, 退出码: {exit_code}")
                return {
                    "success": False,
                    "error": "启动脚本执行失败",
                    "output": output,
                    "stderr": error_output
                }
            
            # 7. 验证 Agent 状态
            logger.info(f"[部署Agent] 步骤7: 验证Agent状态")
            if not self._wait_for_agent_health(server):
                logger.error(f"[部署Agent] Agent健康检查失败")
                return {
                    "success": False,
                    "error": "Agent 启动失败，请检查日志",
                    "agent_id": agent_id
                }
            logger.info(f"[部署Agent] Agent健康检查通过")

            sync_ok, sync_error = self._sync_agent_privilege_config(server)
            if not sync_ok:
                logger.error(f"[部署Agent] 同步 Agent 权限配置失败: {sync_error}")
                return {
                    "success": False,
                    "error": f"Agent 权限配置同步失败: {sync_error}",
                    "agent_id": agent_id
                }
            logger.info("[部署Agent] Agent 权限配置同步完成")
            
            # 8. 更新数据库
            logger.info(f"[部署Agent] 步骤8: 更新数据库")
            now = datetime.now()
            server.agent_id = agent_id
            server.agent_port = 8080
            server.updated_at = now
            self.db.update_server(server)
            
            logger.info(f"[部署Agent] 部署成功 - Agent ID: {agent_id}")
            return {
                "success": True,
                "agent_id": agent_id,
                "message": "Agent 重装成功" if is_reinstall else "监控栈部署成功",
                "reinstalled": is_reinstall,
                "services": {
                    "agent": f"http://{server.ip}:8080",
                    "grafana": f"http://{server.ip}:3000",
                    "victoria_metrics": f"http://{server.ip}:8428"
                },
                "runtime": runtime["checks"]
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"[部署Agent] 部署超时")
            return {"success": False, "error": "部署超时"}
        except Exception as e:
            logger.error(f"[部署Agent] 部署失败: {type(e).__name__}: {str(e)}")
            logger.error(f"[部署Agent] 异常详情", exc_info=True)
            return {"success": False, "error": f"部署失败: {str(e)}"}


class CheckAgentStatusTool(BaseTool):
    """检查 Agent 状态 - 调用 Agent API"""
    
    name = "check_agent_status"
    description = "检查 Agent 运行状态、版本、当前任务等信息"
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
        """调用 Agent /api/status API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {
                "success": True,
                "agent_status": "not_deployed",
                "message": "该服务器未部署 Agent"
            }
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=10)
            
            if not client.health_check():
                return {
                    "success": True,
                    "agent_status": "offline",
                    "agent_id": server.agent_id
                }
            
            status = client.get_status()
            
            return {
                "success": True,
                "agent_status": "online",
                "agent_id": status.agent_id,
                "version": status.version,
                "uptime_seconds": status.uptime_seconds,
                "status": status.status,
                "current_task": status.current_task
            }
            
        except Exception as e:
            return {
                "success": True,
                "agent_status": "error",
                "agent_id": server.agent_id,
                "error": str(e)
            }


class GetAgentLogsTool(BaseTool):
    """获取 Agent 日志 - 调用 Agent API"""
    
    name = "get_agent_logs"
    description = "获取 Agent 运行日志"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "lines": {
                "type": "integer",
                "description": "返回的日志行数",
                "default": 100
            },
            "level": {
                "type": "string",
                "description": "日志级别过滤",
                "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, lines: int = 100,
                level: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/storage/logs API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            logs = client.get_logs(lines=lines, level=level)
            
            return {
                "success": True,
                "logs": logs,
                "lines": lines,
                "level": level
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取日志失败: {str(e)}"}


class ConfigureAgentTool(BaseTool):
    """配置 Agent - 调用 Agent API"""
    
    name = "configure_agent"
    description = "更新 Agent 配置参数"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "config": {
                "type": "object",
                "description": "配置参数"
            }
        },
        "required": ["server_id", "config"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, config: dict, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/config API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            import requests

            merged_config = dict(config)
            if "privilege_mode" not in merged_config:
                merged_config["privilege_mode"] = server.privilege_mode
            if "sudo_password" not in merged_config and server.sudo_password_encrypted is not None:
                merged_config["sudo_password"] = server.sudo_password_encrypted

            response = requests.post(
                f"http://{server.ip}:{server.agent_port}/api/config",
                json=merged_config,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "配置已更新",
                "config": merged_config
            }
            
        except Exception as e:
            return {"success": False, "error": f"配置更新失败: {str(e)}"}


class UninstallAgentTool(BaseTool):
    """卸载 Agent - 调用统一基础设施停止脚本"""
    
    name = "uninstall_agent"
    description = "停止所有服务（VM + Grafana + Agent）"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "keep_data": {
                "type": "boolean",
                "description": "是否保留数据文件",
                "default": True
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def _ssh_connect(self, server) -> paramiko.SSHClient:
        """建立 SSH 连接"""
        logger.info(f"[SSH] 开始连接服务器: {server.ip}:{server.port} (用户: {server.ssh_user})")
        
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            if server.ssh_key_path:
                logger.info(f"[SSH] 使用密钥认证: {server.ssh_key_path}")
                client.connect(
                    server.ip, 
                    port=server.port,
                    username=server.ssh_user, 
                    key_filename=server.ssh_key_path, 
                    timeout=30,
                    banner_timeout=30
                )
            else:
                logger.info(f"[SSH] 使用密码认证（禁用公钥和agent）")
                client.connect(
                    server.ip, 
                    port=server.port,
                    username=server.ssh_user, 
                    password=server.ssh_password_encrypted, 
                    timeout=30,
                    banner_timeout=30,
                    allow_agent=False,      # 禁用SSH agent
                    look_for_keys=False     # 禁用自动查找密钥文件
                )
            
            logger.info(f"[SSH] 连接成功: {server.ip}:{server.port}")
            return client
            
        except paramiko.AuthenticationException as e:
            logger.error(f"[SSH] 认证失败 - {server.ip}:{server.port}: {str(e)}")
            logger.error(f"[SSH] 认证方式: {'密钥' if server.ssh_key_path else '密码'}")
            logger.error(f"[SSH] 用户名: {server.ssh_user}")
            if not server.ssh_key_path:
                logger.error(f"[SSH] 密码长度: {len(server.ssh_password_encrypted) if server.ssh_password_encrypted else 0}")
            raise
        except paramiko.SSHException as e:
            logger.error(f"[SSH] SSH协议错误 - {server.ip}:{server.port}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"[SSH] 连接异常 - {server.ip}:{server.port}: {type(e).__name__}: {str(e)}")
            logger.error(f"[SSH] 异常详情", exc_info=True)
            raise
    
    def execute(self, server_id: str, keep_data: bool = True, **kwargs) -> Dict[str, Any]:
        """调用统一基础设施停止脚本停止所有服务"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        agent_id = server.agent_id
        install_dir = DEFAULT_INSTALL_DIR
        
        try:
            client = self._ssh_connect(server)
            
            # 调用统一基础设施停止脚本
            stdin, stdout, stderr = client.exec_command(
                f"cd {install_dir} && "
                f"sed -i 's|/home/ubuntu/Perfa|{install_dir}|g' {REMOTE_INFRA_STOP_SCRIPT} 2>/dev/null || true && "
                f"chmod +x {REMOTE_INFRA_STOP_SCRIPT} 2>/dev/null || true && "
                f"bash {REMOTE_INFRA_STOP_SCRIPT}",
                timeout=60
            )
            
            stdout.read().decode()
            stdout.channel.recv_exit_status()
            
            # 可选清理文件
            if not keep_data:
                client.exec_command(f"rm -rf {install_dir}")
            
            client.close()
            
            # 更新数据库
            server.agent_id = None
            server.agent_port = None
            server.updated_at = datetime.now()
            self.db.update_server(server)
            
            return {
                "success": True,
                "message": f"服务已停止 (Agent: {agent_id})",
                "keep_data": keep_data
            }
            
        except Exception as e:
            return {"success": False, "error": f"卸载失败: {str(e)}"}
