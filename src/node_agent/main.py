#!/usr/bin/env python3
"""
守护进程 Agent 主入口

架构：多线程（非多进程）
- Main Thread: 主循环 + HTTP API Server
- Monitoring Thread: 监控采集（daemon）
- Prometheus: 指标 HTTP 服务（后台线程）
- BenchmarkExecutor: 压测任务执行器
"""

import sys
import signal
import time
import logging
from typing import Optional
import os
from prometheus_client import start_http_server

from monitor import Monitor
from tool.manager import ToolManager
from api.server import APIServer
from benchmark.executor import BenchmarkExecutor
from privilege import get_privilege_config

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
    
    def __init__(self, agent_id: str = "node-agent-001", metrics_port: int = 8000, api_port: int = 8080):
        """
        初始化节点 Agent
        
        Args:
            agent_id: Agent 唯一标识
            metrics_port: Prometheus 指标暴露端口
            api_port: HTTP API 服务端口
        """
        self.agent_id = agent_id
        self.metrics_port = metrics_port
        self.api_port = api_port
        
        # 各个功能模块
        self.monitor: Optional[Monitor] = None
        self.tool_manager: Optional[ToolManager] = None
        self.benchmark_executor: Optional[BenchmarkExecutor] = None
        self.api_server: Optional[APIServer] = None
        
        # 运行状态
        self.running = False
        
        logger.info(f"节点 Agent 初始化: {agent_id}")
        logger.info(f"指标端口: {metrics_port}")
        logger.info(f"API 端口: {api_port}")
        privilege = get_privilege_config()
        logger.info(f"权限模式: {privilege.mode}")
    
    def start(self):
        """启动 Agent"""
        logger.info("="*50)
        logger.info("启动节点 Agent（多线程架构）")
        logger.info("="*50)
        
        # 1. 初始化工具管理器
        self._init_tool_manager()
        
        # 2. 初始化压测执行器
        self._init_benchmark_executor()
        
        # 3. 启动 Prometheus metrics HTTP 服务
        self._start_metrics_server()
        
        # 4. 启动监控模块（后台线程）
        self._start_monitor()
        
        # 5. 启动 HTTP API 服务器
        self._start_api_server()
        
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
        
        # 停止压测执行器
        if self.benchmark_executor:
            self.benchmark_executor.shutdown()
        
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
    
    def _init_benchmark_executor(self):
        """初始化压测执行器"""
        logger.info("初始化压测执行器...")
        self.benchmark_executor = BenchmarkExecutor(
            tool_manager=self.tool_manager
        )
        
        # 注册运行器
        from benchmark.runners import (
            FioRunner, StreamRunner, UnixBenchRunner,
            MlcRunner, SuperPiRunner, Hping3Runner,
            SysbenchCpuRunner, SysbenchMemoryRunner, SysbenchThreadsRunner,
            OpenSSLRunner, StressNgRunner, Iperf3Runner, SevenZipRunner
        )
        self.benchmark_executor.register_runner(FioRunner())
        self.benchmark_executor.register_runner(StreamRunner())
        self.benchmark_executor.register_runner(UnixBenchRunner())
        self.benchmark_executor.register_runner(MlcRunner())
        self.benchmark_executor.register_runner(SuperPiRunner())
        self.benchmark_executor.register_runner(Hping3Runner())
        self.benchmark_executor.register_runner(SysbenchCpuRunner())
        self.benchmark_executor.register_runner(SysbenchMemoryRunner())
        self.benchmark_executor.register_runner(SysbenchThreadsRunner())
        self.benchmark_executor.register_runner(OpenSSLRunner())
        self.benchmark_executor.register_runner(StressNgRunner())
        self.benchmark_executor.register_runner(Iperf3Runner())
        self.benchmark_executor.register_runner(SevenZipRunner())
        
        logger.info("压测执行器已初始化")
    
    def _start_api_server(self):
        """启动 HTTP API 服务器"""
        logger.info(f"启动 HTTP API 服务器: http://0.0.0.0:{self.api_port}")
        self.api_server = APIServer(
            agent=self,
            host="0.0.0.0",
            port=self.api_port
        )
        # 在后台线程启动
        self.api_server.run_background()
        logger.info("HTTP API 服务器已启动")


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
    
    # OTel: 初始化追踪（在所有其他导入之前）
    _otel_initialized = False
    try:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if otlp_endpoint:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            
            resource = Resource.create({
                "service.name": "perfa-node-agent",
                "service.version": "0.1.0",
            })
            provider = TracerProvider(resource=resource)
            provider.add_span_processor(BatchSpanProcessor(
                OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            ))
            trace.set_tracer_provider(provider)
            _otel_initialized = True
            logger.info(f"✅ Node Agent OTel: OTLP 导出 → {otlp_endpoint}")
    except ImportError:
        logger.warning("⚠️ opentelemetry 未安装，Node Agent 追踪不可用")
    except Exception as e:
        logger.warning(f"⚠️ Node Agent OTel 初始化失败: {e}")
    
    # OTel: Flask 自动 Instrumentation
    if _otel_initialized:
        try:
            from opentelemetry.instrumentation.flask import FlaskInstrumentor
            FlaskInstrumentor().instrument()
            logger.info("✅ FlaskInstrumentor 已启用")
        except ImportError:
            logger.warning("⚠️ opentelemetry-instrumentation-flask 未安装")
        except Exception as e:
            logger.warning(f"⚠️ FlaskInstrumentor 启用失败: {e}")
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动 agent
    agent = NodeAgent(
        agent_id="node-agent-001",
        metrics_port=8000,  # Prometheus 指标端口
        api_port=8080       # HTTP API 端口
    )
    agent.start()
    
    # 打印访问信息
    logger.info("="*50)
    logger.info("服务访问地址:")
    logger.info(f"  - 控制面板: http://localhost:8080/")
    logger.info(f"  - API 文档: http://localhost:8080/health")
    logger.info(f"  - Prometheus: http://localhost:8000/metrics")
    logger.info("="*50)
    
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
