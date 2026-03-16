"""Benchmark 压测管理工具"""
from typing import Dict, Any, Optional
from datetime import datetime
from .base import BaseTool
from storage import Database
from agent_client import AgentClient


class RunBenchmarkTool(BaseTool):
    """执行压测任务"""
    
    name = "run_benchmark"
    description = """在目标服务器上执行压测任务。

支持的测试及其参数：
- unixbench: CPU综合性能测试，参数：{single: true/false, multi: true/false}
- stream: 内存带宽测试，参数：{array_size: 100000000, ntimes: 10, nt: 4}
- fio: 磁盘IO测试，参数：{rw: "randread", bs: "4k", size: "1G", iodepth: 32, numjobs: 1}
- superpi: CPU浮点测试，参数：{digits: 1048576}
- mlc: Intel内存延迟测试，参数：{}
- hping3: 网络测试，参数：{target: "192.168.1.1", count: 10, interval: 1}
"""
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID（通过 list_servers 查询）"
            },
            "test_name": {
                "type": "string",
                "description": "测试名称",
                "enum": ["unixbench", "stream", "fio", "superpi", "mlc", "hping3"]
            },
            "params": {
                "type": "object",
                "description": "测试参数（可选，不同工具有不同参数，不传则使用默认值）",
                "properties": {
                    # UnixBench 参数
                    "single": {
                        "type": "boolean",
                        "description": "[unixbench] 是否运行单核测试"
                    },
                    "multi": {
                        "type": "boolean",
                        "description": "[unixbench] 是否运行多核测试"
                    },
                    # STREAM 参数
                    "array_size": {
                        "type": "integer",
                        "description": "[stream] 数组大小，默认 100000000"
                    },
                    "ntimes": {
                        "type": "integer",
                        "description": "[stream] 迭代次数，默认 10"
                    },
                    "nt": {
                        "type": "integer",
                        "description": "[stream] 并行线程数，默认自动检测"
                    },
                    # FIO 参数
                    "rw": {
                        "type": "string",
                        "description": "[fio] 读写模式: read, write, randread, randwrite, randrw",
                        "enum": ["read", "write", "randread", "randwrite", "randrw"]
                    },
                    "bs": {
                        "type": "string",
                        "description": "[fio] 块大小，如 4k, 8k, 64k, 1m"
                    },
                    "size": {
                        "type": "string",
                        "description": "[fio 必填] 测试文件大小，如 1G, 10G"
                    },
                    "iodepth": {
                        "type": "integer",
                        "description": "[fio] IO队列深度，默认 32"
                    },
                    "numjobs": {
                        "type": "integer",
                        "description": "[fio] 并行任务数，默认 1"
                    },
                    "filename": {
                        "type": "string",
                        "description": "[fio] 测试文件路径（可选）"
                    },
                    # SuperPi 参数
                    "digits": {
                        "type": "integer",
                        "description": "[superpi] 计算精度（小数位数），如 1048576"
                    },
                    # hping3 参数
                    "target": {
                        "type": "string",
                        "description": "[hping3] 目标 IP 地址"
                    },
                    "count": {
                        "type": "integer",
                        "description": "[hping3] 发送次数"
                    },
                    "interval": {
                        "type": "number",
                        "description": "[hping3] 发送间隔（秒）"
                    }
                }
            }
        },
        "required": ["server_id", "test_name"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, test_name: str, 
                params: Optional[dict] = None, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/benchmark/run API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent，请先部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            # 检查 Agent 是否在线
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            # 检查是否有任务在运行
            current_task = client.get_current_task()
            if current_task:
                return {
                    "success": False,
                    "error": "Agent 正在执行任务",
                    "current_task": current_task
                }
            
            # 执行压测
            task_id = client.run_benchmark(test_name, params or {})
            
            return {
                "success": True,
                "task_id": task_id,
                "test_name": test_name,
                "status": "started",
                "message": "压测任务已启动",
                "params": params
            }
            
        except Exception as e:
            error_msg = str(e)
            if "not installed" in error_msg.lower():
                return {
                    "success": False,
                    "error": f"工具 {test_name} 未安装，请先调用 install_tool 安装"
                }
            return {"success": False, "error": f"执行失败: {error_msg}"}


class GetBenchmarkStatusTool(BaseTool):
    """查询压测任务状态"""
    
    name = "get_benchmark_status"
    description = "查询压测任务的执行状态和进度"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "task_id": {
                "type": "string",
                "description": "任务 ID"
            }
        },
        "required": ["server_id", "task_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, task_id: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/benchmark/tasks/<task_id> API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            status = client.get_benchmark_status(task_id)
            
            return {
                "success": True,
                "task_id": task_id,
                **status
            }
            
        except Exception as e:
            return {"success": False, "error": f"查询状态失败: {str(e)}"}


class CancelBenchmarkTool(BaseTool):
    """取消压测任务"""
    
    name = "cancel_benchmark"
    description = "取消正在运行的压测任务"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "task_id": {
                "type": "string",
                "description": "任务 ID"
            }
        },
        "required": ["server_id", "task_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, task_id: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/benchmark/cancel API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            success = client.cancel_benchmark(task_id)
            
            if success:
                return {
                    "success": True,
                    "task_id": task_id,
                    "status": "cancelled",
                    "message": "任务已取消"
                }
            else:
                return {
                    "success": False,
                    "error": "无法取消任务（可能已完成或不存在）"
                }
            
        except Exception as e:
            return {"success": False, "error": f"取消失败: {str(e)}"}


class GetBenchmarkResultTool(BaseTool):
    """获取压测结果"""
    
    name = "get_benchmark_result"
    description = "获取压测任务的详细结果和指标"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "task_id": {
                "type": "string",
                "description": "任务 ID"
            }
        },
        "required": ["server_id", "task_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, task_id: str, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/benchmark/results/<task_id> API 并获取完整日志"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            result = client.get_benchmark_result(task_id)
            
            response = {
                "success": True,
                "task_id": result.task_id,
                "test_name": result.test_name,
                "status": result.status,
                "duration_seconds": result.duration_seconds,
                "metrics": result.metrics,
                "log_file": result.log_file,
                "error": result.error
            }
            
            # 如果有日志文件，获取完整日志内容
            if result.log_file:
                try:
                    import os
                    # log_file 可能是完整路径或文件名
                    log_name = os.path.basename(result.log_file)
                    log_content = client._request("GET", f"/api/storage/logs/{log_name}", params={"lines": 5000})
                    response["log_content"] = log_content.get("content", "")
                    response["log_total_lines"] = log_content.get("total_lines", 0)
                except Exception as e:
                    response["log_content_error"] = f"获取日志内容失败: {str(e)}"
            
            return response
            
        except Exception as e:
            return {"success": False, "error": f"获取结果失败: {str(e)}"}


class ListBenchmarkHistoryTool(BaseTool):
    """列出历史测试记录"""
    
    name = "list_benchmark_history"
    description = "列出目标服务器上的历史压测记录"
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID"
            },
            "test_name": {
                "type": "string",
                "description": "按测试名称筛选（可选）",
                "enum": ["unixbench", "stream", "fio", "superpi", "mlc", "hping3"]
            },
            "limit": {
                "type": "integer",
                "description": "返回记录数量限制",
                "default": 20
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, test_name: Optional[str] = None,
                limit: int = 20, **kwargs) -> Dict[str, Any]:
        """调用 Agent /api/benchmark/results API"""
        server = self.db.get_server(server_id)
        if not server:
            return {"success": False, "error": f"服务器 {server_id} 不存在"}
        
        if not server.agent_id:
            return {"success": False, "error": "该服务器未部署 Agent"}
        
        try:
            client = AgentClient(f"http://{server.ip}:{server.agent_port}", timeout=30)
            
            if not client.health_check():
                return {"success": False, "error": "Agent 离线"}
            
            results = client.list_benchmark_results(test_name=test_name, limit=limit)
            
            return {
                "success": True,
                "server_id": server_id,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            return {"success": False, "error": f"获取历史记录失败: {str(e)}"}
