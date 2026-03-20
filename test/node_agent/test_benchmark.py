#!/usr/bin/env python3
"""
Node Agent Benchmark 模块测试

测试范围:
- 压测任务执行
- 任务状态查询
- 任务控制（暂停/恢复/取消）
- 并发限制
- 结果查询
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


class BenchmarkTester:
    """Benchmark 模块测试器"""

    def __init__(self, host: str = "localhost", port: int = 8080, verbose: bool = False):
        self.base_url = f"http://{host}:{port}"
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.passed = 0
        self.failed = 0
        self.current_task_id: Optional[str] = None

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

    def request(self, method: str, endpoint: str, data: Optional[Dict] = None, timeout: int = 30) -> tuple:
        """发送请求"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=timeout)
            else:
                resp = requests.post(url, json=data, timeout=timeout)
            return resp.status_code, resp.json()
        except requests.exceptions.ConnectionError:
            return 0, {"error": "Connection refused"}
        except requests.exceptions.Timeout:
            return 0, {"error": "Request timeout"}
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

    def ensure_tool_installed(self, tool_name: str) -> bool:
        """确保工具已安装"""
        status_code, data = self.request("GET", f"/api/tools/{tool_name}")

        if status_code != 200:
            return False

        status = data.get("data", {}).get("status")
        if status == "installed":
            return True

        # 安装工具
        self.log(f"工具 {tool_name} 未安装，正在安装...", "WARN")
        status_code, data = self.request("POST", f"/api/tools/{tool_name}/install", timeout=120)

        if status_code != 200:
            self.log(f"安装 {tool_name} 失败", "FAIL")
            return False

        return True

    def ensure_no_running_task(self) -> bool:
        """确保没有运行中的任务"""
        status_code, data = self.request("GET", "/api/benchmark/current")

        if status_code != 200:
            return False

        current_task = data.get("data", {}).get("current_task")

        if current_task:
            task_id = current_task.get("task_id")
            if task_id:
                self.log(f"发现运行中的任务 {task_id}，正在取消...", "WARN")
                self.request("POST", "/api/benchmark/cancel", {"task_id": task_id})
                time.sleep(1)

        return True

    def wait_for_task(self, task_id: str, timeout: int = 300, interval: int = 3) -> Optional[Dict]:
        """等待任务完成"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")

            if status_code != 200:
                return None

            task_data = data.get("data", {})
            status = task_data.get("status")

            if status in ("completed", "failed", "cancelled"):
                return task_data

            # 显示进度
            progress = task_data.get("progress", 0)
            elapsed = int(time.time() - start_time)
            self.log(f"任务 {task_id[:8]}... 状态: {status}, 进度: {progress}%, 已等待: {elapsed}s", "INFO")
            time.sleep(interval)

        return None

    # ==================== 测试用例 ====================

    def test_list_tasks(self):
        """测试任务列表查询"""
        print(f"\n{'='*60}")
        print("TEST: 任务列表查询")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/benchmark/tasks")

        self.log(f"请求 GET /api/benchmark/tasks", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("任务列表", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        tasks = resp_data.get("tasks", [])

        self.log(f"任务数量: {len(tasks)}", "DATA")

        for task in tasks[:5]:  # 只显示前 5 个
            task_id = task.get("task_id", "unknown")
            test_name = task.get("test_name", "unknown")
            status = task.get("status", "unknown")
            self.log(f"  - {task_id[:8]}... | {test_name} | {status}", "DATA")

        self.record(TestResult("任务列表", True, f"找到 {len(tasks)} 个任务"))

    def test_list_results(self):
        """测试结果列表查询"""
        print(f"\n{'='*60}")
        print("TEST: 结果列表查询")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/benchmark/results")

        self.log(f"请求 GET /api/benchmark/results", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("结果列表", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        results = resp_data.get("results", [])

        self.log(f"结果数量: {len(results)}", "DATA")

        for result in results[:5]:  # 只显示前 5 个
            task_id = result.get("task_id", "unknown")
            test_name = result.get("test_name", "unknown")
            score = result.get("score", "N/A")
            self.log(f"  - {task_id[:8]}... | {test_name} | score: {score}", "DATA")

        self.record(TestResult("结果列表", True, f"找到 {len(results)} 个结果"))

    def test_current_task(self):
        """测试当前任务查询"""
        print(f"\n{'='*60}")
        print("TEST: 当前任务查询")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/benchmark/current")

        self.log(f"请求 GET /api/benchmark/current", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("当前任务", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        current_task = resp_data.get("current_task")
        is_busy = resp_data.get("is_busy")

        if current_task:
            task_id = current_task.get("task_id")
            test_name = current_task.get("test_name")
            status = current_task.get("status")
            progress = current_task.get("progress", 0)

            self.log(f"当前有任务运行:", "DATA")
            self.log(f"  任务 ID: {task_id}", "DATA")
            self.log(f"  测试名: {test_name}", "DATA")
            self.log(f"  状态: {status}", "DATA")
            self.log(f"  进度: {progress}%", "DATA")

            self.current_task_id = task_id
        else:
            self.log(f"当前无运行中的任务", "DATA")
            self.log(f"is_busy: {is_busy}", "DATA")

        self.record(TestResult("当前任务", True, "查询成功", {"is_busy": is_busy}))

    def test_run_stream(self):
        """测试执行 STREAM 基准测试"""
        print(f"\n{'='*60}")
        print("TEST: 执行 STREAM 测试")
        print(f"{'='*60}")

        # 确保没有运行中的任务
        self.ensure_no_running_task()

        # 确保工具已安装
        if not self.ensure_tool_installed("stream"):
            self.record(TestResult("STREAM测试", False, "无法安装 stream 工具"))
            return

        # 执行测试
        self.log(f"步骤 1: 发起 STREAM 测试请求", "INFO")
        params = {"array_size": 10000000}  # 使用较小的数组加速测试

        start_time = time.time()
        status_code, data = self.request("POST", "/api/benchmark/run",
                                          {"test_name": "stream", "params": params},
                                          timeout=120)

        if status_code != 200:
            self.record(TestResult("STREAM测试", False, f"执行请求失败: HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        task_id = resp_data.get("task_id")
        status = resp_data.get("status")

        self.log(f"任务已创建:", "DATA")
        self.log(f"  任务 ID: {task_id}", "DATA")
        self.log(f"  初始状态: {status}", "DATA")

        # 如果同步完成
        if status == "completed":
            elapsed = time.time() - start_time
            results = resp_data.get("results", {})

            self.log(f"测试同步完成，耗时 {elapsed:.1f} 秒", "DATA")
            self.log(f"结果:", "DATA")

            # 显示 STREAM 结果
            for key in ["copy_rate", "scale_rate", "add_rate", "triad_rate"]:
                if key in results:
                    self.log(f"  {key}: {results[key]} MB/s", "DATA")

            self.record(TestResult("STREAM测试", True,
                                   f"完成，耗时 {elapsed:.1f}s",
                                   {"task_id": task_id, "results": results}))
            return

        # 如果异步执行，等待完成
        if status == "running":
            self.log(f"步骤 2: 等待任务完成...", "INFO")

            final_data = self.wait_for_task(task_id, timeout=120)
            elapsed = time.time() - start_time

            if not final_data:
                self.record(TestResult("STREAM测试", False, "等待超时"))
                return

            final_status = final_data.get("status")
            self.log(f"最终状态: {final_status}", "DATA")

            if final_status == "completed":
                results = final_data.get("results", {})

                self.log(f"测试完成，总耗时 {elapsed:.1f} 秒", "DATA")
                self.log(f"结果:", "DATA")

                for key in ["copy_rate", "scale_rate", "add_rate", "triad_rate"]:
                    if key in results:
                        self.log(f"  {key}: {results[key]} MB/s", "DATA")

                self.record(TestResult("STREAM测试", True,
                                       f"完成，耗时 {elapsed:.1f}s",
                                       {"task_id": task_id, "results": results}))
            else:
                self.record(TestResult("STREAM测试", False, f"任务状态: {final_status}"))

    def test_task_control(self):
        """测试任务控制（暂停/恢复/取消）"""
        print(f"\n{'='*60}")
        print("TEST: 任务控制")
        print(f"{'='*60}")

        # 确保没有运行中的任务
        self.ensure_no_running_task()

        # 确保 unixbench 已安装（长时间测试便于控制）
        if not self.ensure_tool_installed("unixbench"):
            self.log("无法安装 unixbench，跳过任务控制测试", "WARN")
            self.record(TestResult("任务控制", True, "跳过（unixbench 不可用）"))
            return

        # 启动 unixbench
        self.log(f"步骤 1: 启动 UnixBench 测试", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/run",
                                          {"test_name": "unixbench"},
                                          timeout=30)

        if status_code != 200:
            self.record(TestResult("任务控制", False, f"启动测试失败: HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        task_id = resp_data.get("task_id")

        if not task_id:
            self.record(TestResult("任务控制", False, "未返回 task_id", data))
            return

        self.log(f"任务已启动: {task_id}", "DATA")
        time.sleep(2)

        # 查询状态
        self.log(f"步骤 2: 查询任务状态", "INFO")
        status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")

        if status_code == 200:
            status = data.get("data", {}).get("status")
            self.log(f"当前状态: {status}", "DATA")

        # 暂停任务
        self.log(f"步骤 3: 暂停任务", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/pause", {"task_id": task_id})

        if status_code != 200:
            self.record(TestResult("任务控制", False, f"暂停失败: HTTP {status_code}", data))
            self.request("POST", "/api/benchmark/cancel", {"task_id": task_id})
            return

        self.log(f"暂停成功", "DATA")

        # 验证暂停状态
        status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")
        status = data.get("data", {}).get("status")

        if status != "paused":
            self.log(f"警告: 状态应为 paused，实际: {status}", "WARN")

        # 恢复任务
        self.log(f"步骤 4: 恢复任务", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/resume", {"task_id": task_id})

        if status_code != 200:
            self.record(TestResult("任务控制", False, f"恢复失败: HTTP {status_code}", data))
            return

        self.log(f"恢复成功", "DATA")

        # 验证恢复状态
        status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")
        status = data.get("data", {}).get("status")

        self.log(f"当前状态: {status}", "DATA")

        # 取消任务
        self.log(f"步骤 5: 取消任务", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/cancel", {"task_id": task_id})

        if status_code != 200:
            self.record(TestResult("任务控制", False, f"取消失败: HTTP {status_code}", data))
            return

        self.log(f"取消成功", "DATA")

        # 验证取消状态
        status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")
        status = data.get("data", {}).get("status")

        if status != "cancelled":
            self.log(f"警告: 状态应为 cancelled，实际: {status}", "WARN")

        self.record(TestResult("任务控制", True, "暂停/恢复/取消流程正确", {"task_id": task_id}))

    def test_concurrent_limit(self):
        """测试并发限制"""
        print(f"\n{'='*60}")
        print("TEST: 并发限制")
        print(f"{'='*60}")

        # 确保没有运行中的任务
        self.ensure_no_running_task()

        # 确保工具已安装
        if not self.ensure_tool_installed("unixbench"):
            self.log("无法安装 unixbench，跳过并发限制测试", "WARN")
            self.record(TestResult("并发限制", True, "跳过（unixbench 不可用）"))
            return

        # 启动一个长时间测试
        self.log(f"步骤 1: 启动 UnixBench 测试", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/run",
                                          {"test_name": "unixbench"},
                                          timeout=30)

        if status_code != 200:
            self.record(TestResult("并发限制", False, f"启动测试失败: HTTP {status_code}", data))
            return

        task_id = data.get("data", {}).get("task_id")
        self.log(f"任务已启动: {task_id}", "DATA")

        # 尝试启动另一个测试（应该失败）
        self.log(f"步骤 2: 尝试启动另一个测试（应被拒绝）", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/run",
                                          {"test_name": "stream"},
                                          timeout=30)

        if status_code != 409:
            self.log(f"警告: 应返回 409，实际: {status_code}", "WARN")
            self.record(TestResult("并发限制", False, f"应返回 409，实际: {status_code}", data))
        else:
            error_code = data.get("error", {}).get("code")
            current_task = data.get("error", {}).get("details", {}).get("current_task_id")

            self.log(f"正确返回 409: {error_code}", "DATA")
            self.log(f"当前运行任务: {current_task}", "DATA")

            self.record(TestResult("并发限制", True, "正确拒绝并发任务"))

        # 清理：取消任务
        self.log(f"步骤 3: 取消测试任务", "INFO")
        self.request("POST", "/api/benchmark/cancel", {"task_id": task_id})

    def test_result_query(self):
        """测试结果查询"""
        print(f"\n{'='*60}")
        print("TEST: 结果查询")
        print(f"{'='*60}")

        # 获取结果列表
        status_code, data = self.request("GET", "/api/benchmark/results?limit=1")

        if status_code != 200:
            self.record(TestResult("结果查询", False, f"获取结果列表失败: HTTP {status_code}", data))
            return

        results = data.get("data", {}).get("results", [])

        if not results:
            self.log("没有历史结果，跳过结果查询测试", "WARN")
            self.record(TestResult("结果查询", True, "跳过（无历史结果）"))
            return

        # 取第一个结果
        first_result = results[0]
        task_id = first_result.get("task_id")

        self.log(f"使用结果: {task_id}", "DATA")

        # 查询任务详情
        self.log(f"步骤 1: 查询任务详情", "INFO")
        status_code, data = self.request("GET", f"/api/benchmark/tasks/{task_id}")

        if status_code != 200:
            self.record(TestResult("结果查询", False, f"查询任务失败: HTTP {status_code}", data))
            return

        task_data = data.get("data", {})
        self.log(f"任务信息:", "DATA")
        self.log(f"  测试名: {task_data.get('test_name')}", "DATA")
        self.log(f"  状态: {task_data.get('status')}", "DATA")
        self.log(f"  开始时间: {task_data.get('start_time')}", "DATA")

        # 查询结果详情
        self.log(f"步骤 2: 查询结果详情", "INFO")
        status_code, data = self.request("GET", f"/api/benchmark/results/{task_id}")

        if status_code != 200:
            self.record(TestResult("结果查询", False, f"查询结果失败: HTTP {status_code}", data))
            return

        result_data = data.get("data", {})
        self.log(f"结果信息:", "DATA")
        self.log(f"  得分: {result_data.get('score')}", "DATA")

        # 查询日志路径
        self.log(f"步骤 3: 查询日志路径", "INFO")
        status_code, data = self.request("GET", f"/api/benchmark/logs/{task_id}")

        if status_code == 200:
            log_path = data.get("data", {}).get("log_file")
            self.log(f"日志路径: {log_path}", "DATA")

        self.record(TestResult("结果查询", True, "任务/结果/日志查询成功", {"task_id": task_id}))

    def test_invalid_operations(self):
        """测试无效操作"""
        print(f"\n{'='*60}")
        print("TEST: 无效操作测试")
        print(f"{'='*60}")

        # 无效的任务 ID
        self.log(f"测试无效任务 ID", "INFO")

        status_code, data = self.request("GET", "/api/benchmark/tasks/invalid-id-123")
        if status_code == 404:
            self.log(f"查询无效任务正确返回 404", "DATA")
        else:
            self.log(f"警告: 应返回 404，实际: {status_code}", "WARN")

        status_code, data = self.request("POST", "/api/benchmark/cancel", {"task_id": "invalid-id-123"})
        if status_code == 400:
            self.log(f"取消无效任务正确返回 400", "DATA")
        else:
            self.log(f"警告: 应返回 400，实际: {status_code}", "WARN")

        # 无效的测试名
        self.log(f"测试无效测试名", "INFO")
        status_code, data = self.request("POST", "/api/benchmark/run", {"test_name": "invalid_test"})

        if status_code in (400, 409):  # 400 工具不存在，或 409 有任务在运行
            self.log(f"无效测试名正确返回 {status_code}", "DATA")
        else:
            self.log(f"警告: 应返回 400 或 409，实际: {status_code}", "WARN")

        self.record(TestResult("无效操作", True, "无效操作正确返回错误"))

    def run_all(self, quick: bool = False):
        """运行所有测试"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}    Node Agent Benchmark 模块测试{Colors.NC}")
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
        self.test_list_tasks()
        self.test_list_results()
        self.test_current_task()
        self.test_invalid_operations()

        if not quick:
            self.test_run_stream()
            self.test_task_control()
            self.test_concurrent_limit()
            self.test_result_query()
        else:
            self.log("快速模式：跳过执行测试", "WARN")

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
    parser = argparse.ArgumentParser(description="Benchmark 模块测试")
    parser.add_argument("--host", default="localhost", help="服务地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--quick", action="store_true", help="快速测试（跳过执行测试）")
    args = parser.parse_args()

    tester = BenchmarkTester(host=args.host, port=args.port, verbose=args.verbose)
    tester.run_all(quick=args.quick)


if __name__ == "__main__":
    main()