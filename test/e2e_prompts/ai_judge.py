#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent.parent
LANGCHAIN_ENV = PROJECT_ROOT / "src" / "langchain_agent" / ".env"


def load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def build_judge_messages(case: Dict[str, Any], execution: Dict[str, Any]) -> list[dict[str, str]]:
    system = (
        "你是测试评审 AI。你要根据运行上下文判断一个 Agent 场景测试是否通过。"
        "只能输出 JSON，不要输出额外解释。"
        "JSON 必须包含 verdict、reason、confidence、evidence。"
        "verdict 只能是 PASS、FAIL、UNSURE。"
    )
    payload = {
        "case": {
            "id": case.get("id"),
            "name": case.get("name"),
            "prompt": case.get("prompt"),
            "expectations": case.get("expectations", []),
            "review_hints": case.get("review_hints", []),
        },
        "execution": execution,
    }
    user = f"{case.get('ai_judge_prompt')}\n\n上下文如下：\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _extract_json_payload(content: str) -> str:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return content


def judge_case(case: Dict[str, Any], execution: Dict[str, Any]) -> Dict[str, Any]:
    load_env_file(LANGCHAIN_ENV)
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=os.getenv("ZHIPU_MODEL", "glm-5"),
        api_key=os.getenv("ZHIPU_API_KEY"),
        base_url=os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"),
        temperature=0.0,
        max_tokens=2048,
    )
    response = model.invoke(build_judge_messages(case, execution))
    content = response.content if hasattr(response, "content") else str(response)
    try:
        return json.loads(_extract_json_payload(content))
    except json.JSONDecodeError:
        return {
            "verdict": "UNSURE",
            "reason": "Judge model did not return valid JSON",
            "confidence": 0,
            "evidence": [content],
            "raw_output": content,
        }


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: ai_judge.py <case_json> <execution_json>", file=sys.stderr)
        return 2
    case = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    execution = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    result = judge_case(case, execution)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
