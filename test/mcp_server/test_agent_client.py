import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
MCP_DIR = SRC_DIR / "mcp_server"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(MCP_DIR))

from mcp_server.agent_client.client import AgentClient


class AgentClientTestCase(unittest.TestCase):
    @patch("mcp_server.agent_client.client.requests.request")
    def test_cancel_benchmark_accepts_cancelled_status(self, mock_request):
        response = Mock()
        response.json.return_value = {
            "success": True,
            "data": {"task_id": "task-1", "status": "cancelled"},
        }
        response.raise_for_status.return_value = None
        mock_request.return_value = response

        client = AgentClient("http://agent")
        self.assertTrue(client.cancel_benchmark("task-1"))

    @patch("mcp_server.agent_client.client.requests.request")
    def test_get_status_fills_defaults_for_degraded_agent_response(self, mock_request):
        response = Mock()
        response.json.return_value = {"success": True, "data": {"monitor_running": True}}
        response.raise_for_status.return_value = None
        mock_request.return_value = response

        client = AgentClient("http://agent")
        status = client.get_status()

        self.assertEqual(status.status, "online")
        self.assertEqual(status.agent_id, "unknown")
        self.assertEqual(status.version, "unknown")
        self.assertTrue(status.monitor_running)


if __name__ == "__main__":
    unittest.main()
