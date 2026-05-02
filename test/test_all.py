#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_suite(label: str, target: str) -> bool:
    print(f"\n=== {label} ===")
    cmd = [sys.executable, "-m", "unittest", "discover", "-s", target, "-p", "test*.py"]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'src'}:{ROOT / 'src' / 'mcp_server'}:{ROOT / 'src' / 'node_agent'}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(cmd, cwd=ROOT, env=env)
    return result.returncode == 0


def main() -> int:
    suites = [
        ("MCP Server Tests", "test/mcp_server"),
        ("LangChain Agent Tests", "test/langchain_agent"),
        ("Regression Tests", "test/regressions"),
        ("Ops Script Tests", "test/ops"),
        ("WebUI V2 Tests", "test/webui_v2"),
    ]
    failed = []
    for label, target in suites:
        if not run_suite(label, target):
            failed.append(label)

    print("\n=== Summary ===")
    if failed:
        print("FAILED:")
        for item in failed:
            print(f"- {item}")
        return 1

    print("All deterministic test suites passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
