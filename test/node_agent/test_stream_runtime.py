import sys
import unittest
from pathlib import Path
from unittest import mock

PROJECT_ROOT = Path(__file__).resolve().parents[2]
NODE_AGENT_ROOT = PROJECT_ROOT / "src" / "node_agent"
sys.path.insert(0, str(NODE_AGENT_ROOT))

from benchmark.cleaner import Cleaner
from benchmark.executor import BenchmarkExecutor
from benchmark.runners.stream import StreamRunner
from benchmark.task import BenchmarkTask


class _DummyProcess:
    def __init__(self):
        self.stdout = None

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0


class _DummyTool:
    binary_path = "/usr/local/bin/stream"

    def check(self):
        return {"status": "installed"}


class _DummyToolManager:
    def check_tool(self, tool_name):
        return {"status": "installed"}

    def get_tool(self, tool_name):
        return _DummyTool()


class StreamRuntimeTests(unittest.TestCase):
    def test_stream_runner_is_async(self):
        self.assertTrue(StreamRunner.requires_async)

    def test_cleaner_does_not_match_curl_payload_text(self):
        cleaner = Cleaner()

        self.assertFalse(
            cleaner._matches_residual_process(
                proc_name="curl",
                cmdline=[
                    "curl",
                    "-X",
                    "POST",
                    "http://127.0.0.1:8080/api/benchmark/run",
                    "-d",
                    '{"test_name":"stream"}',
                ],
                process_names=["stream"],
            )
        )

    def test_executor_passes_runner_environment_to_subprocess(self):
        executor = BenchmarkExecutor(tool_manager=_DummyToolManager(), data_dir="/tmp/perfa_test_data")
        runner = StreamRunner()
        task = BenchmarkTask(task_id="", test_name="stream", params={"array_size": 1000, "ntimes": 1, "nt": 3})
        task.working_dir = "/tmp/benchmark_work/test_stream"

        runner.prepare(task, executor.tool_manager)
        cmd = runner.build_command(task)

        with mock.patch("benchmark.executor.subprocess.Popen", return_value=_DummyProcess()) as popen:
            executor._execute_task(task, runner)

        _, kwargs = popen.call_args
        self.assertEqual(kwargs["env"]["STREAM_ARRAY_SIZE"], "1000")
        self.assertEqual(kwargs["env"]["NTIMES"], "1")
        self.assertEqual(kwargs["env"]["OMP_NUM_THREADS"], "3")
        self.assertEqual(cmd, ["/usr/local/bin/stream"])
        self.assertEqual(task.status.value, "completed")


if __name__ == "__main__":
    unittest.main()
