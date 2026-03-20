#!/usr/bin/env python3
"""
Node Agent Monitor 模块测试

测试范围:
- 健康检查 API
- 系统信息采集
- 监控启停控制
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


@dataclass
class TestResult:
    name: str
    passed: bool
    message: str
    details: Optional[Dict] = None


class MonitorTester:
    """Monitor 模块测试器"""

    def __init__(self, host: str = "localhost", port: int = 8080, verbose: bool = False):
        self.base_url = f"http://{host}:{port}"
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.passed = 0
        self.failed = 0

    def log(self, msg: str, level: str = "INFO"):
        """打印日志"""
        prefix = {
            "INFO": f"{Colors.BLUE}[INFO]{Colors.NC}",
            "PASS": f"{Colors.GREEN}[PASS]{Colors.NC}",
            "FAIL": f"{Colors.RED}[FAIL]{Colors.NC}",
            "WARN": f"{Colors.YELLOW}[WARN]{Colors.NC}",
            "DATA": f"{Colors.CYAN}[DATA]{Colors.NC}",
        }.get(level, "[LOG]")
        print(f"  {prefix} {msg}")

    def request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> tuple:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=30)
            else:
                resp = requests.post(url, json=data, timeout=30)
            return resp.status_code, resp.json()
        except requests.exceptions.ConnectionError:
            return 0, {"error": "Connection refused"}
        except Exception as e:
            return 0, {"error": str(e)}

    def record(self, result: TestResult):
        """记录结果"""
        self.results.append(result)
        if result.passed:
            self.passed += 1
            self.log(f"{result.name}: {result.message}", "PASS")
        else:
            self.failed += 1
            self.log(f"{result.name}: {result.message}", "FAIL")
        if result.details and self.verbose:
            print(f"    {Colors.CYAN}Details:{Colors.NC} {json.dumps(result.details, indent=2, ensure_ascii=False)}")

    # ==================== 测试用例 ====================

    def test_health_check(self):
        """测试健康检查接口"""
        print(f"\n{'='*60}")
        print("TEST: 健康检查")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/health")

        self.log(f"请求 GET /health", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("健康检查", False, f"HTTP {status_code}", data))
            return

        # 验证响应格式
        if not data.get("success"):
            self.record(TestResult("健康检查", False, "响应 success 不为 true", data))
            return

        resp_data = data.get("data", {})
        if resp_data.get("status") != "healthy":
            self.record(TestResult("健康检查", False, f"状态不为 healthy: {resp_data.get('status')}", data))
            return

        uptime = resp_data.get("uptime_seconds", 0)
        self.log(f"服务运行时间: {uptime} 秒", "DATA")

        self.record(TestResult("健康检查", True, f"服务健康，运行 {uptime} 秒", {"uptime": uptime}))

    def test_agent_status(self):
        """测试 Agent 状态接口"""
        print(f"\n{'='*60}")
        print("TEST: Agent 状态")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/status")

        self.log(f"请求 GET /api/status", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("Agent状态", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        # 验证必要字段
        required_fields = ["agent_id", "uptime_seconds", "monitor_running", "version"]
        missing = [f for f in required_fields if f not in resp_data]

        if missing:
            self.record(TestResult("Agent状态", False, f"缺少字段: {missing}", data))
            return

        self.log(f"Agent ID: {resp_data.get('agent_id')}", "DATA")
        self.log(f"版本: {resp_data.get('version')}", "DATA")
        self.log(f"监控运行中: {resp_data.get('monitor_running')}", "DATA")
        self.log(f"运行时间: {resp_data.get('uptime_seconds')} 秒", "DATA")

        current_task = resp_data.get("current_task")
        if current_task:
            self.log(f"当前任务: {current_task.get('task_id')} ({current_task.get('status')})", "DATA")

        self.record(TestResult("Agent状态", True, 
                               f"Agent {resp_data.get('agent_id')} v{resp_data.get('version')}",
                               resp_data))

    def test_system_info(self):
        """测试系统信息采集"""
        print(f"\n{'='*60}")
        print("TEST: 系统静态信息")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/system/info")

        self.log(f"请求 GET /api/system/info", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("系统信息", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        system = resp_data.get("system", {})

        # 验证必要字段
        required_fields = ["hostname", "os", "arch", "cpu_model", "cpu_cores", "memory_total_gb"]
        missing = [f for f in required_fields if f not in system]

        if missing:
            self.record(TestResult("系统信息", False, f"缺少字段: {missing}", data))
            return

        # 验证字段值有效性
        cpu_cores = system.get("cpu_cores")
        try:
            cpu_cores = int(cpu_cores) if cpu_cores else 0
        except (ValueError, TypeError):
            cpu_cores = 0

        if cpu_cores <= 0:
            self.record(TestResult("系统信息", False, f"CPU 核心数无效: {system.get('cpu_cores')}", data))
            return

        memory_total = system.get("memory_total_gb")
        try:
            memory_total = float(memory_total) if memory_total else 0
        except (ValueError, TypeError):
            memory_total = 0

        if memory_total <= 0:
            self.record(TestResult("系统信息", False, f"内存大小无效: {system.get('memory_total_gb')}", data))
            return

        self.log(f"主机名: {system.get('hostname')}", "DATA")
        self.log(f"操作系统: {system.get('os')}", "DATA")
        self.log(f"架构: {system.get('arch')}", "DATA")
        self.log(f"CPU: {system.get('cpu_model')} ({system.get('cpu_cores')} 核)", "DATA")
        self.log(f"内存: {system.get('memory_total_gb')} GB", "DATA")
        self.log(f"内核: {system.get('kernel')}", "DATA")

        self.record(TestResult("系统信息", True,
                               f"{system.get('hostname')} - {system.get('cpu_model')}",
                               system))

    def test_system_status(self):
        """测试系统实时状态"""
        print(f"\n{'='*60}")
        print("TEST: 系统实时状态")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/system/status")

        self.log(f"请求 GET /api/system/status", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("系统状态", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        # 验证各模块数据
        cpu = resp_data.get("cpu", {})
        memory = resp_data.get("memory", {})
        disk = resp_data.get("disk", {})

        if not cpu:
            self.record(TestResult("系统状态", False, "缺少 CPU 数据", data))
            return

        if not memory:
            self.record(TestResult("系统状态", False, "缺少内存数据", data))
            return

        if not disk:
            self.record(TestResult("系统状态", False, "缺少磁盘数据", data))
            return

        # 验证数值合理性
        cpu_percent = cpu.get("percent", -1)
        if not (0 <= cpu_percent <= 100):
            self.record(TestResult("系统状态", False, f"CPU 使用率无效: {cpu_percent}", data))
            return

        mem_percent = memory.get("percent", -1)
        if not (0 <= mem_percent <= 100):
            self.record(TestResult("系统状态", False, f"内存使用率无效: {mem_percent}", data))
            return

        self.log(f"CPU 使用率: {cpu_percent}%", "DATA")
        self.log(f"CPU 频率: {cpu.get('freq_mhz')} MHz", "DATA")
        self.log(f"内存使用: {memory.get('used_gb')}/{memory.get('total_gb')} GB ({mem_percent}%)", "DATA")
        self.log(f"磁盘使用: {disk.get('used_gb')}/{disk.get('total_gb')} GB ({disk.get('percent')}%)", "DATA")
        self.log(f"系统负载: {resp_data.get('load_average', {})}", "DATA")

        self.record(TestResult("系统状态", True,
                               f"CPU {cpu_percent}%, 内存 {mem_percent}%",
                               resp_data))

    def test_monitor_control(self):
        """测试监控启停控制"""
        print(f"\n{'='*60}")
        print("TEST: 监控启停控制")
        print(f"{'='*60}")

        # 1. 获取当前状态
        self.log("步骤 1: 获取当前监控状态", "INFO")
        status_code, data = self.request("GET", "/api/monitor/status")

        if status_code != 200:
            self.record(TestResult("监控控制", False, f"获取状态失败: HTTP {status_code}", data))
            return

        current_running = data.get("data", {}).get("running", False)
        self.log(f"当前监控状态: {'运行中' if current_running else '已停止'}", "DATA")

        # 2. 如果监控在运行，先停止
        if current_running:
            self.log("步骤 2: 监控已在运行，先停止", "INFO")
            status_code, data = self.request("POST", "/api/monitor/stop")

            if status_code != 200:
                self.record(TestResult("监控控制", False, f"停止监控失败: HTTP {status_code}", data))
                return

            self.log("监控已停止", "DATA")
            time.sleep(1)

        # 3. 启动监控
        self.log("步骤 3: 启动监控", "INFO")
        status_code, data = self.request("POST", "/api/monitor/start",
                                          {"interval": 5, "enabled_metrics": ["cpu", "memory"]})

        if status_code != 200:
            self.record(TestResult("监控控制", False, f"启动监控失败: HTTP {status_code}", data))
            return

        # 验证返回的数据
        resp_data = data.get("data", {})
        if not resp_data.get("running"):
            self.record(TestResult("监控控制", False, "启动后 running 不为 true", data))
            return

        interval = resp_data.get("interval")
        metrics = resp_data.get("enabled_metrics")

        self.log(f"监控已启动: 间隔 {interval} 秒, 指标 {metrics}", "DATA")

        # 4. 验证状态
        self.log("步骤 4: 验证监控已启动", "INFO")
        status_code, data = self.request("GET", "/api/monitor/status")

        if status_code != 200:
            self.record(TestResult("监控控制", False, f"查询状态失败: HTTP {status_code}", data))
            return

        if not data.get("data", {}).get("running"):
            self.record(TestResult("监控控制", False, "状态查询显示监控未运行", data))
            return

        self.log("状态验证通过: 监控正在运行", "DATA")

        # 5. 测试重复启动（应该失败）
        self.log("步骤 5: 测试重复启动（预期失败）", "INFO")
        status_code, data = self.request("POST", "/api/monitor/start")

        if status_code != 409:
            self.record(TestResult("监控控制", False, f"重复启动应返回 409，实际: {status_code}", data))
            return

        self.log(f"重复启动正确返回 409: {data.get('error', {}).get('code')}", "DATA")

        # 6. 停止监控
        self.log("步骤 6: 停止监控", "INFO")
        status_code, data = self.request("POST", "/api/monitor/stop")

        if status_code != 200:
            self.record(TestResult("监控控制", False, f"停止监控失败: HTTP {status_code}", data))
            return

        self.log("监控已停止", "DATA")

        # 7. 验证停止状态
        self.log("步骤 7: 验证监控已停止", "INFO")
        status_code, data = self.request("GET", "/api/monitor/status")

        if data.get("data", {}).get("running"):
            self.record(TestResult("监控控制", False, "停止后状态仍显示运行中", data))
            return

        # 8. 测试重复停止（应该失败）
        self.log("步骤 8: 测试重复停止（预期失败）", "INFO")
        status_code, data = self.request("POST", "/api/monitor/stop")

        if status_code != 400:
            self.record(TestResult("监控控制", False, f"重复停止应返回 400，实际: {status_code}", data))
            return

        self.log(f"重复停止正确返回 400: {data.get('error', {}).get('code')}", "DATA")

        self.record(TestResult("监控控制", True, "启停流程全部正确", {"interval": interval, "metrics": metrics}))

    def run_all(self):
        """运行所有测试"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}    Node Agent Monitor 模块测试{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

        # 检查服务
        print(f"\n检查服务可用性...", end=" ")
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            if resp.status_code == 200:
                print(f"{Colors.GREEN}✓ 服务运行中{Colors.NC}")
            else:
                print(f"{Colors.RED}✗ 服务异常{Colors.NC}")
                sys.exit(1)
        except:
            print(f"{Colors.RED}✗ 无法连接服务{Colors.NC}")
            sys.exit(1)

        # 运行测试
        self.test_health_check()
        self.test_agent_status()
        self.test_system_info()
        self.test_system_status()
        self.test_monitor_control()

        # 输出总结
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}    测试总结{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.GREEN}通过: {self.passed}{Colors.NC}")
        print(f"{Colors.RED}失败: {self.failed}{Colors.NC}")

        if self.failed == 0:
            print(f"\n{Colors.GREEN}所有测试通过!{Colors.NC}")
            sys.exit(0)
        else:
            print(f"\n{Colors.RED}存在失败的测试{Colors.NC}")
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Monitor 模块测试")
    parser.add_argument("--host", default="localhost", help="服务地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    tester = MonitorTester(host=args.host, port=args.port, verbose=args.verbose)
    tester.run_all()


if __name__ == "__main__":
    main()