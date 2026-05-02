import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from langchain_agent.workflows.nodes import (
    check_environment,
    check_tools,
    install_tools,
    run_benchmark,
    route_after_server_selection,
    route_after_tool_check,
    route_after_install,
)


class _SyncTool:
    def __init__(self, fn):
        self._fn = fn

    def run(self, args):
        return self._fn(args)


class WorkflowNodesTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_check_environment_reads_server_id_from_list_servers_result(self):
        state = {
            "scenario": "cpu_focus",
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        list_servers_tool = _SyncTool(
            lambda args: {
                "success": True,
                "servers": [
                    {
                        "server_id": "srv-1",
                        "ip": "118.25.19.83",
                        "agent_id": "agent-1",
                        "agent_status": "online",
                    }
                ],
            }
        )
        list_tools_tool = _SyncTool(
            lambda args: {
                "success": True,
                "tools": [{"name": "unixbench"}, {"name": "superpi"}],
            }
        )

        result = await check_environment(
            state,
            tools={
                "list_servers": list_servers_tool,
                "list_tools": list_tools_tool,
            },
        )

        self.assertEqual(result["server_id"], "srv-1")
        self.assertEqual(result["server_ip"], "118.25.19.83")
        self.assertEqual(result["agent_status"], "online")
        self.assertIn("unixbench", result["available_tools"])
        self.assertEqual(result["node_statuses"]["check_environment"], "completed")

    async def test_check_tools_fails_fast_without_server_id(self):
        state = {
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        result = await check_tools(state, required_tools=["fio"])

        self.assertEqual(result["node_statuses"]["check_tools"], "failed")
        self.assertTrue(any(err["node"] == "check_tools" for err in result["errors"]))

    async def test_check_environment_marks_workflow_failed_when_no_servers(self):
        state = {
            "scenario": "cpu_focus",
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        list_servers_tool = _SyncTool(lambda args: {"success": True, "servers": [], "count": 0})

        result = await check_environment(
            state,
            tools={"list_servers": list_servers_tool},
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["node_statuses"]["check_environment"], "completed")
        self.assertTrue(any(err["node"] == "check_environment" for err in result["errors"]))

    async def test_install_tools_marks_failure_and_records_errors(self):
        state = {
            "server_id": "srv-1",
            "missing_tools": ["fio", "hping3"],
            "available_tools": [],
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        def install(args):
            if args["tool_name"] == "fio":
                return {"success": True}
            return {"success": False, "error": "sudo required"}

        result = await install_tools(state, tools={"install_tool": _SyncTool(install)})

        self.assertTrue(result["tool_install_failed"])
        self.assertIn("fio", result["available_tools"])
        self.assertIn("hping3", result["missing_tools"])
        self.assertEqual(result["node_statuses"]["install_tools"], "failed")
        self.assertTrue(any(err["node"] == "install_tools" for err in result["errors"]))

    async def test_install_tools_fails_fast_without_server_id(self):
        state = {
            "missing_tools": ["fio"],
            "available_tools": [],
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        result = await install_tools(state, tools={"install_tool": _SyncTool(lambda args: {"success": True})})

        self.assertTrue(result["tool_install_failed"])
        self.assertEqual(result["node_statuses"]["install_tools"], "failed")
        self.assertTrue(any(err["node"] == "install_tools" for err in result["errors"]))

    async def test_run_benchmark_skips_when_dependency_install_failed(self):
        state = {
            "server_id": "srv-1",
            "missing_tools": ["fio"],
            "tool_install_failed": True,
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        result = await run_benchmark(state, test_name="fio", tools={})

        self.assertEqual(result["node_statuses"]["run_fio"], "failed")
        self.assertTrue(any("跳过 fio 测试" in err["error"] for err in result["errors"]))

    async def test_run_benchmark_times_out_instead_of_marking_completed(self):
        state = {
            "server_id": "srv-1",
            "missing_tools": [],
            "tool_install_failed": False,
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
            "task_ids": {},
        }

        run_tool = _SyncTool(lambda args: {"task_id": "task-1"})
        status_tool = _SyncTool(lambda args: {"status": "running"})

        async def fast_sleep(_):
            return None

        from unittest.mock import patch

        with patch("langchain_agent.workflows.nodes.asyncio.sleep", fast_sleep):
            result = await run_benchmark(
                state,
                test_name="hping3",
                tools={
                    "run_benchmark": run_tool,
                    "get_benchmark_status": status_tool,
                },
            )

        self.assertEqual(result["node_statuses"]["run_hping3"], "failed")
        self.assertTrue(any("测试超时" in err["error"] for err in result["errors"]))

    def test_route_after_server_selection_handles_missing_server(self):
        self.assertEqual(
            route_after_server_selection({"node_statuses": {"select_server": "failed"}}),
            "handle_error",
        )
        self.assertEqual(
            route_after_server_selection({"server_id": "srv-1", "node_statuses": {"select_server": "completed"}}),
            "proceed",
        )

    def test_route_after_tool_check_handles_failed_check(self):
        self.assertEqual(
            route_after_tool_check({"node_statuses": {"check_tools": "failed"}}),
            "handle_error",
        )
        self.assertEqual(
            route_after_tool_check({"server_id": "srv-1", "missing_tools": ["fio"]}),
            "install_tools",
        )
        self.assertEqual(
            route_after_tool_check({"server_id": "srv-1", "missing_tools": []}),
            "proceed",
        )

    def test_route_after_install_handles_failed_install(self):
        self.assertEqual(
            route_after_install({"node_statuses": {"install_tools": "failed"}, "tool_install_failed": True}),
            "handle_error",
        )
        self.assertEqual(
            route_after_install({"node_statuses": {"install_tools": "completed"}, "tool_install_failed": False}),
            "proceed",
        )


if __name__ == "__main__":
    unittest.main()
