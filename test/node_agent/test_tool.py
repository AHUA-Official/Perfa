#!/usr/bin/env python3
"""
Node Agent Tool 模块测试

测试范围:
- 工具列表查询
- 工具状态查询
- 工具安装/卸载
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


class ToolTester:
    """Tool 模块测试器"""

    # 已知的工具列表
    KNOWN_TOOLS = ["stream", "unixbench", "superpi", "mlc", "fio", "hping3"]

    def __init__(self, host: str = "localhost", port: int = 8080, verbose: bool = False):
        self.base_url = f"http://{host}:{port}"
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.passed = 0
        self.failed = 0
        self.tool_status: Dict[str, str] = {}  # 记录工具状态

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

    def test_list_tools(self):
        """测试工具列表查询"""
        print(f"\n{'='*60}")
        print("TEST: 工具列表查询")
        print(f"{'='*60}")

        status_code, data = self.request("GET", "/api/tools")

        self.log(f"请求 GET /api/tools", "INFO")
        self.log(f"响应状态码: {status_code}", "DATA")

        if status_code != 200:
            self.record(TestResult("工具列表", False, f"HTTP {status_code}", data))
            return

        resp_data = data.get("data", {})
        tools = resp_data.get("tools", [])

        if not isinstance(tools, list):
            self.record(TestResult("工具列表", False, "tools 不是列表", data))
            return

        # 记录工具状态
        for tool in tools:
            name = tool.get("name")
            status = tool.get("status")
            if name and status:
                self.tool_status[name] = status

        # 验证已知工具都存在
        found_tools = {t.get("name") for t in tools}
        missing = set(self.KNOWN_TOOLS) - found_tools

        if missing:
            self.log(f"缺少工具: {missing}", "WARN")

        self.log(f"工具数量: {len(tools)}", "DATA")

        # 打印工具详情
        for tool in tools:
            name = tool.get("name")
            status = tool.get("status")
            category = tool.get("category", "unknown")
            status_icon = "✓" if status == "installed" else "✗"
            self.log(f"  [{status_icon}] {name} ({category}): {status}", "DATA")

        self.record(TestResult("工具列表", True, f"发现 {len(tools)} 个工具", {"count": len(tools), "tools": found_tools}))

    def test_get_tool_status(self):
        """测试单个工具状态查询"""
        print(f"\n{'='*60}")
        print("TEST: 工具状态查询")
        print(f"{'='*60}")

        # 测试每个已知工具
        for tool_name in self.KNOWN_TOOLS:
            self.log(f"查询工具: {tool_name}", "INFO")

            status_code, data = self.request("GET", f"/api/tools/{tool_name}")

            if status_code != 200:
                self.record(TestResult(f"工具状态-{tool_name}", False, f"HTTP {status_code}", data))
                continue

            resp_data = data.get("data", {})

            # 验证响应字段
            required = ["name", "status"]
            missing = [f for f in required if f not in resp_data]

            if missing:
                self.record(TestResult(f"工具状态-{tool_name}", False, f"缺少字段: {missing}", data))
                continue

            name = resp_data.get("name")
            status = resp_data.get("status")
            version = resp_data.get("version")
            binary_path = resp_data.get("binary_path")

            # 更新状态记录
            self.tool_status[name] = status

            self.log(f"  名称: {name}", "DATA")
            self.log(f"  状态: {status}", "DATA")
            if version:
                self.log(f"  版本: {version}", "DATA")
            if binary_path:
                self.log(f"  路径: {binary_path}", "DATA")

            self.record(TestResult(f"工具状态-{tool_name}", True, f"{status}"))

        # 测试不存在的工具
        self.log(f"查询不存在的工具: notexist", "INFO")
        status_code, data = self.request("GET", "/api/tools/notexist")

        if status_code == 404:
            self.log(f"正确返回 404", "DATA")
            self.record(TestResult("工具状态-不存在", True, "正确返回 404"))
        else:
            self.record(TestResult("工具状态-不存在", False, f"应返回 404，实际: {status_code}", data))

    def test_install_uninstall(self, tool_name: str = "stream"):
        """测试工具安装和卸载"""
        print(f"\n{'='*60}")
        print(f"TEST: 工具安装/卸载 (测试工具: {tool_name})")
        print(f"{'='*60}")

        # 1. 查询当前状态
        self.log(f"步骤 1: 查询 {tool_name} 当前状态", "INFO")
        status_code, data = self.request("GET", f"/api/tools/{tool_name}")

        if status_code != 200:
            self.record(TestResult("工具安装卸载", False, f"查询状态失败: HTTP {status_code}", data))
            return

        current_status = data.get("data", {}).get("status")
        self.log(f"当前状态: {current_status}", "DATA")

        # 2. 如果已安装，先卸载
        if current_status == "installed":
            self.log(f"步骤 2: 工具已安装，先卸载", "INFO")
            status_code, data = self.request("POST", f"/api/tools/{tool_name}/uninstall")

            if status_code != 200:
                self.record(TestResult("工具安装卸载", False, f"卸载失败: HTTP {status_code}", data))
                return

            # 验证卸载成功
            status_code, data = self.request("GET", f"/api/tools/{tool_name}")
            new_status = data.get("data", {}).get("status")
            self.log(f"卸载后状态: {new_status}", "DATA")

            if new_status != "not_installed":
                self.record(TestResult("工具安装卸载", False, f"卸载后状态应为 not_installed，实际: {new_status}", data))
                return

        # 3. 安装工具
        self.log(f"步骤 3: 安装 {tool_name}", "INFO")
        start_time = time.time()
        status_code, data = self.request("POST", f"/api/tools/{tool_name}/install")
        elapsed = time.time() - start_time

        self.log(f"安装耗时: {elapsed:.1f} 秒", "DATA")

        if status_code != 200:
            self.record(TestResult("工具安装卸载", False, f"安装失败: HTTP {status_code}", data))
            return

        # 验证安装响应
        resp_data = data.get("data", {})
        if not resp_data.get("installed"):
            self.record(TestResult("工具安装卸载", False, "安装响应 installed 不为 true", data))
            return

        self.log(f"安装响应: {resp_data.get('message')}", "DATA")

        # 4. 验证安装状态
        self.log(f"步骤 4: 验证安装状态", "INFO")
        status_code, data = self.request("GET", f"/api/tools/{tool_name}")

        if status_code != 200:
            self.record(TestResult("工具安装卸载", False, f"验证请求失败: HTTP {status_code}", data))
            return

        installed_status = data.get("data", {}).get("status")
        self.log(f"安装后状态: {installed_status}", "DATA")

        if installed_status != "installed":
            self.record(TestResult("工具安装卸载", False, f"安装后状态应为 installed，实际: {installed_status}", data))
            return

        version = data.get("data", {}).get("version")
        binary_path = data.get("data", {}).get("binary_path")
        self.log(f"安装版本: {version}", "DATA")
        self.log(f"安装路径: {binary_path}", "DATA")

        # 5. 卸载工具
        self.log(f"步骤 5: 卸载 {tool_name}", "INFO")
        status_code, data = self.request("POST", f"/api/tools/{tool_name}/uninstall")

        if status_code != 200:
            self.record(TestResult("工具安装卸载", False, f"卸载失败: HTTP {status_code}", data))
            return

        # 验证卸载响应
        resp_data = data.get("data", {})
        if resp_data.get("installed"):
            self.record(TestResult("工具安装卸载", False, "卸载响应 installed 不为 false", data))
            return

        self.log(f"卸载响应: {resp_data.get('message')}", "DATA")

        # 6. 验证卸载状态
        self.log(f"步骤 6: 验证卸载状态", "INFO")
        status_code, data = self.request("GET", f"/api/tools/{tool_name}")

        uninstalled_status = data.get("data", {}).get("status")
        self.log(f"卸载后状态: {uninstalled_status}", "DATA")

        if uninstalled_status != "not_installed":
            self.record(TestResult("工具安装卸载", False, f"卸载后状态应为 not_installed，实际: {uninstalled_status}", data))
            return

        # 7. 重新安装（保持环境干净）
        self.log(f"步骤 7: 重新安装 {tool_name} (恢复环境)", "INFO")
        status_code, data = self.request("POST", f"/api/tools/{tool_name}/install")

        if status_code == 200:
            self.log(f"重新安装成功", "DATA")

        self.record(TestResult("工具安装卸载", True,
                               f"{tool_name} 安装/卸载流程正确",
                               {"elapsed_sec": round(elapsed, 1), "version": version}))

    def test_category_filter(self):
        """测试按类别过滤工具"""
        print(f"\n{'='*60}")
        print("TEST: 工具类别过滤")
        print(f"{'='*60}")

        categories = ["cpu", "memory", "disk", "network"]

        for category in categories:
            self.log(f"查询类别: {category}", "INFO")

            status_code, data = self.request("GET", f"/api/tools?category={category}")

            if status_code != 200:
                self.record(TestResult(f"类别过滤-{category}", False, f"HTTP {status_code}", data))
                continue

            tools = data.get("data", {}).get("tools", [])

            # 验证返回的工具都属于该类别
            for tool in tools:
                tool_category = tool.get("category")
                if tool_category != category:
                    self.record(TestResult(f"类别过滤-{category}", False,
                                           f"工具 {tool.get('name')} 类别为 {tool_category}，预期 {category}"))
                    break
            else:
                self.log(f"  找到 {len(tools)} 个工具", "DATA")
                for t in tools:
                    self.log(f"    - {t.get('name')}", "DATA")
                self.record(TestResult(f"类别过滤-{category}", True, f"找到 {len(tools)} 个工具"))

    def run_all(self, install_test: bool = True):
        """运行所有测试"""
        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}    Node Agent Tool 模块测试{Colors.NC}")
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
        self.test_list_tools()
        self.test_get_tool_status()

        if install_test:
            # 使用 stream 作为安装测试（相对快速）
            self.test_install_uninstall("stream")

        self.test_category_filter()

        # 输出工具状态汇总
        print(f"\n{'='*60}")
        print("工具状态汇总:")
        print(f"{'='*60}")
        for name, status in sorted(self.tool_status.items()):
            icon = f"{Colors.GREEN}✓{Colors.NC}" if status == "installed" else f"{Colors.RED}✗{Colors.NC}"
            print(f"  {icon} {name}: {status}")

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
    parser = argparse.ArgumentParser(description="Tool 模块测试")
    parser.add_argument("--host", default="localhost", help="服务地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--skip-install", action="store_true", help="跳过安装测试")
    args = parser.parse_args()

    tester = ToolTester(host=args.host, port=args.port, verbose=args.verbose)
    tester.run_all(install_test=not args.skip_install)


if __name__ == "__main__":
    main()