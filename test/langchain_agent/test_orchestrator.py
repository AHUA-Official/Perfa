import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from langchain_agent.core.orchestrator import AgentOrchestrator


class _WorkflowEngine:
    async def run(self, scenario_name, query, session_id):
        return {
            "success": True,
            "result": "done",
            "node_statuses": {
                "select_server": "completed",
                "run_fio": "completed",
            },
            "completed_nodes": ["select_server", "run_fio"],
        }


class OrchestratorRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_workflow_sets_success_fields_and_current_node(self):
        orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
        orchestrator.workflow_engine = _WorkflowEngine()

        result = await AgentOrchestrator._run_workflow(
            orchestrator,
            "storage_focus",
            "test disk io",
            "session-1",
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["is_success"])
        self.assertEqual(result["mode"], "workflow")
        self.assertEqual(result["scenario"], "storage_focus")
        self.assertEqual(result["current_node"], "run_fio")


if __name__ == "__main__":
    unittest.main()
