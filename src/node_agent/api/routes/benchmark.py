"""
压测任务路由
"""
from flask import Blueprint, request

from ..responses import success, error_response, ErrorCodes

bp = Blueprint('benchmark', __name__)


@bp.route('/api/benchmark/run', methods=['POST'])
def run_benchmark():
    """执行压测"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    data = request.get_json()
    if not data:
        return error_response(ErrorCodes.INVALID_PARAMS, "Request body is required")
    
    test_name = data.get('test_name')
    params = data.get('params', {})
    
    if not test_name:
        return error_response(ErrorCodes.INVALID_PARAMS, "test_name is required")
    
    if agent.benchmark_executor.is_busy():
        current = agent.benchmark_executor.get_current_task()
        return error_response(ErrorCodes.TASK_RUNNING, "已有任务在运行",
            {"current_task_id": current.task_id if current else None})
    
    try:
        result = agent.benchmark_executor.run_benchmark(test_name, params)
        return success(result)
    except Exception as e:
        code = ErrorCodes.TOOL_NOT_INSTALLED if "not installed" in str(e).lower() else ErrorCodes.INTERNAL_ERROR
        return error_response(code, str(e))


@bp.route('/api/benchmark/cancel', methods=['POST'])
def cancel_benchmark():
    """取消任务"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    task_id = (request.get_json() or {}).get('task_id')
    if not task_id:
        return error_response(ErrorCodes.INVALID_PARAMS, "task_id is required")
    
    if agent.benchmark_executor.cancel_task(task_id):
        return success({"task_id": task_id, "status": "cancelled"})
    return error_response(ErrorCodes.TASK_CANNOT_CANCEL, "无法取消任务")


@bp.route('/api/benchmark/pause', methods=['POST'])
def pause_benchmark():
    """暂停任务"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    task_id = (request.get_json() or {}).get('task_id')
    if not task_id:
        return error_response(ErrorCodes.INVALID_PARAMS, "task_id is required")
    
    if agent.benchmark_executor.pause_task(task_id):
        return success({"task_id": task_id, "status": "paused"})
    return error_response(ErrorCodes.TASK_NOT_RUNNING, "无法暂停任务")


@bp.route('/api/benchmark/resume', methods=['POST'])
def resume_benchmark():
    """恢复任务"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    task_id = (request.get_json() or {}).get('task_id')
    if not task_id:
        return error_response(ErrorCodes.INVALID_PARAMS, "task_id is required")
    
    if agent.benchmark_executor.resume_task(task_id):
        return success({"task_id": task_id, "status": "running"})
    return error_response(ErrorCodes.TASK_NOT_RUNNING, "无法恢复任务")


@bp.route('/api/benchmark/current', methods=['GET'])
def get_current_task():
    """获取当前任务"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return success({"current_task": None})
    
    current = agent.benchmark_executor.get_current_task()
    return success({
        "current_task": current.to_dict() if current else None,
        "is_busy": agent.benchmark_executor.is_busy()
    })


@bp.route('/api/benchmark/tasks', methods=['GET'])
def list_tasks():
    """任务列表"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return success({"tasks": []})
    
    limit = request.args.get('limit', 50, type=int)
    tasks = agent.benchmark_executor.list_tasks(limit=limit)
    return success({"tasks": tasks, "count": len(tasks)})


@bp.route('/api/benchmark/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id: str):
    """查询任务状态"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    status = agent.benchmark_executor.get_task_status(task_id)
    if not status:
        return error_response(ErrorCodes.TASK_NOT_FOUND, f"Task '{task_id}' not found")
    return success(status)


@bp.route('/api/benchmark/results/<task_id>', methods=['GET'])
def get_result(task_id: str):
    """获取测试结果"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    result = agent.benchmark_executor.get_result(task_id)
    if not result:
        return error_response(ErrorCodes.TASK_NOT_FOUND, f"Result for task '{task_id}' not found")
    return success(result)


@bp.route('/api/benchmark/results', methods=['GET'])
def list_results():
    """结果列表"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return success({"results": []})
    
    test_name = request.args.get('test_name')
    limit = request.args.get('limit', 100, type=int)
    
    results = agent.benchmark_executor.result_collector.list_results(test_name=test_name, limit=limit)
    return success({"results": [r.to_dict() for r in results], "count": len(results)})


@bp.route('/api/benchmark/logs/<task_id>', methods=['GET'])
def get_log(task_id: str):
    """获取日志文件路径"""
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.benchmark_executor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "BenchmarkExecutor not initialized")
    
    log_path = agent.benchmark_executor.get_log_path(task_id)
    if not log_path:
        return error_response(ErrorCodes.NOT_FOUND, f"Log file for task '{task_id}' not found")
    return success({"task_id": task_id, "log_file": log_path})
