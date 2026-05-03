import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODE_AGENT_ROOT = PROJECT_ROOT / "src" / "node_agent"
sys.path.insert(0, str(NODE_AGENT_ROOT))

from benchmark.executor import BenchmarkExecutor


class _DummyToolManager:
    def check_tool(self, tool_name):
        return {"status": "installed"}


class _AsyncRunner:
    name = "dummy_async"
    tool_name = "dummy_tool"
    requires_async = True

    def get_working_subdir(self, task):
        return task.task_id

    def prepare(self, task, tool_manager):
        return True

    def build_command(self, task):
        return ["/bin/sh", "-c", "sleep 1"]

    def get_timeout(self, params):
        return 5

    def collect_result(self, task, output):
        return {"ok": True}


class _SyncRunner(_AsyncRunner):
    name = "dummy_sync"
    requires_async = False

    def build_command(self, task):
        return ["/bin/sh", "-c", "printf done"]


class BenchmarkExecutorRuntimeTests(unittest.TestCase):
    def test_async_runner_returns_task_id_immediately(self):
        executor = BenchmarkExecutor(tool_manager=_DummyToolManager(), data_dir="/tmp/perfa_test_data")
        executor.register_runner(_AsyncRunner())

        result = executor.run_benchmark("dummy_async", {})

        self.assertIn("task_id", result)
        self.assertEqual(result["status"], "running")

    def test_environment_snapshot_is_persisted_in_metrics(self):
        snapshot = {
            "block_devices": [{"name": "sda", "scheduler": "mq-deadline"}],
            "memory": {"Cached_kb": 1234, "Dirty_kb": 0},
            "vm": {"swappiness": "60"},
        }
        with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as work_dir:
            executor = BenchmarkExecutor(
                tool_manager=_DummyToolManager(),
                data_dir=data_dir,
                working_dir=work_dir,
            )
            executor.register_runner(_SyncRunner())

            with mock.patch.object(executor.environment_collector, "collect", return_value=snapshot):
                result = executor.run_benchmark("dummy_sync", {})

            task_id = result["task_id"]
            stored = executor.get_result(task_id)

        self.assertEqual(result["result"]["metrics"]["ok"], True)
        self.assertEqual(result["result"]["metrics"]["environment_snapshot"], snapshot)
        self.assertEqual(stored["metrics"]["environment_snapshot"], snapshot)


if __name__ == "__main__":
    unittest.main()
