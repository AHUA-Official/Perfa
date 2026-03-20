#!/usr/bin/env python3
"""
Node Agent Storage 模块测试

测试范围:
- 存储使用情况查询
- 日志文件管理
- 存储清理
- 配置管理
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


class StorageTester:
    """Storage 模块测试器"""

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
                resp = requests.post(url, json=data, timeout=60)
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

    # ==================== 测试用例 ====================

    def test_storage_usage(self):
        """测试存储使用情况查询"""
        print(f"\n{'='*60}")
        print("TEST: 存储使用情况")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/storage/usage")

        self.log(f"请求 GET /api/storage/usage", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("存储使用", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        # 验证必要字段
        required_fields = ["data_dir", "working_dir", "total_size_mb"]
        missing = [f for f in required_fields if f not in resp_data]

        if missing:
            self.record(TestResult("存储使用", False, f"缺少字段: {missing}", data))
            return

        # 显示存储信息
        self.log(f"数据目录: {resp_data.get('data_dir')}", "DATA")
        self.log(f"工作目录: {resp_data.get('working_dir')}", "DATA")
        self.log(f"总大小: {resp_data.get('total_size_mb')} MB", "DATA")

        # 数据库信息
        db_info = resp_data.get("database")
        if db_info:
            self.log(f"数据库:", "DATA")
            self.log(f"  路径: {db_info.get('path')}", "DATA")
            self.log(f"  大小: {db_info.get('size_mb')} MB", "DATA")
            self.log(f"  结果数: {db_info.get('result_count', 'N/A')}", "DATA")

        # 日志信息
        logs_info = resp_data.get("logs")
        if logs_info:
            self.log(f"日志:", "DATA")
            self.log(f"  数量: {logs_info.get('count')}", "DATA")
            self.log(f"  大小: {logs_info.get('total_size_mb')} MB", "DATA")

        # 工作目录信息
        work_info = resp_data.get("working_dir_files")
        if work_info:
            self.log(f"工作目录文件:", "DATA")
            self.log(f"  数量: {work_info.get('count')}", "DATA")
            self.log(f"  大小: {work_info.get('total_size_mb')} MB", "DATA")

        self.record(TestResult("存储使用", True,
                               f"总大小 {resp_data.get('total_size_mb')} MB",
                               resp_data))

    def test_list_logs(self):
        """测试日志文件列表"""
        print(f"\n{'='*60}")
        print("TEST: 日志文件列表")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/storage/logs?limit=10")

        self.log(f"请求 GET /api/storage/logs?limit=10", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("日志列表", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        logs = resp_data.get("logs", [])
        total_count = resp_data.get("total_count", 0)

        self.log(f"日志数量: {len(logs)}/{total_count}", "DATA")

        if not logs:
            self.log("没有日志文件", "WARN")
            self.record(TestResult("日志列表", True, "无日志文件"))
            return

        # 显示日志列表
        for log in logs:
            name = log.get("name", "unknown")
            size = log.get("size_kb", 0)
            modified = log.get("modified", "unknown")
            self.log(f"  - {name} ({size} KB, {modified})", "DATA")

        self.record(TestResult("日志列表", True, f"找到 {total_count} 个日志文件"))

    def test_read_log(self):
        """测试读取日志内容"""
        print(f"\n{'='*60}")
        print("TEST: 读取日志内容")
        print(f"{'='*60}")

        # 先获取日志列表
        status_code, data = self.request("GET", "/api/storage/logs?limit=1")

        if status_code != 200 or not data.get("data", {}).get("logs"):
            self.log("没有日志文件可测试", "WARN")
            self.record(TestResult("读取日志", True, "跳过（无日志文件）"))
            return

        log_name = data.get("data", {}).get("logs", [])[0].get("name")

        self.log(f"步骤 1: 读取日志文件: {log_name}", "INFO")

        status_code, data = self.request("GET", f"/api/storage/logs/{log_name}?lines=50")

        if status_code != 200:
            self.record(TestResult("读取日志", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        # 验证响应字段
        required = ["name", "content", "total_lines"]
        missing = [f for f in required if f not in resp_data]

        if missing:
            self.record(TestResult("读取日志", False, f"缺少字段: {missing}", data))
            return

        self.log(f"日志信息:", "DATA")
        self.log(f"  文件名: {resp_data.get('name')}", "DATA")
        self.log(f"  总行数: {resp_data.get('total_lines')}", "DATA")
        self.log(f"  显示行数: {resp_data.get('shown_lines')}", "DATA")
        self.log(f"  文件大小: {resp_data.get('size_kb')} KB", "DATA")

        # 显示部分内容
        content = resp_data.get("content", "")
        lines = content.split("\n")[:5]
        self.log(f"内容预览 (前 5 行):", "DATA")
        for line in lines:
            if line.strip():
                self.log(f"    {line[:100]}", "DATA")

        self.record(TestResult("读取日志", True,
                               f"读取成功，共 {resp_data.get('total_lines')} 行"))

    def test_log_security(self):
        """测试日志读取安全性"""
        print(f"\n{'='*60}")
        print("TEST: 日志读取安全性")
        print(f"{'='*60}")

        # 测试路径遍历攻击
        self.log("测试路径遍历攻击: ../etc/passwd", "INFO")

        status_code, data = self.request("GET", "/api/storage/logs/../etc/passwd")

        # 应该返回 400（参数错误）或 404（未找到）
        if status_code in (400, 404):
            self.log(f"正确拒绝: HTTP {status_code}", "DATA")
        else:
            self.record(TestResult("日志安全", False, f"应拒绝请求，实际: HTTP {status_code}", data))
            return

        # 测试非日志文件
        self.log("测试非日志文件: /etc/passwd", "INFO")

        status_code, data = self.request("GET", "/api/storage/logs//etc/passwd")

        if status_code in (400, 404):
            self.log(f"正确拒绝: HTTP {status_code}", "DATA")
        else:
            self.record(TestResult("日志安全", False, f"应拒绝请求，实际: HTTP {status_code}", data))
            return

        # 测试不存在的日志
        self.log("测试不存在的日志: nonexistent.log", "INFO")

        status_code, data = self.request("GET", "/api/storage/logs/nonexistent.log")

        if status_code == 404:
            self.log(f"正确返回 404", "DATA")
        else:
            self.record(TestResult("日志安全", False, f"应返回 404，实际: HTTP {status_code}", data))
            return

        self.record(TestResult("日志安全", True, "安全检查全部通过"))

    def test_storage_cleanup(self):
        """测试存储清理"""
        print(f"\n{'='*60}")
        print("TEST: 存储清理")
        print(f"{'='*60}")

        # 获取清理前的存储使用情况
        self.log("步骤 1: 获取清理前的存储使用情况", "INFO")
        status_code, data = self.request("GET", "/api/storage/usage")

        if status_code != 200:
            self.record(TestResult("存储清理", False, "无法获取存储使用情况", data))
            return

        before_size = data.get("data", {}).get("total_size_mb", 0)
        self.log(f"清理前大小: {before_size} MB", "DATA")

        # 执行清理（安全模式，不实际删除）
        self.log("步骤 2: 执行清理（安全模式）", "INFO")

        cleanup_params = {
            "clean_logs": False,       # 不清理日志
            "clean_working_dir": False,  # 不清理工作目录
            "clean_old_results": False   # 不清理旧结果
        }

        status_code, data = self.request("POST", "/api/storage/cleanup", cleanup_params)

        if status_code != 200:
            self.record(TestResult("存储清理", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        self.log(f"清理结果:", "DATA")
        self.log(f"  删除日志数: {resp_data.get('logs_deleted', 0)}", "DATA")
        self.log(f"  日志释放空间: {resp_data.get('logs_size_freed_mb', 0)} MB", "DATA")
        self.log(f"  删除工作文件数: {resp_data.get('working_files_deleted', 0)}", "DATA")
        self.log(f"  工作目录释放空间: {resp_data.get('working_size_freed_mb', 0)} MB", "DATA")
        self.log(f"  删除结果数: {resp_data.get('results_deleted', 0)}", "DATA")

        # 验证清理后的存储使用情况
        self.log("步骤 3: 验证清理后的存储使用情况", "INFO")
        status_code, data = self.request("GET", "/api/storage/usage")

        if status_code == 200:
            after_size = data.get("data", {}).get("total_size_mb", 0)
            self.log(f"清理后大小: {after_size} MB", "DATA")

        self.record(TestResult("存储清理", True, "清理接口正常工作", resp_data))

    def test_config_get(self):
        """测试配置获取"""
        print(f"\n{'='*60}")
        print("TEST: 配置获取")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/config")

        self.log(f"请求 GET /api/config", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("配置获取", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})

        # 显示配置信息
        self.log(f"当前配置:", "DATA")
        self.log(f"  采集间隔: {resp_data.get('collect_interval_sec')} 秒", "DATA")
        self.log(f"  最大并发任务: {resp_data.get('max_concurrent_tasks')}", "DATA")
        self.log(f"  监控运行中: {resp_data.get('monitor_running')}", "DATA")

        enabled_metrics = resp_data.get("enabled_metrics", [])
        if enabled_metrics:
            self.log(f"  启用的指标: {enabled_metrics}", "DATA")

        self.record(TestResult("配置获取", True, "获取成功", resp_data))

    def test_config_update(self):
        """测试配置更新"""
        print(f"\n{'='*60}")
        print("TEST: 配置更新")
        print(f"{'='*60}")

        # 获取当前配置
        self.log("步骤 1: 获取当前配置", "INFO")
        status_code, data = self.request("GET", "/api/config")

        if status_code != 200:
            self.record(TestResult("配置更新", False, "无法获取当前配置", data))
            return

        original_interval = data.get("data", {}).get("collect_interval_sec", 5)
        self.log(f"原始采集间隔: {original_interval}", "DATA")

        # 更新配置
        self.log("步骤 2: 更新采集间隔", "INFO")
        new_interval = 15 if original_interval != 15 else 10

        status_code, data = self.request("POST", "/api/config",
                                          {"collect_interval_sec": new_interval})

        if status_code != 200:
            self.record(TestResult("配置更新", False, f"更新失败: HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        self.log(f"更新响应: {resp_data}", "DATA")

        # 验证更新
        self.log("步骤 3: 验证配置已更新", "INFO")
        status_code, data = self.request("GET", "/api/config")

        if status_code != 200:
            self.record(TestResult("配置更新", False, "无法验证更新", data))
            return

        updated_interval = data.get("data", {}).get("collect_interval_sec")
        self.log(f"更新后采集间隔: {updated_interval}", "DATA")

        if updated_interval != new_interval:
            self.record(TestResult("配置更新", False,
                                   f"配置未更新，预期 {new_interval}，实际 {updated_interval}", data))
            return

        # 恢复原配置
        self.log("步骤 4: 恢复原配置", "INFO")
        self.request("POST", "/api/config", {"collect_interval_sec": original_interval})

        # 测试无效配置
        self.log("步骤 5: 测试无效配置更新", "INFO")
        status_code, data = self.request("POST", "/api/config", {})

        if status_code == 400:
            self.log(f"空配置正确返回 400", "DATA")
        else:
            self.log(f"警告: 应返回 400，实际: {status_code}", "WARN")

        self.record(TestResult("配置更新", True,
                               f"成功更新采集间隔: {original_interval} -> {new_interval} -> {original_interval}"))

    def run_all(self):
        """运行所有测试"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}    Node Agent Storage 模块测试{Colors.NC}")
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
        self.test_storage_usage()
        self.test_list_logs()
        self.test_read_log()
        self.test_log_security()
        self.test_storage_cleanup()
        self.test_config_get()
        self.test_config_update()

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
    parser = argparse.ArgumentParser(description="Storage 模块测试")
    parser.add_argument("--host", default="localhost", help="服务地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    tester = StorageTester(host=args.host, port=args.port, verbose=args.verbose)
    tester.run_all()


if __name__ == "__main__":
    main()