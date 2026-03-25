"""
HTTP API 服务器
"""
import logging
import threading
from pathlib import Path
from typing import Optional

from flask import Flask, send_from_directory

from .routes import health_bp, monitor_bp, tool_bp, benchmark_bp


logger = logging.getLogger(__name__)


class APIServer:
    """HTTP API 服务器"""
    
    def __init__(self, agent, host: str = "0.0.0.0", port: int = 8080):
        """
        初始化 API 服务器
        
        Args:
            agent: NodeAgent 实例
            host: 监听地址
            port: 监听端口
        """
        self.agent = agent
        self.host = host
        self.port = port
        
        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        
        # 创建 Flask 应用，指定静态文件夹
        self.app = Flask(__name__, static_folder=str(self.static_dir), static_url_path='')
        
        # 将 agent 存储在 app.config 中，供路由使用
        self.app.config['agent'] = agent
        
        # 注册路由
        self._register_routes()
        
        logger.info(f"APIServer initialized on {host}:{port}")
    
    def _register_routes(self):
        """注册所有路由"""
        # 首页路由 - 返回控制面板
        @self.app.route('/')
        def index():
            """返回控制面板页面"""
            return send_from_directory(self.static_dir, 'index.html')
        
        self.app.register_blueprint(health_bp)
        self.app.register_blueprint(monitor_bp)
        self.app.register_blueprint(tool_bp)
        self.app.register_blueprint(benchmark_bp)
        
        # 添加错误处理
        self.app.register_error_handler(404, self._not_found)
        self.app.register_error_handler(500, self._internal_error)
        
        logger.info("Routes registered")
    
    def _not_found(self, e):
        """404 错误处理"""
        from .responses import error_response, ErrorCodes
        return error_response(ErrorCodes.NOT_FOUND, "Resource not found")
    
    def _internal_error(self, e):
        """500 错误处理"""
        from .responses import error_response, ErrorCodes
        return error_response(ErrorCodes.INTERNAL_ERROR, "Internal server error")
    
    def run(self):
        """启动 API 服务器（阻塞）"""
        logger.info(f"Starting API server on {self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, threaded=True)
    
    def run_background(self) -> threading.Thread:
        """
        在后台线程启动 API 服务器
        
        Returns:
            服务器线程
        """
        thread = threading.Thread(target=self.run, daemon=True, name="APIServer")
        thread.start()
        logger.info("API server started in background thread")
        return thread
