import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from langchain_agent.backend.openai_api import (
    ChatMessage,
    ChatRequest,
    AgentDeployRequest,
    chat_completions,
    deploy_server_agent,
)


class _FailingOrchestrator:
    async def process_query(self, query, session_id=None, conversation_id=None):
        return {
            "success": False,
            "is_success": False,
            "error": "backend failed",
        }


class _DeployTool:
    def __init__(self):
        self.args = None

    async def ainvoke(self, args):
        self.args = args
        return {"success": True, "agent_id": "agent-1"}


class _DeployOrchestrator:
    def __init__(self, tool):
        self.tools_dict = {"deploy_agent": tool}


class OpenAIAPITestCase(unittest.IsolatedAsyncioTestCase):
    @patch("langchain_agent.backend.openai_api.get_orchestrator")
    async def test_sync_chat_returns_502_for_business_failure(self, mock_get_orchestrator):
        mock_get_orchestrator.return_value = _FailingOrchestrator()
        request = ChatRequest(
            messages=[ChatMessage(role="user", content="run benchmark")],
            stream=False,
            session_id="session-1",
        )

        with self.assertRaises(HTTPException) as ctx:
            await chat_completions(request)

        self.assertEqual(ctx.exception.status_code, 502)

    @patch("langchain_agent.backend.openai_api.get_orchestrator")
    async def test_deploy_server_agent_passes_install_dir(self, mock_get_orchestrator):
        tool = _DeployTool()
        mock_get_orchestrator.return_value = _DeployOrchestrator(tool)

        req = AgentDeployRequest(
            force_reinstall=True,
            agent_only=True,
            install_dir="/home/ubuntu/Perfa",
        )

        result = await deploy_server_agent("srv-1", req)

        self.assertTrue(result["success"])
        self.assertEqual(tool.args["server_id"], "srv-1")
        self.assertEqual(tool.args["install_dir"], "/home/ubuntu/Perfa")


if __name__ == "__main__":
    unittest.main()
