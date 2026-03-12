"""
健康检查路由
"""
from flask import Blueprint
import time

from ..responses import success

bp = Blueprint('health', __name__)


# 记录启动时间
_start_time = time.time()


@bp.route('/health', methods=['GET'])
def health_check():
    """
    健康检查
    
    GET /health
    """
    return success({
        "status": "healthy",
        "uptime_seconds": int(time.time() - _start_time)
    })


@bp.route('/api/status', methods=['GET'])
def get_status():
    """
    获取 Agent 状态
    
    GET /api/status
    """
    # 通过 Flask 的 current_app 获取 agent 实例
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent:
        return success({
            "status": "unknown",
            "uptime_seconds": int(time.time() - _start_time)
        })
    
    data = {
        "agent_id": agent.agent_id,
        "uptime_seconds": int(time.time() - _start_time),
        "monitor_running": agent.monitor.is_running() if agent.monitor else False,
        "current_task": None,
        "version": "1.0.0"
    }
    
    # 获取当前任务
    if agent.benchmark_executor:
        current_task = agent.benchmark_executor.get_current_task()
        if current_task:
            data["current_task"] = current_task.to_dict()
    
    return success(data)
