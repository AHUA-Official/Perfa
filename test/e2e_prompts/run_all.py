#!/usr/bin/env python3
"""
Run all prompt-first E2E cases sequentially.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNNER = ROOT / "runner.py"
CASES = ROOT / "cases.json"


def main() -> int:
    import json

    cases = json.loads(CASES.read_text(encoding="utf-8"))
    overall = 0
    for case in cases:
        print(f"\n{'#' * 80}")
        print(f"RUN CASE: {case['id']} | {case['name']}")
        print(f"{'#' * 80}\n")
        result = subprocess.run(
            [sys.executable, str(RUNNER), "--case-id", case["id"]],
            cwd=ROOT.parent.parent,
        )
        if result.returncode != 0:
            overall = result.returncode
    return overall


if __name__ == "__main__":
    raise SystemExit(main())
