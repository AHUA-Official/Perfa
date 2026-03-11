#!/usr/bin/env python3
"""
守护进程 Agent 主入口

架构：多线程（非多进程）
- Main Thread: 主循环 + 将来 HTTP API Server
- Monitoring Thread: 监控采集（daemon）
- Prometheus: 指标 HTTP 服务（后台线程）
- TaskExecutor（待实现）: 任务执行线程
"""

import sys
import signal
import time
import logging
from typing import Optional
from prometheus_client import start_http_server

from monitor import Monitor
from tool.manager import ToolManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class NodeAgent:
    
    def __init__(self, agent_id: str = "node-agent-001", metrics_port: int = 8000):
        """
        初始化节点 Agent
        
        Args:
            agent_id: Agent 唯一标识
            metrics_port: Prometheus 指标暴露端口
        """
        self.agent_id = agent_id
        self.metrics_port = metrics_port
        
        # 各个功能模块
        self.monitor: Optional[Monitor] = None
        self.tool_manager: Optional[ToolManager] = None
        
        # 运行状态
        self.running = False
        
        logger.info(f"节点 Agent 初始化: {agent_id}")
        logger.info(f"指标端口: {metrics_port}")
    
    def start(self):
        """启动 Agent"""
        logger.info("="*50)
        logger.info("启动节点 Agent（多线程架构）")
        logger.info("="*50)
        
        # 1. 注册并启动工具管理器
        self._register_tools()
        
        # 2. 启动 Prometheus metrics HTTP 服务
        self._start_metrics_server()
        
        # 3. 启动监控模块（后台线程）
        self._start_monitor()
        
        self.running = True
        logger.info("节点 Agent 已启动")
    
    def _start_metrics_server(self):
        """启动 Prometheus 指标 HTTP 服务"""
        logger.info(f"启动 Prometheus metrics 服务: http://0.0.0.0:{self.metrics_port}/metrics")
        start_http_server(self.metrics_port)
        logger.info("Prometheus metrics 服务已启动")
    
    def stop(self):
        """停止 Agent"""
        logger.info("停止节点 Agent...")
        
        # 停止监控模块
        if self.monitor:
            self.monitor.stop()
        
        self.running = False
        logger.info("节点 Agent 已停止")
    
    def _start_monitor(self):
        """启动监控模块"""
        logger.info("初始化监控模块...")
        
        config = {
            'interval': 5,  # 每5秒采集一次
            'enabled_metrics': ['cpu', 'memory', 'disk', 'network']
        }
        
        self.monitor = Monitor(
            agent_id=self.agent_id,
            config=config
        )
        
        self.monitor.start()
        logger.info("监控模块已启动")
    
    def _init_tool_manager(self):
        """初始化工具管理器"""
        logger.info("初始化工具管理器...")
        self.tool_manager = ToolManager()
        
        # 检查所有工具状态
        status = self.tool_manager.check_all(verify=True)
        logger.info(f"工具状态: {status['count']} 个工具")
        for tool in status['tools']:
            logger.info(f"  - {tool['tool']}: {tool['status']} (verified: {tool.get('verified')})")


def signal_handler(signum, frame):
    """信号处理函数"""
    global agent
    logger.info(f"收到信号 {signum}，准备退出...")
    if agent:
        agent.stop()
    sys.exit(0)


# 全局 agent 实例
agent: Optional[NodeAgent] = None


def main():
    """主函数"""
    global agent
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动 agent
    agent = NodeAgent(
        agent_id="node-agent-001",
        metrics_port=8000  # Prometheus 指标端口
    )
    agent.start()
    
    # 保持主线程运行
    try:
        while agent.running:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到键盘中断")
        agent.stop()


if __name__ == "__main__":
    main()
