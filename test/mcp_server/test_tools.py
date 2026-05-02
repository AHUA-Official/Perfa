import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
MCP_DIR = SRC_DIR / "mcp_server"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(MCP_DIR))

from mcp_server.storage.database import Database
from mcp_server.storage.models import Server
from mcp_server.tools.benchmark_tools import RunBenchmarkTool
from mcp_server.tools.tool_tools import InstallToolTool, ListToolsTool


class MCPToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db = Database(str(Path(self.tmpdir.name) / "mcp.db"))
        now = datetime.now()
        self.server = Server(
            server_id="srv-1",
            ip="118.25.19.83",
            port=22,
            alias="web-server",
            agent_id="agent-1",
            agent_port=8080,
            ssh_user="ubuntu",
            ssh_password_encrypted="ssh-secret",
            ssh_key_path=None,
            privilege_mode="sudo_password",
            sudo_password_encrypted="sudo-secret",
            tags=[],
            created_at=now,
            updated_at=now,
        )
        self.db.create_server(self.server)

    def tearDown(self):
        self.tmpdir.cleanup()

    @patch("mcp_server.tools.tool_tools.AgentClient")
    def test_install_tool_passes_privilege_settings(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.health_check.return_value = True
        mock_client.install_tool.return_value = {"installed": True}

        tool = InstallToolTool(self.db)
        result = tool.execute(server_id="srv-1", tool_name="fio")

        self.assertTrue(result["success"])
        mock_client.install_tool.assert_called_once_with(
            "fio",
            privilege_mode="sudo_password",
            sudo_password="sudo-secret",
        )

    @patch("mcp_server.tools.benchmark_tools.AgentClient")
    def test_run_benchmark_updates_agent_config_before_start(self, mock_client_cls):
        mock_client = mock_client_cls.return_value
        mock_client.health_check.return_value = True
        mock_client.get_current_task.return_value = None
        mock_client.run_benchmark.return_value = "task-1"

        tool = RunBenchmarkTool(self.db)
        result = tool.execute(server_id="srv-1", test_name="fio", params={"rw": "randread"})

        self.assertTrue(result["success"])
        mock_client.update_config.assert_called_once_with(
            {
                "privilege_mode": "sudo_password",
                "sudo_password": "sudo-secret",
            }
        )
        mock_client.run_benchmark.assert_called_once_with("fio", {"rw": "randread"})

    def test_new_short_benchmarks_are_exposed_in_schemas(self):
        run_tool = RunBenchmarkTool(self.db)
        install_tool = InstallToolTool(self.db)
        list_tool = ListToolsTool(self.db)

        benchmark_enum = run_tool.input_schema["properties"]["test_name"]["enum"]
        tool_enum = install_tool.input_schema["properties"]["tool_name"]["enum"]
        categories = list_tool.input_schema["properties"]["category"]["enum"]

        self.assertIn("sysbench_cpu", benchmark_enum)
        self.assertIn("sysbench_memory", benchmark_enum)
        self.assertIn("sysbench_threads", benchmark_enum)
        self.assertIn("openssl_speed", benchmark_enum)
        self.assertIn("stress_ng", benchmark_enum)
        self.assertIn("iperf3", benchmark_enum)
        self.assertIn("7z_b", benchmark_enum)
        self.assertIn("sysbench", tool_enum)
        self.assertIn("iperf3", tool_enum)
        self.assertIn("network", categories)


if __name__ == "__main__":
    unittest.main()
