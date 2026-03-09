from __future__ import annotations

import argparse
import sys

from perfa_mvp1.config import ConfigError, load_config_from_env
from perfa_mvp1.cpu_benchmark import run_cpu_test, to_pretty_json
from perfa_mvp1.ssh_executor import SSHExecutor


def main() -> int:
    parser = argparse.ArgumentParser(description="MVP1: 远程执行 sysbench CPU 测试")
    parser.add_argument("--threads", type=int, default=1, help="CPU 测试线程数，默认 1")
    args = parser.parse_args()

    try:
        config = load_config_from_env()
    except ConfigError as exc:
        print(f"配置错误: {exc}", file=sys.stderr)
        return 2

    try:
        with SSHExecutor(config) as executor:
            result = run_cpu_test(executor, threads=args.threads)
    except Exception as exc:  # noqa: BLE001
        print(f"执行失败: {exc}", file=sys.stderr)
        return 1

    print(to_pretty_json(result))

    if result.exit_code != 0:
        return result.exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
