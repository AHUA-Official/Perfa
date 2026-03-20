#!/usr/bin/env python3
"""
Node Agent 全模块测试入口

运行所有四个模块的测试:
- test_monitor.py   - 监控模块
- test_tool.py      - 工具管理模块
- test_benchmark.py - 压测执行模块
- test_storage.py   - 存储管理模块

使用方法:
    python run_all.py                    # 运行所有测试
    python run_all.py --quick            # 快速测试
    python run_all.py --module monitor   # 只运行指定模块
"""

import argparse
import subprocess
import sys
from pathlib import Path


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


MODULES = {
    "monitor": {
        "script": "test_monitor.py",
        "description": "监控模块测试（健康检查、系统信息、监控启停）"
    },
    "tool": {
        "script": "test_tool.py",
        "description": "工具管理模块测试（工具列表、安装/卸载）"
    },
    "benchmark": {
        "script": "test_benchmark.py",
        "description": "压测执行模块测试（任务执行、控制、结果查询）"
    },
    "storage": {
        "script": "test_storage.py",
        "description": "存储管理模块测试（存储查询、日志管理、配置）"
    }
}


def run_test(script: str, host: str, port: int, quick: bool, verbose: bool) -> tuple:
    """运行单个测试脚本"""
    cmd = [sys.executable, script, "--host", host, "--port", str(port)]

    if quick:
        cmd.append("--quick" if "benchmark" in script else "--skip-install")

    if verbose:
        cmd.append("-v")

    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Node Agent 全模块测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
模块说明:
  monitor    健康检查、系统信息、监控启停
  tool       工具列表、安装/卸载
  benchmark  任务执行、控制、结果查询
  storage    存储查询、日志管理、配置

示例:
  python run_all.py                      # 运行所有测试
  python run_all.py --quick              # 快速测试
  python run_all.py --module monitor     # 只测试监控模块
  python run_all.py --host 192.168.1.100 # 指定服务地址
"""
    )

    parser.add_argument("--host", default="localhost", help="服务地址")
    parser.add_argument("--port", type=int, default=8080, help="服务端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    parser.add_argument("--quick", action="store_true", help="快速测试")
    parser.add_argument("--module", choices=list(MODULES.keys()), help="只运行指定模块")

    args = parser.parse_args()

    script_dir = Path(__file__).parent

    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.CYAN}    Node Agent 全模块测试{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"\n服务地址: {args.host}:{args.port}")
    print(f"测试模式: {'快速' if args.quick else '完整'}")

    results = {}
    modules_to_run = [args.module] if args.module else list(MODULES.keys())

    for module in modules_to_run:
        info = MODULES[module]
        script = script_dir / info["script"]

        print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"{Colors.CYAN}模块: {module}{Colors.NC}")
        print(f"{Colors.CYAN}{'='*60}{Colors.NC}")
        print(f"说明: {info['description']}")

        if not script.exists():
            print(f"{Colors.RED}错误: 脚本不存在 - {script}{Colors.NC}")
            results[module] = False
            continue

        passed = run_test(str(script), args.host, args.port, args.quick, args.verbose)
        results[module] = passed

    # 输出总结
    print(f"\n{Colors.CYAN}{'='*60}{Colors.NC}")
    print(f"{Colors.CYAN}    全模块测试总结{Colors.NC}")
    print(f"{Colors.CYAN}{'='*60}{Colors.NC}")

    total_passed = sum(1 for v in results.values() if v)
    total_failed = len(results) - total_passed

    for module, passed in results.items():
        status = f"{Colors.GREEN}✓ 通过{Colors.NC}" if passed else f"{Colors.RED}✗ 失败{Colors.NC}"
        print(f"  {module:<15} {status}")

    print()
    print(f"{Colors.GREEN}通过模块: {total_passed}{Colors.NC}")
    print(f"{Colors.RED}失败模块: {total_failed}{Colors.NC}")

    if total_failed == 0:
        print(f"\n{Colors.GREEN}所有模块测试通过!{Colors.NC}")
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}存在失败的模块{Colors.NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()