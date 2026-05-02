#!/usr/bin/env python3
"""
Prompt-first E2E runner.

目标：
1. 每个 prompt 单独触发一次真实 AI 会话
2. 打印 SSE 过程事件、最终回答、session detail、trace_id/jaeger_url
3. 不做强断言式“自动通过”，而是输出足够上下文供 AI / 人类审阅
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess
import tempfile

import requests
from requests.exceptions import RequestException


ROOT = Path(__file__).resolve().parent
CASES_PATH = ROOT / "cases.json"
AI_JUDGE = ROOT / "ai_judge.py"


class Printer:
    @staticmethod
    def line(title: str):
        print(f"\n{'=' * 24} {title} {'=' * 24}")

    @staticmethod
    def block(title: str, data: Any):
        print(f"\n--- {title} ---")
        if isinstance(data, (dict, list)):
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(data)


class PromptE2ERunner:
    def __init__(self, host: str, port: int):
        self.base_url = f"http://{host}:{port}/v1"

    def request(self, method: str, path: str, timeout: int = 180, **kwargs):
        url = f"{self.base_url}{path}"
        return requests.request(method, url, timeout=timeout, **kwargs)

    def load_cases(self) -> List[Dict[str, Any]]:
        return json.loads(CASES_PATH.read_text(encoding="utf-8"))

    def get_case(self, case_id: str) -> Dict[str, Any]:
        for case in self.load_cases():
            if case["id"] == case_id:
                return case
        raise KeyError(f"Unknown case_id: {case_id}")

    def stream_chat(self, prompt: str, session_id: str, conversation_id: str) -> Dict[str, Any]:
        payload = {
            "model": "perfa-agent",
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "session_id": session_id,
            "conversation_id": conversation_id,
        }
        response = self.request("POST", "/chat/completions", json=payload, stream=True)
        response.raise_for_status()

        chunks: List[Dict[str, Any]] = []
        text_parts: List[str] = []
        trace_id: Optional[str] = None
        jaeger_url: Optional[str] = None
        workflow: Optional[Dict[str, Any]] = None
        metadata_events: List[Dict[str, Any]] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data: "):
                continue
            raw = raw_line[6:]
            if raw == "[DONE]":
                break
            try:
                chunk = json.loads(raw)
            except json.JSONDecodeError:
                continue
            chunks.append(chunk)
            if chunk.get("trace_id"):
                trace_id = chunk["trace_id"]
            if chunk.get("jaeger_url"):
                jaeger_url = chunk["jaeger_url"]
            if chunk.get("workflow"):
                workflow = chunk["workflow"]
            meta = chunk.get("metadata")
            if meta:
                metadata_events.append(meta)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if delta.get("content"):
                text_parts.append(delta["content"])

        return {
            "chunks": chunks,
            "metadata_events": metadata_events,
            "final_text": "".join(text_parts),
            "trace_id": trace_id,
            "jaeger_url": jaeger_url,
            "workflow": workflow,
        }

    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        response = self.request("GET", f"/sessions/{session_id}", timeout=60)
        response.raise_for_status()
        return response.json()

    def build_review_summary(self, case: Dict[str, Any], result: Dict[str, Any], session_detail: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "case_id": case["id"],
            "case_name": case["name"],
            "prompt": case["prompt"],
            "trace_id": result.get("trace_id"),
            "jaeger_url": result.get("jaeger_url"),
            "workflow": result.get("workflow"),
            "event_count": len(result.get("metadata_events", [])),
            "session_id": session_detail.get("session_id"),
            "message_count": session_detail.get("message_count"),
            "last_user_message": session_detail.get("last_user_message"),
            "manual_review_required": True,
            "pass_rule": "根据最终回答、workflow、tool_result、session 历史、日志/trace 上下文，由 AI 或人工确认是否通过",
        }

    def run_ai_judge(self, case: Dict[str, Any], execution: Dict[str, Any]) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix="perfa_e2e_") as tmpdir:
            tmp = Path(tmpdir)
            case_file = tmp / "case.json"
            exec_file = tmp / "execution.json"
            case_file.write_text(json.dumps(case, ensure_ascii=False, indent=2), encoding="utf-8")
            exec_file.write_text(json.dumps(execution, ensure_ascii=False, indent=2), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(AI_JUDGE), str(case_file), str(exec_file)],
                capture_output=True,
                text=True,
                cwd=ROOT.parent.parent,
            )
            if proc.returncode != 0:
                return {
                    "verdict": "UNSURE",
                    "reason": "AI judge execution failed",
                    "confidence": 0,
                    "evidence": [proc.stderr.strip() or proc.stdout.strip()],
                }
            try:
                return json.loads(proc.stdout)
            except json.JSONDecodeError:
                return {
                    "verdict": "UNSURE",
                    "reason": "AI judge returned non-JSON output",
                    "confidence": 0,
                    "evidence": [proc.stdout.strip()],
                }

    def write_human_summary(self, case: Dict[str, Any], execution: Dict[str, Any], ai_judgement: Dict[str, Any]) -> Path:
        reports_dir = ROOT / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"{case['id']}.md"
        lines = [
            f"# {case['name']}",
            "",
            f"- case_id: `{case['id']}`",
            f"- ai_verdict: `{ai_judgement.get('verdict', 'UNSURE')}`",
            f"- ai_confidence: `{ai_judgement.get('confidence', '')}`",
            f"- trace_id: `{execution.get('trace_id')}`",
            f"- jaeger_url: `{execution.get('jaeger_url')}`",
            "",
            "## Prompt",
            "",
            case["prompt"],
            "",
            "## Expectations",
            "",
        ]
        lines.extend([f"- {item}" for item in case.get("expectations", [])])
        lines.extend([
            "",
            "## AI Judge",
            "",
            f"- verdict: `{ai_judgement.get('verdict', 'UNSURE')}`",
            f"- reason: {ai_judgement.get('reason', '')}",
            f"- evidence: {json.dumps(ai_judgement.get('evidence', []), ensure_ascii=False, indent=2)}",
            "",
            "## Human Review Checklist",
            "",
        ])
        lines.extend([f"- {item}" for item in case.get("review_hints", [])])
        lines.extend([
            "",
            "## Final Answer",
            "",
            execution.get("final_text", ""),
            "",
            "## Workflow",
            "",
            "```json",
            json.dumps(execution.get("workflow"), ensure_ascii=False, indent=2),
            "```",
            "",
            "## Session Detail",
            "",
            "```json",
            json.dumps(execution.get("session_detail"), ensure_ascii=False, indent=2),
            "```",
        ])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return report_path

    def run_case(self, case_id: str) -> int:
        case = self.get_case(case_id)
        session_id = f"e2e_session_{case_id}_{uuid.uuid4().hex[:8]}"
        conversation_id = f"e2e_conv_{case_id}_{uuid.uuid4().hex[:8]}"

        Printer.line(f"{case['name']} | {case_id}")
        Printer.block("Prompt", case["prompt"])
        Printer.block("Expectations", case.get("expectations", []))
        Printer.block("Review Hints", case.get("review_hints", []))
        Printer.block("Identifiers", {
            "session_id": session_id,
            "conversation_id": conversation_id,
        })

        started_at = time.time()
        try:
            result = self.stream_chat(case["prompt"], session_id, conversation_id)
            session_detail = self.get_session_detail(session_id)
            duration_sec = round(time.time() - started_at, 2)
        except RequestException as e:
            duration_sec = round(time.time() - started_at, 2)
            Printer.block("Execution Error", {
                "error_type": type(e).__name__,
                "error": str(e),
                "note": "当前执行环境无法直连后端时，也保留 prompt / expectation / identifiers 供人工审阅",
            })
            review_summary = {
                "case_id": case["id"],
                "case_name": case["name"],
                "prompt": case["prompt"],
                "session_id": session_id,
                "conversation_id": conversation_id,
                "manual_review_required": True,
                "pass_rule": "先确认环境连通后再复跑；当前输出仅作为场景定义和执行失败上下文",
            }
            Printer.block("Review Summary", review_summary)
            Printer.block("Execution Stats", {
                "duration_sec": duration_sec,
                "backend_reachable": False,
            })
            print("\nMANUAL_RESULT: REVIEW_REQUIRED")
            print("MANUAL_GUIDE: 当前环境无法连到后端，先修复连通性，再复跑这个 case")
            return 0

        execution = {
            "trace_id": result.get("trace_id"),
            "jaeger_url": result.get("jaeger_url"),
            "workflow": result.get("workflow"),
            "metadata_events": result.get("metadata_events", []),
            "final_text": result.get("final_text", ""),
            "session_detail": session_detail,
            "duration_sec": duration_sec,
        }
        ai_judgement = self.run_ai_judge(case, execution)
        report_path = self.write_human_summary(case, execution, ai_judgement)

        Printer.block("SSE Metadata Events", result["metadata_events"])
        Printer.block("Workflow", result.get("workflow"))
        Printer.block("Final Answer", result["final_text"])
        Printer.block("Session Detail", session_detail)
        Printer.block("Review Summary", self.build_review_summary(case, result, session_detail))
        Printer.block("AI Judge", ai_judgement)
        Printer.block("Human Summary Report", str(report_path))
        Printer.block("Execution Stats", {
            "duration_sec": duration_sec,
            "trace_id": result.get("trace_id"),
            "jaeger_url": result.get("jaeger_url"),
            "chunk_count": len(result.get("chunks", [])),
            "metadata_event_count": len(result.get("metadata_events", [])),
        })

        print("\nMANUAL_RESULT: REVIEW_REQUIRED")
        print("MANUAL_GUIDE: 查看上面的 final answer / workflow / metadata events / session detail，自行判断 PASS 或 FAIL")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Prompt-first E2E runner")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=10000)
    parser.add_argument("--case-id", required=True)
    args = parser.parse_args()

    runner = PromptE2ERunner(host=args.host, port=args.port)
    return runner.run_case(args.case_id)


if __name__ == "__main__":
    sys.exit(main())
