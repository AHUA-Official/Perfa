"""
短时 benchmark 运行器
"""
import json
import os
import signal
import re
import socket
import subprocess
from typing import Any, Dict, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class _PackageRunner(BaseRunner):
    tool_name: str = ""
    binary_name: str = ""

    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        tool = tool_manager.get_tool(self.tool_name)
        if not tool:
            return False
        status = tool.check()
        status_value = status.get("status")
        if hasattr(status_value, "value"):
            status_value = status_value.value
        if status_value != "installed":
            return False
        self.binary_path = tool.binary_path or self.tool_name
        return True

    def _command(self) -> str:
        return getattr(self, "binary_path", None) or self.binary_name or self.tool_name

    def get_cleanup_patterns(self) -> List[str]:
        return [f"{self.name}_*", "*.tmp"]


class SysbenchCpuRunner(_PackageRunner):
    name = "sysbench_cpu"
    tool_name = "sysbench"
    binary_name = "sysbench"
    description = "sysbench CPU quick benchmark"
    category = "cpu"
    typical_duration_seconds = 30
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        max_prime = int(params.get("cpu_max_prime", 20000))
        duration = min(240, int(params.get("time", 30)))
        threads = int(params.get("threads", 1))
        return [self._command(), "cpu", f"--threads={threads}", f"--time={duration}", f"--cpu-max-prime={max_prime}", "run"]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        events = re.search(r"events per second:\s+([\d.]+)", output, re.IGNORECASE)
        latency = re.search(r"95th percentile:\s+([\d.]+)", output, re.IGNORECASE)
        total = re.search(r"total time:\s+([\d.]+)s", output, re.IGNORECASE)
        return {
            "events_per_sec": float(events.group(1)) if events else None,
            "latency_95th_ms": float(latency.group(1)) if latency else None,
            "total_time_sec": float(total.group(1)) if total else None,
        }


class SysbenchMemoryRunner(_PackageRunner):
    name = "sysbench_memory"
    tool_name = "sysbench"
    binary_name = "sysbench"
    description = "sysbench memory quick benchmark"
    category = "mem"
    typical_duration_seconds = 30
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        duration = min(240, int(params.get("time", 20)))
        threads = int(params.get("threads", 1))
        block_size = params.get("block_size", "1M")
        scope = params.get("scope", "global")
        op = params.get("operation", "read")
        return [
            self._command(), "memory",
            f"--threads={threads}",
            f"--time={duration}",
            f"--memory-block-size={block_size}",
            f"--memory-scope={scope}",
            f"--memory-oper={op}",
            "run",
        ]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        throughput = re.search(r"transferred.*?\(([\d.]+)\s+MiB/sec\)", output, re.IGNORECASE)
        operations = re.search(r"Operations performed:\s+(\d+)", output, re.IGNORECASE)
        return {
            "throughput_mib_s": float(throughput.group(1)) if throughput else None,
            "operations": int(operations.group(1)) if operations else None,
        }


class SysbenchThreadsRunner(_PackageRunner):
    name = "sysbench_threads"
    tool_name = "sysbench"
    binary_name = "sysbench"
    description = "sysbench threads quick benchmark"
    category = "cpu"
    typical_duration_seconds = 20
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        duration = min(180, int(params.get("time", 15)))
        threads = int(params.get("threads", 8))
        locks = int(params.get("locks", 64))
        yield_count = int(params.get("yield", 100))
        return [
            self._command(), "threads",
            f"--threads={threads}",
            f"--time={duration}",
            f"--thread-locks={locks}",
            f"--thread-yields={yield_count}",
            "run",
        ]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        events = re.search(r"events per second:\s+([\d.]+)", output, re.IGNORECASE)
        fairness = re.search(r"events \(avg/stddev\):\s+([\d.]+)/([\d.]+)", output, re.IGNORECASE)
        return {
            "events_per_sec": float(events.group(1)) if events else None,
            "events_avg": float(fairness.group(1)) if fairness else None,
            "events_stddev": float(fairness.group(2)) if fairness else None,
        }


class OpenSSLRunner(_PackageRunner):
    name = "openssl_speed"
    tool_name = "openssl_speed"
    binary_name = "openssl"
    description = "OpenSSL speed quick benchmark"
    category = "cpu"
    typical_duration_seconds = 20
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        seconds = min(120, int(params.get("seconds", 10)))
        algorithm = params.get("algorithm", "aes-256-cbc")
        return [self._command(), "speed", "-seconds", str(seconds), algorithm]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        algo = task.params.get("algorithm", "aes-256-cbc")
        lines = [line.strip() for line in output.splitlines() if algo in line]
        return {
            "algorithm": algo,
            "summary_line": lines[-1] if lines else None,
            "raw_output": output[-3000:],
        }


class StressNgRunner(_PackageRunner):
    name = "stress_ng"
    tool_name = "stress_ng"
    binary_name = "stress-ng"
    description = "stress-ng quick benchmark"
    category = "cpu"
    typical_duration_seconds = 45
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        mode = params.get("mode", "cpu")
        workers = int(params.get("workers", 1))
        timeout = min(240, int(params.get("timeout", 30)))
        return [
            self._command(),
            f"--{mode}", str(workers),
            "--timeout", f"{timeout}s",
            "--metrics-brief",
            "--json", "-",
        ]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        try:
            json_start = output.find("{")
            data = json.loads(output[json_start:]) if json_start != -1 else {}
            metrics = data.get("metrics", [])
            first = metrics[0] if metrics else {}
            return {
                "stressor": first.get("stressor"),
                "bogo_ops": first.get("bogo-ops"),
                "bogo_ops_per_sec": first.get("bogo-ops-per-second-real-time"),
            }
        except Exception:
            return {"raw_output": output[-3000:]}


class Iperf3Runner(_PackageRunner):
    name = "iperf3"
    tool_name = "iperf3"
    binary_name = "iperf3"
    description = "iperf3 short network throughput benchmark"
    category = "net"
    typical_duration_seconds = 20
    requires_async = False

    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        if not super().prepare(task, tool_manager):
            return False
        params = task.params or {}
        host = params.get("host") or params.get("server") or "127.0.0.1"
        port = int(params.get("port", 5201))
        auto_server = params.get("auto_server", False)

        if auto_server and self._is_local_target(host):
            server_log = os.path.join(task.working_dir or "/tmp", f"iperf3_server_{task.short_id}.log")
            proc = subprocess.Popen(
                [self._command(), "-s", "-1", "-p", str(port)],
                stdout=open(server_log, "w"),
                stderr=subprocess.STDOUT,
                text=True,
            )
            task.params["_iperf3_server_pid"] = proc.pid
            task.params["_iperf3_server_log"] = server_log
        return True

    def _is_local_target(self, host: str) -> bool:
        return host in {"127.0.0.1", "localhost", "::1", "0.0.0.0"}

    def _command(self) -> str:
        return getattr(self, "binary_path", None) or self.binary_name or self.tool_name

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        host = params.get("host") or params.get("server") or "127.0.0.1"
        port = int(params.get("port", 5201))
        duration = min(120, int(params.get("time", 10)))
        parallel = int(params.get("parallel", 1))
        reverse = params.get("reverse", False)
        cmd = [self._command(), "-c", host, "-p", str(port), "-t", str(duration), "-P", str(parallel), "-J"]
        if reverse:
            cmd.append("-R")
        return cmd

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        try:
            data = json.loads(output)
            end = data.get("end", {})
            sent = end.get("sum_sent", {})
            received = end.get("sum_received", {})
            return {
                "sent_mbps": round((sent.get("bits_per_second") or 0) / 1_000_000, 2),
                "received_mbps": round((received.get("bits_per_second") or 0) / 1_000_000, 2),
                "retransmits": sent.get("retransmits"),
            }
        except Exception:
            return {"raw_output": output[-3000:]}

    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        host = params.get("host") or params.get("server")
        if not host:
            return ["host/server is required for iperf3 benchmark"]
        return []

    def get_cleanup_patterns(self) -> List[str]:
        return super().get_cleanup_patterns() + ["iperf3_server_*"]


class SevenZipRunner(_PackageRunner):
    name = "7z_b"
    tool_name = "7z_b"
    binary_name = "7z"
    description = "7-Zip short benchmark"
    category = "cpu"
    typical_duration_seconds = 90
    requires_async = False

    def build_command(self, task: BenchmarkTask) -> List[str]:
        params = task.params or {}
        mm = params.get("method", "lzma2")
        threads = int(params.get("threads", 1))
        passes = int(params.get("passes", 3))
        return [self._command(), "b", f"-mm={mm}", f"-mmt={threads}", f"-md=32m", f"-p{passes}"]

    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        rating = re.findall(r"Rating.*?(\d+)\s+MIPS", output)
        usage = re.findall(r"CPU Freq:.*?(\d+)", output)
        return {
            "rating_mips": int(rating[-1]) if rating else None,
            "cpu_freq_mhz": int(usage[-1]) if usage else None,
            "raw_output": output[-3000:],
        }
