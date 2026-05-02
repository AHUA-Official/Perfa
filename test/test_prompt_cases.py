#!/usr/bin/env python3
"""
Prompt 场景测试（接口行为 + OTel 链路联合校验）

测试目标：
1. 接口返回成功，且 session / conversation 关系正确
2. OTel trace 真实落到 Jaeger，且包含关键属性
3. 多轮对话复用同一个 conversation_id，并在会话历史中聚合
"""

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    expected_mode: str
    expected_scenario: Optional[str] = None


class PromptCaseTester:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 10000,
        jaeger_base: str = "http://127.0.0.1:16686",
        verbose: bool = False,
    ):
        self.base_url = f"http://{host}:{port}/v1"
        self.jaeger_base = jaeger_base.rstrip("/")
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

    def request(self, method: str, path: str, timeout: int = 120, **kwargs):
        url = f"{self.base_url}{path}"
        return requests.request(method, url, timeout=timeout, **kwargs)

    def request_jaeger(self, path: str, timeout: int = 30):
        url = f"{self.jaeger_base}{path}"
        return requests.get(url, timeout=timeout)

    def pass_case(self, msg: str):
        self.passed += 1
        self.log(msg, "PASS")

    def fail_case(self, msg: str):
        self.failed += 1
        self.log(msg, "FAIL")

    def parse_chat_response(self, response: requests.Response) -> Tuple[Dict[str, Any], str]:
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return data, content

    def run_sync_chat(
        self,
        prompt: str,
        session_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        payload = {
            "model": "perfa-agent",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "session_id": session_id,
            "conversation_id": conversation_id,
        }
        response = self.request("POST", "/chat/completions", json=payload)
        data, content = self.parse_chat_response(response)
        return {
            "status_code": response.status_code,
            "json": data,
            "content": content,
        }

    def run_stream_chat(
        self,
        prompt: str,
        session_id: str,
        conversation_id: str,
    ) -> Dict[str, Any]:
        payload = {
            "model": "perfa-agent",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "session_id": session_id,
            "conversation_id": conversation_id,
        }
        response = self.request("POST", "/chat/completions", json=payload, stream=True, timeout=180)
        trace_id = None
        streamed_text_parts: List[str] = []
        raw_events: List[Dict[str, Any]] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue
            data = raw_line[6:]
            if data == "[DONE]":
                break
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            raw_events.append(event)
            if event.get("trace_id"):
                trace_id = event["trace_id"]
            delta = event.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                streamed_text_parts.append(delta["content"])

        return {
            "status_code": response.status_code,
            "trace_id": trace_id,
            "content": "".join(streamed_text_parts),
            "events": raw_events,
        }

    def wait_for_trace(self, trace_id: str, retries: int = 10, sleep_sec: int = 2) -> Optional[Dict[str, Any]]:
        for _ in range(retries):
            try:
                resp = self.request_jaeger(f"/api/traces/{trace_id}")
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("data"):
                        return data
            except Exception:
                pass
            time.sleep(sleep_sec)
        return None

    def flatten_trace_fields(self, trace_data: Dict[str, Any]) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "span_attributes": {},
            "event_fields": {},
            "operation_names": [],
        }
        traces = trace_data.get("data") or []
        if not traces:
            return result

        spans = traces[0].get("spans", [])
        for span in spans:
            operation = span.get("operationName")
            if operation:
                result["operation_names"].append(operation)

            for tag in span.get("tags", []):
                key = tag.get("key")
                if key:
                    result["span_attributes"][key] = tag.get("value")

            for log in span.get("logs", []):
                for field in log.get("fields", []):
                    key = field.get("key")
                    if key:
                        result["event_fields"][key] = field.get("value")

        return result

    def assert_trace(
        self,
        trace_id: str,
        expected_session_id: str,
        expected_conversation_id: str,
        expected_mode: str,
        expected_scenario: Optional[str],
        case_name: str,
    ) -> bool:
        trace_data = self.wait_for_trace(trace_id)
        if not trace_data:
            self.fail_case(f"{case_name}: Jaeger 中未找到 trace {trace_id}")
            return False

        fields = self.flatten_trace_fields(trace_data)
        attrs = fields["span_attributes"]
        event_fields = fields["event_fields"]
        operations = fields["operation_names"]

        if "orchestrator.process_query_stream" not in operations:
            self.fail_case(f"{case_name}: trace 中缺少 orchestrator.process_query_stream span")
            return False

        if attrs.get("session_id") != expected_session_id:
            self.fail_case(
                f"{case_name}: trace session_id 不匹配, got={attrs.get('session_id')} expected={expected_session_id}"
            )
            return False

        if attrs.get("conversation_id") != expected_conversation_id:
            self.fail_case(
                f"{case_name}: trace conversation_id 不匹配, got={attrs.get('conversation_id')} expected={expected_conversation_id}"
            )
            return False

        mode_used = attrs.get("mode_used") or event_fields.get("mode")
        if mode_used != expected_mode:
            self.fail_case(f"{case_name}: trace mode 不匹配, got={mode_used} expected={expected_mode}")
            return False

        if expected_scenario:
            routed_scenario = event_fields.get("routed_scenario")
            if routed_scenario != expected_scenario:
                self.fail_case(
                    f"{case_name}: routed_scenario 不匹配, got={routed_scenario} expected={expected_scenario}"
                )
                return False

        self.pass_case(f"{case_name}: 接口与 trace 断言通过")
        return True

    def assert_session_detail(self, session_id: str, expected_messages: int, expected_last_user: str) -> bool:
        response = self.request("GET", f"/sessions/{session_id}")
        if response.status_code != 200:
            self.fail_case(f"会话详情获取失败: HTTP {response.status_code}")
            return False

        detail = response.json()
        messages = detail.get("messages", [])
        if len(messages) < expected_messages:
            self.fail_case(f"会话消息数异常: got={len(messages)} expected>={expected_messages}")
            return False

        if detail.get("last_user_message") != expected_last_user:
            self.fail_case(
                f"最后一条用户消息不匹配: got={detail.get('last_user_message')} expected={expected_last_user}"
            )
            return False

        self.pass_case(f"会话历史聚合正确，消息数 {len(messages)}")
        return True

    def run_case(self, case: PromptCase) -> bool:
        session_id = f"test_session_{uuid.uuid4().hex[:12]}"
        conversation_id = f"test_conv_{uuid.uuid4().hex[:12]}"

        sync_result = self.run_sync_chat(case.prompt, session_id, conversation_id)
        if sync_result["status_code"] != 200 or not sync_result["content"].strip():
            self.fail_case(f"{case.name}: 非流式接口失败或正文为空 (status={sync_result['status_code']})")
            return False

        stream_result = self.run_stream_chat(case.prompt, session_id, conversation_id)
        if stream_result["status_code"] != 200:
            self.fail_case(f"{case.name}: 流式接口失败 (status={stream_result['status_code']})")
            return False
        if not stream_result["trace_id"]:
            self.fail_case(f"{case.name}: 流式响应未返回 trace_id")
            return False

        if self.verbose:
            self.log(
                json.dumps(
                    {
                        "session_id": session_id,
                        "conversation_id": conversation_id,
                        "trace_id": stream_result["trace_id"],
                    },
                    ensure_ascii=False,
                ),
                "DATA",
            )

        return self.assert_trace(
            trace_id=stream_result["trace_id"],
            expected_session_id=session_id,
            expected_conversation_id=conversation_id,
            expected_mode=case.expected_mode,
            expected_scenario=case.expected_scenario,
            case_name=case.name,
        )

    def test_multi_turn(self) -> bool:
        session_id = f"test_session_{uuid.uuid4().hex[:12]}"
        conversation_id = f"test_conv_{uuid.uuid4().hex[:12]}"

        first = self.run_stream_chat("帮我看看 CPU 测试一般怎么做", session_id, conversation_id)
        second = self.run_stream_chat("那再加一个 superpi，对比一下", session_id, conversation_id)

        if first["status_code"] != 200 or second["status_code"] != 200:
            self.fail_case("多轮会话: 流式接口失败")
            return False
        if not first["trace_id"] or not second["trace_id"]:
            self.fail_case("多轮会话: 缺少 trace_id")
            return False

        ok1 = self.assert_trace(
            trace_id=first["trace_id"],
            expected_session_id=session_id,
            expected_conversation_id=conversation_id,
            expected_mode="workflow",
            expected_scenario="cpu_focus",
            case_name="多轮-第一问",
        )
        ok2 = self.assert_trace(
            trace_id=second["trace_id"],
            expected_session_id=session_id,
            expected_conversation_id=conversation_id,
            expected_mode="workflow",
            expected_scenario="cpu_focus",
            case_name="多轮-第二问",
        )
        if not (ok1 and ok2):
            return False

        return self.assert_session_detail(
            session_id=session_id,
            expected_messages=4,
            expected_last_user="那再加一个 superpi，对比一下",
        )

    def run(self):
        self.log("开始 prompt 场景测试（接口 + OTel）", "INFO")

        cases = [
            PromptCase("CPU 场景", "测试 CPU 性能", expected_mode="workflow", expected_scenario="cpu_focus"),
            PromptCase("存储场景", "测试磁盘 IO 性能", expected_mode="workflow", expected_scenario="storage_focus"),
            PromptCase("网络场景", "测试网络性能", expected_mode="workflow", expected_scenario="network_focus"),
        ]

        for case in cases:
            self.run_case(case)

        self.test_multi_turn()

        total = self.passed + self.failed
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
        self.log(f"总断言数: {total}", "INFO")
        self.log(f"通过: {self.passed}", "PASS" if self.passed else "INFO")
        self.log(f"失败: {self.failed}", "FAIL" if self.failed else "INFO")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")
        return 0 if self.failed == 0 else 1


def main():
    parser = argparse.ArgumentParser(description="Prompt 场景测试（接口 + OTel）")
    parser.add_argument("--host", default="127.0.0.1", help="后端地址")
    parser.add_argument("--port", type=int, default=10000, help="后端端口")
    parser.add_argument("--jaeger", default="http://127.0.0.1:16686", help="Jaeger API 根地址")
    parser.add_argument("-v", "--verbose", action="store_true", help="打印详细 trace 信息")
    args = parser.parse_args()

    tester = PromptCaseTester(
        host=args.host,
        port=args.port,
        jaeger_base=args.jaeger,
        verbose=args.verbose,
    )
    sys.exit(tester.run())


if __name__ == "__main__":
    main()
