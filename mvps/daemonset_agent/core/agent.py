"""
Agent 主类
负责启动和管理所有Agent组件
"""

import threading
import logging
from typing import Dict, Any

from core.task_executor import TaskExecutor
from core.monitor import Monitor
from core.logger import LogPusher
from core.health import HealthChecker
from api.server import APIServer
from communication.http_client import MCPClient
from storage.influxdb_writer import InfluxDBWriter
from storage.sqlite_writer import SQLiteWriter

logger = logging.getLogger(__name__)


class Agent:
    """Agent主类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Agent
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.agent_id = config['agent']['id']
        self.agent_name = config['agent'].get('name', self.agent_id)
        
        # 初始化组件
        self._init_components()
        
        # 运行状态
        self.running = False
        self.threads = []
        
        logger.info(f"Agent初始化完成: {self.agent_id}")
    
    def _init_components(self):
        """初始化所有组件"""
        logger.info("初始化组件...")
        
        # 1. 数据存储
        self.influxdb_writer = InfluxDBWriter(
            url=self.config['influxdb']['url'],
            token=self.config['influxdb']['token'],
            org=self.config['influxdb']['org'],
            bucket=self.config['influxdb']['bucket']
        )
        
        self.sqlite_writer = SQLiteWriter(
            db_path=self.config['sqlite']['path']
        )
        
        # 2. 监控采集器
        self.monitor = Monitor(
            agent_id=self.agent_id,
            influxdb_writer=self.influxdb_writer,
            config=self.config.get('monitoring', {})
        )
        
        # 3. 任务执行器
        self.task_executor = TaskExecutor(
            agent_id=self.agent_id,
            sqlite_writer=self.sqlite_writer,
            influxdb_writer=self.influxdb_writer
        )
        
        # 4. 日志推送器
        self.log_pusher = LogPusher(
            agent_id=self.agent_id,
            mcp_server_url=self.config['mcp_server']['websocket_url']
        )
        
        # 5. 健康检查器
        self.health_checker = HealthChecker(
            agent_id=self.agent_id,
            monitor=self.monitor,
            task_executor=self.task_executor
        )
        
        # 6. MCP客户端（用于上报状态）
        self.mcp_client = MCPClient(
            base_url=self.config['mcp_server']['url']
        )
        
        # 7. API服务器（接收MCP Server指令）
        self.api_server = APIServer(
            agent_id=self.agent_id,
            task_executor=self.task_executor,
            monitor=self.monitor,
            health_checker=self.health_checker,
            config=self.config.get('api', {})
        )
        
        logger.info("组件初始化完成")
    
    def start(self):
        """启动Agent"""
        logger.info("启动Agent...")
        self.running = True
        
        # 1. 启动监控线程
        monitor_thread = threading.Thread(
            target=self.monitor.start,
            name="MonitorThread",
            daemon=True
        )
        monitor_thread.start()
        self.threads.append(monitor_thread)
        logger.info("监控线程已启动")
        
        # 2. 启动日志推送线程
        log_thread = threading.Thread(
            target=self.log_pusher.start,
            name="LogPusherThread",
            daemon=True
        )
        log_thread.start()
        self.threads.append(log_thread)
        logger.info("日志推送线程已启动")
        
        # 3. 启动健康检查线程
        health_thread = threading.Thread(
            target=self.health_checker.start,
            name="HealthCheckerThread",
            daemon=True
        )
        health_thread.start()
        self.threads.append(health_thread)
        logger.info("健康检查线程已启动")
        
        # 4. 向MCP Server注册
        self._register_to_mcp_server()
        
        # 5. 启动API服务器（阻塞运行）
        logger.info(f"启动API服务器: {self.config['api']['host']}:{self.config['api']['port']}")
        self.api_server.start()  # 这会阻塞主线程
    
    def stop(self):
        """停止Agent"""
        logger.info("停止Agent...")
        self.running = False
        
        # 停止所有组件
        self.monitor.stop()
        self.log_pusher.stop()
        self.health_checker.stop()
        self.api_server.stop()
        
        # 等待所有线程结束
        for thread in self.threads:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Agent已停止")
    
    def _register_to_mcp_server(self):
        """向MCP Server注册"""
        try:
            logger.info("向MCP Server注册...")
            response = self.mcp_client.register_agent(
                agent_id=self.agent_id,
                agent_name=self.agent_name,
                host=self._get_local_ip(),
                port=self.config['api']['port']
            )
            logger.info(f"注册成功: {response}")
        except Exception as e:
            logger.warning(f"注册失败: {e}，将在后台重试")
    
    def _get_local_ip(self) -> str:
        """获取本机IP"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
