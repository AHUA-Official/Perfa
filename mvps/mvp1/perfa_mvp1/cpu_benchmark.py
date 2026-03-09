from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from .ssh_executor import SSHExecutor


@dataclass
class CpuBenchmarkResult:
    command: str
    exit_code: int
    events_per_second: float | None
    total_time_sec: float | None
    latency_avg_ms: float | None
    raw_stdout: str
    raw_stderr: str


def _extract_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def run_cpu_test(executor: SSHExecutor, threads: int = 1) -> CpuBenchmarkResult:
    command = f"sysbench cpu --threads={threads} run"
    exit_code, stdout, stderr = executor.run(command, timeout=180)

    return CpuBenchmarkResult(
        command=command,
        exit_code=exit_code,
        events_per_second=_extract_float(r"events per second:\\s+([\\d.]+)", stdout),
        total_time_sec=_extract_float(r"total time:\\s+([\\d.]+)s", stdout),
        latency_avg_ms=_extract_float(r"avg:\\s+([\\d.]+)", stdout),
        raw_stdout=stdout,
        raw_stderr=stderr,
    )


def to_pretty_json(result: CpuBenchmarkResult) -> str:
    return json.dumps(asdict(result), ensure_ascii=False, indent=2)
