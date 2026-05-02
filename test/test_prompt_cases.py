#!/usr/bin/env python3
"""
Prompt 场景集成测试

覆盖点：
- 闲聊 / 非性能请求
- 多轮会话连续性
- CPU / 存储 / 网络等典型 prompt
- 会话列表与会话详情接口
"""

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Optional

import requests


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"


@dataclass
class PromptCase:
    name: str
    prompt: str
    expect_non_empty: bool = True
    conversation_id: Optional[str] = None


class PromptCaseTester:
    def __init__(self, host: str = "127.0.0.1", port: int = 10000, verbose: bool = False):
        self.base_url = f"http://{host}:{port}/v1"
        self.verbose = verbose
        self.passed = 0
        self.failed = 0

    def log(self, msg: str, level: str = "INFO"):
        prefix = {
            "INFO": f"{Colors.BLUE}[INFO]{Colors.NC}",
            "PASS": f"{Colors.GREEN}[PASS]{Colors.NC}",
            "FAIL": f"{Colors.RED}[FAIL]{Colors.NC}",
            "WARN": f"{Colors.YELLOW}[WARN]{Colors.NC}",
            "DATA": f"{Colors.CYAN}[DATA]{Colors.NC}",
        }.get(level, "[LOG]")
        print(f"{prefix} {msg}")

    def request(self, method: str, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        return requests.request(method, url, timeout=120, **kwargs)

    def run_case(
        self,
        case: PromptCase,
        session_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> bool:
        payload = {
            "model": "perfa-agent",
            "messages": [{"role": "user", "content": case.prompt}],
            "stream": False,
        }
        if session_id:
            payload["session_id"] = session_id
        if conversation_id:
            payload["conversation_id"] = conversation_id

        response = self.request("POST", "/chat/completions", json=payload)
        ok = response.status_code == 200
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        if self.verbose:
            self.log(json.dumps(data, ensure_ascii=False, indent=2)[:1200], "DATA")

        passed = ok and ((not case.expect_non_empty) or bool(content.strip()))
        if passed:
            self.passed += 1
            self.log(f"{case.name}: 返回成功，正文长度 {len(content)}", "PASS")
        else:
            self.failed += 1
            self.log(f"{case.name}: 请求失败或正文为空 (status={response.status_code})", "FAIL")

        return passed

    def test_session_interfaces(self, session_id: str, expected_messages: int) -> bool:
        response = self.request("GET", "/sessions")
        if response.status_code != 200:
            self.failed += 1
            self.log(f"会话列表接口失败: HTTP {response.status_code}", "FAIL")
            return False

        sessions = response.json().get("sessions", [])
        self.log(f"会话列表返回 {len(sessions)} 条", "DATA")

        target = next((session for session in sessions if session.get("session_id") == session_id), None)
        if not target:
            self.failed += 1
            self.log(f"会话列表里未找到目标会话: {session_id}", "FAIL")
            return False

        detail_response = self.request("GET", f"/sessions/{session_id}")
        if detail_response.status_code != 200:
            self.failed += 1
            self.log(f"会话详情接口失败: HTTP {detail_response.status_code}", "FAIL")
            return False

        detail = detail_response.json()
        messages = detail.get("messages", [])
        if len(messages) < expected_messages:
            self.failed += 1
            self.log(
                f"会话详情消息数不符合预期: got={len(messages)} expected>={expected_messages}",
                "FAIL",
            )
            return False

        self.passed += 1
        self.log(f"会话详情接口成功，消息数 {len(messages)}", "PASS")
        return True

    def test_multi_turn(self) -> bool:
        session_id = f"test_session_{uuid.uuid4().hex[:12]}"
        conversation_id = f"test_conv_{uuid.uuid4().hex[:12]}"

        cases = [
            PromptCase("多轮-第一问", "帮我看看 CPU 测试一般怎么做"),
            PromptCase("多轮-第二问", "那再加一个 superpi，对比一下"),
        ]

        passed = all(
            self.run_case(case, session_id=session_id, conversation_id=conversation_id)
            for case in cases
        )
        if not passed:
            self.failed += 1
            self.log("多轮会话基础请求失败", "FAIL")
            return False

        detail_response = self.request("GET", f"/sessions/{session_id}")
        if detail_response.status_code != 200:
            self.failed += 1
            self.log(f"多轮会话详情获取失败: HTTP {detail_response.status_code}", "FAIL")
            return False

        detail = detail_response.json()
        messages = detail.get("messages", [])
        if len(messages) < 4:
            self.failed += 1
            self.log(f"多轮会话消息数异常: got={len(messages)} expected>=4", "FAIL")
            return False

        last_user_message = detail.get("last_user_message")
        if last_user_message != "那再加一个 superpi，对比一下":
            self.failed += 1
            self.log(f"最后一条用户消息不匹配: {last_user_message}", "FAIL")
            return False

        self.passed += 1
        self.log("多轮会话已在同一真实会话下聚合", "PASS")
        return self.test_session_interfaces(session_id=session_id, expected_messages=4)

    def run(self):
        self.log("开始 prompt 场景测试", "INFO")

        cases = [
            PromptCase("闲聊场景", "你好，你是谁？"),
            PromptCase("CPU 场景", "测试 CPU 性能"),
            PromptCase("存储场景", "测试磁盘 IO 性能"),
            PromptCase("网络场景", "测试网络性能"),
        ]

        for case in cases:
            session_id = f"test_session_{uuid.uuid4().hex[:12]}"
            conversation_id = f"test_conv_{uuid.uuid4().hex[:12]}"
            self.run_case(case, session_id=session_id, conversation_id=conversation_id)

        self.test_multi_turn()

        total = self.passed + self.failed
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
        self.log(f"总用例: {total}", "INFO")
        self.log(f"通过: {self.passed}", "PASS" if self.passed else "INFO")
        self.log(f"失败: {self.failed}", "FAIL" if self.failed else "INFO")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")
        return 0 if self.failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Prompt 场景集成测试")
    parser.add_argument("--host", default="127.0.0.1", help="后端地址")
    parser.add_argument("--port", type=int, default=10000, help="后端端口")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印详细响应")
    args = parser.parse_args()

    tester = PromptCaseTester(host=args.host, port=args.port, verbose=args.verbose)
    sys.exit(tester.run())


if __name__ == "__main__":
    main()
