import unittest
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODE_AGENT_ROOT = PROJECT_ROOT / "src" / "node_agent"
sys.path.insert(0, str(NODE_AGENT_ROOT))

from tool.manager import ToolManager
from benchmark.runners.quick import (
    SysbenchCpuRunner,
    SysbenchMemoryRunner,
    SysbenchThreadsRunner,
    OpenSSLRunner,
    StressNgRunner,
    Iperf3Runner,
    SevenZipRunner,
)
from benchmark.task import BenchmarkTask, TaskStatus


class QuickBenchmarkRegistryTests(unittest.TestCase):
    def test_tool_manager_registers_quick_tools(self):
        manager = ToolManager()
        for tool_name in [
            "sysbench",
            "openssl_speed",
            "stress_ng",
            "iperf3",
            "7z_b",
        ]:
            self.assertIn(tool_name, manager.tools)

    def test_sysbench_cpu_default_is_short(self):
        runner = SysbenchCpuRunner()
        task = BenchmarkTask(task_id="t1", test_name="sysbench_cpu", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertIn("--time=30", cmd)
        self.assertIn("cpu", cmd)

    def test_sysbench_memory_default_is_short(self):
        runner = SysbenchMemoryRunner()
        task = BenchmarkTask(task_id="t2", test_name="sysbench_memory", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertIn("--time=20", cmd)
        self.assertIn("memory", cmd)

    def test_threads_default_is_short(self):
        runner = SysbenchThreadsRunner()
        task = BenchmarkTask(task_id="t3", test_name="sysbench_threads", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertIn("--time=15", cmd)
        self.assertIn("threads", cmd)

    def test_openssl_default_is_short(self):
        runner = OpenSSLRunner()
        task = BenchmarkTask(task_id="t4", test_name="openssl_speed", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertEqual(cmd[:3], ["openssl", "speed", "-seconds"])
        self.assertIn("10", cmd)

    def test_stress_ng_default_is_short(self):
        runner = StressNgRunner()
        task = BenchmarkTask(task_id="t5", test_name="stress_ng", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertIn("--timeout", cmd)
        self.assertIn("30s", cmd)
        self.assertIn("--metrics-brief", cmd)

    def test_iperf3_requires_host(self):
        runner = Iperf3Runner()
        self.assertEqual(runner.validate_params({}), ["host/server is required for iperf3 benchmark"])

    def test_iperf3_default_is_short(self):
        runner = Iperf3Runner()
        task = BenchmarkTask(task_id="t6", test_name="iperf3", params={"host": "127.0.0.1"}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertIn("-t", cmd)
        self.assertIn("10", cmd)
        self.assertIn("-J", cmd)

    def test_7z_default_is_short(self):
        runner = SevenZipRunner()
        task = BenchmarkTask(task_id="t7", test_name="7z_b", params={}, status=TaskStatus.PENDING)
        cmd = runner.build_command(task)
        self.assertEqual(cmd[1], "b")
        self.assertIn("-mm=lzma2", cmd)


if __name__ == "__main__":
    unittest.main()
