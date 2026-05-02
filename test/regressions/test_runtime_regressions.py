import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
NODE_AGENT_DIR = SRC_DIR / "node_agent"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(NODE_AGENT_DIR))

from node_agent.tool.base import BaseTool, _is_package_manager_lock_error


class _DummyTool(BaseTool):
    def __init__(self):
        super().__init__(name="dummy", description="dummy", category="cpu")

    def install(self):
        return True

    def check(self):
        return {}

    def uninstall(self):
        return True


class RuntimeRegressionTests(unittest.TestCase):
    def test_package_manager_lock_error_detector_matches_apt_lock_messages(self):
        self.assertTrue(_is_package_manager_lock_error("Could not get lock /var/lib/dpkg/lock-frontend"))
        self.assertFalse(_is_package_manager_lock_error("package not found"))

    @patch("node_agent.tool.base.time.sleep")
    @patch("node_agent.tool.base.build_privileged_command")
    @patch("node_agent.tool.base.subprocess.run")
    def test_package_manager_command_retries_after_lock_conflict(
        self,
        mock_run,
        mock_build_privileged_command,
        _mock_sleep,
    ):
        tool = _DummyTool()
        mock_build_privileged_command.return_value = (["apt-get", "install"], None)

        class _Result:
            def __init__(self, returncode, stderr=""):
                self.returncode = returncode
                self.stdout = ""
                self.stderr = stderr

        mock_run.side_effect = [
            _Result(100, "Could not get lock /var/lib/dpkg/lock-frontend"),
            _Result(0, ""),
        ]

        with patch.object(tool, "_wait_for_apt_lock", return_value=True):
            code, _stdout, _stderr = tool._run_package_manager_command(["apt-get", "install", "fio"])

        self.assertEqual(code, 0)
        self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
