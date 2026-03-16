"""智能分析报告工具"""
from typing import Dict, Any, Optional, List
from .base import BaseTool
from storage import Database
from agent_client import AgentClient
import requests


class GenerateReportTool(BaseTool):
    """生成压测分析报告"""
    
    name = "generate_report"
    description = """生成压测分析报告，整合测试结果、监控数据和性能分析。

功能包括：
- 从 Agent 获取压测结果
- 从 Victoria Metrics 查询监控数据
- 生成结构化的性能分析报告

适用场景：
- 单次压测后的结果分析
- 多次压测的对比分析
- 性能问题的诊断建议
"""
    input_schema = {
        "type": "object",
        "properties": {
            "server_id": {
                "type": "string",
                "description": "服务器 ID（通过 list_servers 查询）"
            },
            "task_id": {
                "type": "string",
                "description": "压测任务 ID（可选，不传则使用最近一次测试）"
            },
            "report_type": {
                "type": "string",
                "description": "报告类型",
                "enum": ["single", "comparison", "diagnosis"],
                "default": "single"
            },
            "compare_task_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "[comparison] 对比的任务 ID 列表"
            },
            "include_metrics": {
                "type": "boolean",
                "description": "是否包含详细监控指标",
                "default": True
            }
        },
        "required": ["server_id"]
    }
    
    def __init__(self, db: Database):
        self.db = db
    
    def execute(self, server_id: str, task_id: Optional[str] = None,
                report_type: str = "single", compare_task_ids: Optional[List[str]] = None,
                include_metrics: bool = True) -> Dict[str, Any]:
        """生成报告"""
        
        # 1. 获取服务器信息
        server = self.db.get_server(server_id)
        if not server:
            return {"error": f"Server {server_id} not found"}
        
        agent_id = server.agent_id
        if not agent_id:
            return {"error": "Agent not deployed on this server"}
        
        # 2. 创建 Agent 客户端
        agent_port = server.agent_port or 8080
        agent_url = f"http://{server.ip}:{agent_port}"
        agent_client = AgentClient(agent_url)
        
        # 3. 检查 Agent 状态
        try:
            if not agent_client.health_check():
                return {"error": "Agent is not healthy"}
        except Exception as e:
            return {"error": f"Agent unreachable: {str(e)}"}
        
        # 4. 根据报告类型生成
        if report_type == "single":
            return self._generate_single_report(agent_client, agent_id, task_id, include_metrics)
        elif report_type == "comparison":
            return self._generate_comparison_report(agent_client, agent_id, compare_task_ids, include_metrics)
        elif report_type == "diagnosis":
            return self._generate_diagnosis_report(agent_client, agent_id, task_id)
        else:
            return {"error": f"Unknown report type: {report_type}"}
    
    def _generate_single_report(self, agent_client: AgentClient, agent_id: str,
                                  task_id: Optional[str], include_metrics: bool) -> Dict[str, Any]:
        """生成单次测试报告"""
        
        # 获取任务 ID
        if not task_id:
            # 获取最近一次完成的测试
            results = agent_client.list_benchmark_results(limit=1)
            if not results:
                return {"error": "No benchmark results found"}
            task_id = results[0].get("task_id") if isinstance(results[0], dict) else results[0].task_id
        
        # 获取测试结果
        result = agent_client.get_benchmark_result(task_id)
        if not result:
            return {"error": f"Task {task_id} not found"}
        
        test_name = result.test_name
        
        # 构建报告
        report = {
            "report_type": "single",
            "task_id": task_id,
            "test_name": test_name,
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "server_info": {},  # system_info 需要单独获取
            "results": result.metrics or {},
            "summary": self._generate_summary(test_name, result),
            "analysis": self._analyze_result(test_name, result),
        }
        
        # 添加日志路径
        if result.log_file:
            report["log_path"] = result.log_file
        
        return report
    
    def _generate_comparison_report(self, agent_client: AgentClient, agent_id: str,
                                      task_ids: Optional[List[str]], include_metrics: bool) -> Dict[str, Any]:
        """生成对比报告"""
        
        if not task_ids or len(task_ids) < 2:
            # 获取最近两次测试
            results_list = agent_client.list_benchmark_results(limit=2)
            if len(results_list) < 2:
                return {"error": "Need at least 2 benchmark results for comparison"}
            task_ids = [r.get("task_id") if isinstance(r, dict) else r.task_id for r in results_list]
        
        # 获取所有测试结果
        results = []
        for tid in task_ids:
            result = agent_client.get_benchmark_result(tid)
            if result:
                results.append(result)
        
        if len(results) < 2:
            return {"error": "Could not fetch enough results for comparison"}
        
        # 构建对比报告
        report = {
            "report_type": "comparison",
            "task_ids": task_ids,
            "comparison": []
        }
        
        # 对比每个结果
        baseline = results[0]
        for i, result in enumerate(results):
            entry = {
                "task_id": result.task_id,
                "test_name": result.test_name,
                "duration_seconds": result.duration_seconds,
                "results": result.metrics or {},
                "summary": self._generate_summary(result.test_name, result)
            }
            
            # 计算与基准的差异
            if i > 0:
                entry["diff_from_baseline"] = self._calculate_diff(
                    baseline.metrics or {},
                    result.metrics or {}
                )
            
            report["comparison"].append(entry)
        
        # 添加对比分析
        report["analysis"] = self._compare_results(results)
        
        return report
    
    def _generate_diagnosis_report(self, agent_client: AgentClient, agent_id: str,
                                     task_id: Optional[str]) -> Dict[str, Any]:
        """生成诊断报告"""
        
        # 先获取基础报告
        base_report = self._generate_single_report(agent_client, agent_id, task_id, True)
        if "error" in base_report:
            return base_report
        
        # 添加诊断分析
        diagnosis = {
            "report_type": "diagnosis",
            "task_id": base_report["task_id"],
            "test_name": base_report["test_name"],
            "results": base_report["results"],
            "metrics": base_report.get("metrics", {}),
            "issues": self._identify_issues(base_report),
            "recommendations": self._generate_recommendations(base_report)
        }
        
        return diagnosis
    
    def _generate_summary(self, test_name: str, result) -> Dict[str, Any]:
        """生成结果摘要"""
        results = result.metrics or {}
        summary = {}
        
        if test_name == "unixbench":
            summary = {
                "single_core_score": results.get("single_core_score"),
                "multi_core_score": results.get("multi_core_score"),
                "parallelism": results.get("parallelism")
            }
        elif test_name == "stream":
            summary = {
                "copy_bandwidth_gb_s": results.get("copy_bandwidth_gb_s"),
                "scale_bandwidth_gb_s": results.get("scale_bandwidth_gb_s"),
                "add_bandwidth_gb_s": results.get("add_bandwidth_gb_s"),
                "triad_bandwidth_gb_s": results.get("triad_bandwidth_gb_s")
            }
        elif test_name == "fio":
            summary = {
                "read_iops": results.get("read_iops"),
                "write_iops": results.get("write_iops"),
                "read_bw_mb_s": results.get("read_bw_mb_s"),
                "write_bw_mb_s": results.get("write_bw_mb_s"),
                "read_lat_us": results.get("read_lat_us"),
                "write_lat_us": results.get("write_lat_us")
            }
        elif test_name == "superpi":
            summary = {
                "digits": results.get("digits"),
                "time_seconds": results.get("time_seconds")
            }
        elif test_name == "mlc":
            summary = {
                "latency_ns": results.get("latency_ns"),
                "bandwidth_gb_s": results.get("bandwidth_gb_s")
            }
        elif test_name == "hping3":
            summary = {
                "min_rtt_ms": results.get("min_rtt_ms"),
                "avg_rtt_ms": results.get("avg_rtt_ms"),
                "max_rtt_ms": results.get("max_rtt_ms"),
                "packet_loss_percent": results.get("packet_loss_percent")
            }
        
        return summary
    
    def _analyze_result(self, test_name: str, result) -> Dict[str, Any]:
        """分析测试结果"""
        results = result.metrics or {}
        analysis = {
            "performance_level": "unknown",
            "bottlenecks": [],
            "notes": []
        }
        
        # 简单的性能评估逻辑
        if test_name == "unixbench":
            score = results.get("multi_core_score", 0)
            if score > 2000:
                analysis["performance_level"] = "excellent"
            elif score > 1000:
                analysis["performance_level"] = "good"
            else:
                analysis["performance_level"] = "fair"
            analysis["notes"].append(f"Multi-core score: {score}")
            
        elif test_name == "stream":
            bandwidth = results.get("copy_bandwidth_gb_s", 0)
            if bandwidth > 50:
                analysis["performance_level"] = "excellent"
            elif bandwidth > 20:
                analysis["performance_level"] = "good"
            else:
                analysis["performance_level"] = "fair"
                analysis["bottlenecks"].append("Memory bandwidth may be a bottleneck")
            
        elif test_name == "fio":
            iops = results.get("read_iops", 0) + results.get("write_iops", 0)
            lat = results.get("read_lat_us", 0)
            if iops > 100000 and lat < 100:
                analysis["performance_level"] = "excellent"
            elif iops > 50000:
                analysis["performance_level"] = "good"
            else:
                analysis["performance_level"] = "fair"
            if lat > 1000:
                analysis["bottlenecks"].append("High I/O latency detected")
        
        return analysis
    
    def _fetch_vm_metrics(self, agent_id: str, start_time: Optional[str],
                           end_time: Optional[str]) -> Dict[str, Any]:
        """从 Victoria Metrics 获取监控数据"""
        
        # TODO: 配置 VM 地址
        vm_url = "http://localhost:8428"
        metrics = {}
        
        try:
            # 查询 CPU 使用率
            cpu_query = 'avg_over_time(cpu_usage_percent{agent_id="' + agent_id + '"}[5m])'
            if start_time and end_time:
                cpu_query = f'avg_over_time(cpu_usage_percent{{agent_id="{agent_id}"}}[{start_time}:{end_time}])'
            
            resp = requests.get(f"{vm_url}/api/v1/query", params={"query": cpu_query}, timeout=5)
            if resp.ok:
                metrics["cpu_usage_avg"] = resp.json().get("data", {}).get("result", [])
            
            # 查询内存使用率
            mem_query = f'avg_over_time(memory_usage_percent{{agent_id="{agent_id}"}}[5m])'
            resp = requests.get(f"{vm_url}/api/v1/query", params={"query": mem_query}, timeout=5)
            if resp.ok:
                metrics["memory_usage_avg"] = resp.json().get("data", {}).get("result", [])
            
            # 查询磁盘 I/O
            io_query = f'sum_over_time(disk_io_bytes{{agent_id="{agent_id}"}}[5m])'
            resp = requests.get(f"{vm_url}/api/v1/query", params={"query": io_query}, timeout=5)
            if resp.ok:
                metrics["disk_io_total"] = resp.json().get("data", {}).get("result", [])
                
        except Exception as e:
            metrics["error"] = f"Failed to fetch VM metrics: {str(e)}"
        
        return metrics
    
    def _calculate_diff(self, baseline: Dict, current: Dict) -> Dict[str, Any]:
        """计算与基准的差异"""
        diff = {}
        
        for key in baseline:
            if key in current:
                base_val = baseline[key]
                curr_val = current[key]
                
                if isinstance(base_val, (int, float)) and isinstance(curr_val, (int, float)):
                    if base_val != 0:
                        change_pct = ((curr_val - base_val) / base_val) * 100
                        diff[key] = {
                            "baseline": base_val,
                            "current": curr_val,
                            "change_percent": round(change_pct, 2)
                        }
        
        return diff
    
    def _compare_results(self, results: List) -> Dict[str, Any]:
        """对比多个结果"""
        analysis = {
            "trend": "stable",
            "best_performer": None,
            "worst_performer": None,
            "notes": []
        }
        
        # 简单的趋势分析
        scores = []
        for r in results:
            test_name = r.test_name
            res = r.metrics or {}
            
            if test_name == "unixbench":
                scores.append(res.get("multi_core_score", 0))
            elif test_name == "stream":
                scores.append(res.get("copy_bandwidth_gb_s", 0))
            elif test_name == "fio":
                scores.append(res.get("read_iops", 0) + res.get("write_iops", 0))
        
        if len(scores) >= 2:
            if scores[0] > scores[-1]:
                analysis["trend"] = "declining"
            elif scores[0] < scores[-1]:
                analysis["trend"] = "improving"
            
            best_idx = scores.index(max(scores))
            worst_idx = scores.index(min(scores))
            analysis["best_performer"] = results[best_idx].task_id
            analysis["worst_performer"] = results[worst_idx].task_id
        
        return analysis
    
    def _identify_issues(self, report: Dict) -> List[Dict[str, Any]]:
        """识别性能问题"""
        issues = []
        
        # 检查 CPU 使用率
        metrics = report.get("metrics", {})
        cpu_data = metrics.get("cpu_usage_avg", [])
        if cpu_data:
            avg_cpu = sum(float(v.get("value", [0, 0])[1]) for v in cpu_data) / len(cpu_data)
            if avg_cpu > 90:
                issues.append({
                    "type": "cpu_saturation",
                    "severity": "high",
                    "description": f"CPU usage averaged {avg_cpu:.1f}% during test"
                })
        
        # 检查内存
        mem_data = metrics.get("memory_usage_avg", [])
        if mem_data:
            avg_mem = sum(float(v.get("value", [0, 0])[1]) for v in mem_data) / len(mem_data)
            if avg_mem > 85:
                issues.append({
                    "type": "memory_pressure",
                    "severity": "medium",
                    "description": f"Memory usage averaged {avg_mem:.1f}% during test"
                })
        
        # 检查测试结果中的异常
        analysis = report.get("analysis", {})
        for bottleneck in analysis.get("bottlenecks", []):
            issues.append({
                "type": "performance_bottleneck",
                "severity": "medium",
                "description": bottleneck
            })
        
        return issues
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        test_name = report.get("test_name", "")
        results = report.get("results", {})
        issues = report.get("issues", [])
        
        # 基于测试类型给出建议
        if test_name == "unixbench":
            score = results.get("multi_core_score", 0)
            if score < 1000:
                recommendations.append("Consider CPU upgrade or check for thermal throttling")
        
        elif test_name == "stream":
            bandwidth = results.get("copy_bandwidth_gb_s", 0)
            if bandwidth < 20:
                recommendations.append("Check memory configuration (channels, frequency)")
                recommendations.append("Consider NUMA optimization if applicable")
        
        elif test_name == "fio":
            iops = results.get("read_iops", 0) + results.get("write_iops", 0)
            lat = results.get("read_lat_us", 0)
            if lat > 1000:
                recommendations.append("High latency detected - check storage device health")
                recommendations.append("Consider using SSDs or NVMe for better performance")
            if iops < 10000:
                recommendations.append("Low IOPS - check if using rotational disks")
        
        # 基于问题给出建议
        for issue in issues:
            if issue["type"] == "cpu_saturation":
                recommendations.append("CPU was saturated - consider reducing parallelism or upgrading CPU")
            elif issue["type"] == "memory_pressure":
                recommendations.append("Memory was under pressure - consider increasing RAM or optimizing memory usage")
        
        return recommendations
