"""
Agent HTTP API 服务器
接收MCP Server的指令并执行
"""

import logging
from flask import Flask, jsonify, request
from typing import Dict, Any

logger = logging.getLogger(__name__)


class APIServer:
    """HTTP API服务器"""
    
    def __init__(
        self,
        agent_id: str,
        task_executor,
        monitor,
        health_checker,
        config: Dict[str, Any]
    ):
        """
        初始化API服务器
        
        Args:
            agent_id: Agent ID
            task_executor: 任务执行器
            monitor: 监控管理器
            health_checker: 健康检查器
            config: API配置
        """
        self.agent_id = agent_id
        self.task_executor = task_executor
        self.monitor = monitor
        self.health_checker = health_checker
        self.config = config
        
        # Flask应用
        self.app = Flask(__name__)
        
        # 注册路由
        self._register_routes()
        
        logger.info("API服务器初始化完成")
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """健康检查"""
            return jsonify({
                'agent_id': self.agent_id,
                'status': 'healthy',
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/api/run_benchmark', methods=['POST'])
        def run_benchmark():
            """执行压测任务"""
            data = request.json
            test_name = data.get('test_name')
            params = data.get('params', {})
            task_id = data.get('task_id')
            
            # 关联监控
            self.monitor.set_task_id(task_id)
            
            # 执行任务
            result = self.task_executor.run_benchmark(test_name, params)
            
            return jsonify(result)
        
        @self.app.route('/api/cancel_task', methods=['POST'])
        def cancel_task():
            """取消任务"""
            data = request.json
            task_id = data.get('task_id')
            
            result = self.task_executor.cancel_task(task_id)
            
            return jsonify(result)
        
        @self.app.route('/api/pause_task', methods=['POST'])
        def pause_task():
            """暂停任务"""
            data = request.json
            task_id = data.get('task_id')
            
            result = self.task_executor.pause_task(task_id)
            
            return jsonify(result)
        
        @self.app.route('/api/resume_task', methods=['POST'])
        def resume_task():
            """恢复任务"""
            data = request.json
            task_id = data.get('task_id')
            
            result = self.task_executor.resume_task(task_id)
            
            return jsonify(result)
        
        @self.app.route('/api/task_status/<task_id>', methods=['GET'])
        def task_status(task_id):
            """查询任务状态"""
            result = self.task_executor.get_task_status(task_id)
            return jsonify(result)
        
        @self.app.route('/api/start_monitoring', methods=['POST'])
        def start_monitoring():
            """启动监控"""
            data = request.json
            monitor_id = data.get('monitor_id')
            metrics = data.get('metrics', [])
            interval = data.get('interval', 5)
            
            # 配置监控
            self.monitor.configure(metrics, interval)
            
            return jsonify({
                'monitor_id': monitor_id,
                'status': 'running',
                'message': '监控已启动'
            })
        
        @self.app.route('/api/stop_monitoring', methods=['POST'])
        def stop_monitoring():
            """停止监控"""
            data = request.json
            monitor_id = data.get('monitor_id')
            
            self.monitor.set_task_id(None)
            
            return jsonify({
                'monitor_id': monitor_id,
                'status': 'stopped',
                'message': '监控已停止'
            })
        
        @self.app.route('/api/execute_command', methods=['POST'])
        def execute_command():
            """执行系统命令（用于环境初始化等）"""
            data = request.json
            command = data.get('command')
            
            # 执行命令
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True
            )
            
            return jsonify({
                'command': command,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
    
    def start(self):
        """启动API服务器（阻塞）"""
        host = self.config.get('host', '0.0.0.0')
        port = self.config.get('port', 9000)
        
        logger.info(f"API服务器启动: {host}:{port}")
        
        # 启动Flask应用（阻塞）
        self.app.run(
            host=host,
            port=port,
            threaded=True
        )
    
    def stop(self):
        """停止API服务器"""
        logger.info("API服务器已停止")
        # Flask没有优雅停止的方法，通常通过进程信号处理


# ==================== 导入 ====================

from datetime import datetime
