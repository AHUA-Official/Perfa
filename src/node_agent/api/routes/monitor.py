"""
监控相关路由
"""
import os
import shutil
from pathlib import Path
from flask import Blueprint, request

from ..responses import success, error_response, ErrorCodes

bp = Blueprint('monitor', __name__)


@bp.route('/api/monitor/start', methods=['POST'])
def start_monitoring():
    """
    启动监控
    
    POST /api/monitor/start
    Body: {"interval": 5, "enabled_metrics": ["cpu", "memory"]}
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.monitor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "Monitor not initialized")
    
    if agent.monitor.is_running():
        return error_response(ErrorCodes.MONITOR_ALREADY_RUNNING, "Monitor is already running")
    
    # 解析参数
    data = request.get_json() or {}
    interval = data.get('interval', 5)
    enabled_metrics = data.get('enabled_metrics')
    
    # 更新配置
    if interval:
        agent.monitor.interval = interval
    if enabled_metrics:
        agent.monitor.enabled_metrics = enabled_metrics
    
    # 启动监控
    agent.monitor.start()
    
    return success({
        "running": True,
        "interval": agent.monitor.interval,
        "enabled_metrics": agent.monitor.enabled_metrics
    }, "监控已启动")


@bp.route('/api/monitor/stop', methods=['POST'])
def stop_monitoring():
    """
    停止监控
    
    POST /api/monitor/stop
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.monitor:
        return error_response(ErrorCodes.INTERNAL_ERROR, "Monitor not initialized")
    
    if not agent.monitor.is_running():
        return error_response(ErrorCodes.MONITOR_NOT_RUNNING, "Monitor is not running")
    
    agent.monitor.stop()
    
    return success({
        "running": False
    }, "监控已停止")


@bp.route('/api/monitor/status', methods=['GET'])
def monitor_status():
    """
    监控状态
    
    GET /api/monitor/status
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    if not agent or not agent.monitor:
        return success({
            "running": False,
            "message": "Monitor not initialized"
        })
    
    return success({
        "running": agent.monitor.is_running(),
        "interval": agent.monitor.interval,
        "enabled_metrics": agent.monitor.enabled_metrics
    })


@bp.route('/api/system/info', methods=['GET'])
def system_info():
    """
    获取系统静态信息
    
    GET /api/system/info
    返回: hostname, os, arch, cpu_model, cpu_cores, memory_total, kernel, machine_id
    """
    try:
        from monitor.info import system_info as sys_info
        return success({
            "system": sys_info.info,
            "labels": sys_info.get_labels()
        })
    except ImportError:
        return error_response(ErrorCodes.INTERNAL_ERROR, "System info module not available")


@bp.route('/api/system/status', methods=['GET'])
def system_status():
    """
    获取系统当前状态（实时采集）
    
    GET /api/system/status
    返回: CPU、内存、磁盘、网络的实时使用情况
    """
    import psutil
    
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.5)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 内存
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # 磁盘
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        
        # 网络
        net_io = psutil.net_io_counters()
        
        # 系统负载
        load_avg = os.getloadavg()
        
        # 运行时间
        uptime_seconds = int(psutil.boot_time())
        
        return success({
            "cpu": {
                "percent": cpu_percent,
                "count": cpu_count,
                "freq_mhz": cpu_freq.current if cpu_freq else None,
            },
            "memory": {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_gb": round(mem.used / (1024**3), 2),
                "percent": mem.percent,
            },
            "swap": {
                "total_gb": round(swap.total / (1024**3), 2),
                "used_gb": round(swap.used / (1024**3), 2),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
                "read_bytes": disk_io.read_bytes if disk_io else None,
                "write_bytes": disk_io.write_bytes if disk_io else None,
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "connections": len(psutil.net_connections()),
            },
            "load_average": {
                "1min": load_avg[0],
                "5min": load_avg[1],
                "15min": load_avg[2],
            },
            "uptime_seconds": uptime_seconds,
        })
    except Exception as e:
        return error_response(ErrorCodes.INTERNAL_ERROR, f"Failed to get system status: {str(e)}")


@bp.route('/api/storage/usage', methods=['GET'])
def storage_usage():
    """
    获取存储使用情况
    
    GET /api/storage/usage
    返回: benchmark 结果数据库、日志文件的大小和数量
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    data_dir = Path("/var/lib/node_agent")
    working_dir = Path("/tmp/benchmark_work")
    
    result = {
        "data_dir": str(data_dir),
        "working_dir": str(working_dir),
        "database": None,
        "logs": None,
        "working_dir_files": None,
        "total_size_mb": 0,
    }
    
    total_size = 0
    
    # 数据库
    db_path = data_dir / "benchmark_results.db"
    if db_path.exists():
        db_size = db_path.stat().st_size
        result["database"] = {
            "path": str(db_path),
            "size_mb": round(db_size / (1024**2), 2),
            "exists": True,
        }
        total_size += db_size
    
    # 日志目录
    log_dir = data_dir / "logs"
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        log_size = sum(f.stat().st_size for f in log_files if f.is_file())
        result["logs"] = {
            "path": str(log_dir),
            "count": len(log_files),
            "total_size_mb": round(log_size / (1024**2), 2),
        }
        total_size += log_size
    
    # 工作目录
    if working_dir.exists():
        work_files = list(working_dir.rglob("*"))
        work_size = sum(f.stat().st_size for f in work_files if f.is_file())
        result["working_dir_files"] = {
            "path": str(working_dir),
            "count": len(work_files),
            "total_size_mb": round(work_size / (1024**2), 2),
        }
        total_size += work_size
    
    result["total_size_mb"] = round(total_size / (1024**2), 2)
    
    # 如果有 benchmark_executor，获取结果数量
    if agent and hasattr(agent, 'benchmark_executor') and agent.benchmark_executor:
        try:
            results = agent.benchmark_executor.result_collector.list_results(limit=10000)
            result["database"]["result_count"] = len(results)
        except:
            pass
    
    return success(result)


@bp.route('/api/storage/cleanup', methods=['POST'])
def storage_cleanup():
    """
    清理存储空间
    
    POST /api/storage/cleanup
    Body: {
        "clean_logs": true,
        "keep_logs_days": 7,
        "clean_working_dir": true,
        "clean_old_results": false,
        "keep_results_days": 30
    }
    """
    from flask import current_app
    agent = current_app.config.get('agent')
    
    data = request.get_json() or {}
    
    clean_logs = data.get('clean_logs', False)
    keep_logs_days = data.get('keep_logs_days', 7)
    clean_working_dir = data.get('clean_working_dir', False)
    clean_old_results = data.get('clean_old_results', False)
    keep_results_days = data.get('keep_results_days', 30)
    
    result = {
        "logs_deleted": 0,
        "logs_size_freed_mb": 0,
        "working_files_deleted": 0,
        "working_size_freed_mb": 0,
        "results_deleted": 0,
    }
    
    data_dir = Path("/var/lib/node_agent")
    working_dir = Path("/tmp/benchmark_work")
    
    # 清理日志
    if clean_logs:
        log_dir = data_dir / "logs"
        if log_dir.exists():
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(days=keep_logs_days)
            
            for log_file in log_dir.glob("*.log"):
                try:
                    # 从文件名解析日期
                    filename = log_file.stem
                    date_str = filename.split("_")[0]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if file_date < cutoff:
                        size = log_file.stat().st_size
                        log_file.unlink()
                        result["logs_deleted"] += 1
                        result["logs_size_freed_mb"] += size / (1024**2)
                except Exception:
                    pass
            
            result["logs_size_freed_mb"] = round(result["logs_size_freed_mb"], 2)
    
    # 清理工作目录
    if clean_working_dir:
        if working_dir.exists():
            size_freed = 0
            count = 0
            for item in working_dir.iterdir():
                try:
                    if item.is_file():
                        size_freed += item.stat().st_size
                        item.unlink()
                        count += 1
                    elif item.is_dir():
                        size_freed += sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                        shutil.rmtree(item)
                        count += 1
                except Exception:
                    pass
            result["working_files_deleted"] = count
            result["working_size_freed_mb"] = round(size_freed / (1024**2), 2)
    
    # 清理旧结果（从数据库）
    if clean_old_results and agent and hasattr(agent, 'benchmark_executor'):
        try:
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(days=keep_results_days)
            
            import sqlite3
            db_path = data_dir / "benchmark_results.db"
            if db_path.exists():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM benchmark_results WHERE created_at < ?",
                    (cutoff.isoformat(),)
                )
                result["results_deleted"] = cursor.rowcount
                conn.commit()
                conn.close()
        except Exception:
            pass
    
    return success(result, "存储清理完成")


@bp.route('/api/storage/logs', methods=['GET'])
def list_logs():
    """
    列出日志文件
    
    GET /api/storage/logs?limit=20
    """
    data_dir = Path("/var/lib/node_agent")
    log_dir = data_dir / "logs"
    
    if not log_dir.exists():
        return success({"logs": [], "count": 0})
    
    limit = request.args.get('limit', 20, type=int)
    
    log_files = []
    for log_file in sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
        stat = log_file.stat()
        log_files.append({
            "name": log_file.name,
            "path": str(log_file),
            "size_kb": round(stat.st_size / 1024, 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    
    return success({
        "logs": log_files,
        "count": len(log_files),
        "total_count": len(list(log_dir.glob("*.log"))),
    })
