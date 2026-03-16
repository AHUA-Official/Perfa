"""
FIO 磁盘 I/O 测试运行器
"""
import re
import json
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class FioRunner(BaseRunner):
    """
    FIO 磁盘 I/O 测试运行器
    
    FIO 参数非常多，支持完整的参数扩展
    """
    
    name = "fio"
    description = "Flexible I/O Tester - disk benchmark"
    category = "disk"
    typical_duration_seconds = 600  # 10分钟
    requires_async = True

    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """准备测试环境"""
        tool = tool_manager.get_tool("fio")
        if not tool:
            return False
        
        status = tool.check()
        if status.get("status") != "installed":
            return False
        
        self.binary_path = tool.binary_path or "fio"
        return True

    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建 FIO 命令
        
        FIO 支持大量参数，这里通过 params dict 完全扩展
        """
        params = task.params or {}
        
        cmd = [self.binary_path]
        
        # 基本参数
        filename = params.get("filename")
        if filename:
            cmd.extend(["--filename", filename])
        else:
            # 默认在工作目录创建测试文件
            test_file = f"{task.working_dir}/fio_test"
            cmd.extend(["--filename", test_file])
        
        # 标准参数映射
        param_mapping = {
            "size": "--size",
            "bs": "--bs",
            "ioengine": "--ioengine",
            "iodepth": "--iodepth",
            "numjobs": "--numjobs",
            "rw": "--rw",
            "direct": "--direct",
            "runtime": "--runtime",
            "time_based": "--time_based",
            "name": "--name",
        }
        
        for key, flag in param_mapping.items():
            if key in params and params[key] is not None:
                if key == "time_based" and params[key]:
                    cmd.append(flag)
                else:
                    cmd.extend([flag, str(params[key])])
        
        # 处理额外参数 (extra_params dict)
        extra = params.get("extra_params", {})
        for key, value in extra.items():
            cmd.extend([f"--{key}", str(value)])
        
        # 必需参数
        if "--name" not in str(cmd):
            cmd.extend(["--name", "benchmark"])
        
        # 默认参数（如果用户未指定）
        if "--size" not in str(cmd):
            cmd.extend(["--size", "1G"])  # 默认 1GB 测试文件
        
        if "--ioengine" not in str(cmd):
            cmd.extend(["--ioengine", "libaio"])  # 默认异步 IO 引擎
        
        if "--rw" not in str(cmd):
            cmd.extend(["--rw", "randread"])  # 默认随机读
        
        if "--bs" not in str(cmd):
            cmd.extend(["--bs", "4k"])  # 默认 4K 块大小
        
        if "--iodepth" not in str(cmd):
            cmd.extend(["--iodepth", "32"])  # 默认 IO 深度
        
        if "--direct" not in str(cmd):
            cmd.extend(["--direct", "1"])  # 默认绕过缓存
        
        if "--runtime" not in str(cmd):
            cmd.extend(["--runtime", "60"])  # 默认运行 60 秒
        
        if "--time_based" not in str(cmd):
            cmd.append("--time_based")  # 基于时间的测试
        
        # 输出格式
        cmd.extend(["--output-format", "json"])
        
        return cmd

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 FIO JSON 输出
        """
        metrics = {
            "read_iops": None,
            "write_iops": None,
            "read_bw_mbs": None,
            "write_bw_mbs": None,
            "read_lat_us": None,
            "write_lat_us": None,
            "raw_output": output[-5000:] if len(output) > 5000 else output
        }
        
        try:
            # 从输出中提取 JSON 部分（跳过 fio 的警告/日志）
            json_start = output.find('{\n  "fio version"')
            if json_start == -1:
                json_start = output.rfind('{')
            
            if json_start != -1:
                json_str = output[json_start:]
                data = json.loads(json_str)
            else:
                data = json.loads(output)
            
            if "jobs" in data and len(data["jobs"]) > 0:
                job = data["jobs"][0]
                
                # 读取指标
                if "read" in job:
                    read = job["read"]
                    metrics["read_iops"] = round(read.get("iops", 0), 2)
                    metrics["read_bw_mbs"] = round(read.get("bw", 0) / 1024, 2) if read.get("bw") else None
                    if "lat_ns" in read and "mean" in read["lat_ns"]:
                        # lat_ns 单位是纳秒，转换为微秒
                        metrics["read_lat_us"] = round(read["lat_ns"]["mean"] / 1000, 2)
                
                # 写入指标
                if "write" in job:
                    write = job["write"]
                    if write.get("iops", 0) > 0:
                        metrics["write_iops"] = round(write.get("iops", 0), 2)
                        metrics["write_bw_mbs"] = round(write.get("bw", 0) / 1024, 2) if write.get("bw") else None
                        if "lat_ns" in write and "mean" in write["lat_ns"]:
                            metrics["write_lat_us"] = round(write["lat_ns"]["mean"] / 1000, 2)
                
                # 添加更多关键指标
                metrics["total_runtime_ms"] = job.get("job_runtime")
                metrics["cpu_utilization"] = {
                    "user": job.get("usr_cpu"),
                    "system": job.get("sys_cpu")
                }
                        
        except json.JSONDecodeError as e:
            # 记录解析错误
            metrics["parse_error"] = str(e)
        except Exception as e:
            metrics["parse_error"] = str(e)
        
        return metrics

    def get_cleanup_patterns(self) -> List[str]:
        return ["fio_test*", "*.fio", "*.tmp"]

    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """根据 runtime 设置超时"""
        runtime = params.get("runtime", 60)
        return max(runtime * 2, 300)  # 至少 5 分钟

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数"""
        errors = []
        
        rw = params.get("rw", "randread")
        valid_rw = ["read", "write", "randread", "randwrite", "rw", "randrw"]
        if rw not in valid_rw:
            errors.append(f"Invalid rw mode: {rw}, must be one of {valid_rw}")
        
        return errors
