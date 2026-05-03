import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_DIR))

from langchain_agent.workflows.nodes import (
    check_environment,
    check_tools,
    generate_report,
    install_tools,
    run_benchmark,
    route_after_server_selection,
    route_after_tool_check,
    route_after_install,
)
from langchain_agent.workflows.scenarios.quick_test import _infer_test_name


class _SyncTool:
    def __init__(self, fn):
        self._fn = fn

    def run(self, args):
        return self._fn(args)


class WorkflowNodesTestCase(unittest.IsolatedAsyncioTestCase):
    def test_quick_test_infers_new_short_benchmarks(self):
        self.assertEqual(_infer_test_name("帮我跑个 sysbench cpu"), "sysbench_cpu")
        self.assertEqual(_infer_test_name("做一个快速内存测试，sysbench memory"), "sysbench_memory")
        self.assertEqual(_infer_test_name("测试一下 iperf3 网络吞吐"), "iperf3")
        self.assertEqual(_infer_test_name("来个 openssl speed"), "openssl_speed")

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
                "tools": [
                    {"name": "unixbench", "status": "installed"},
                    {"name": "superpi", "status": "installed"},
                ],
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

    async def test_check_environment_only_keeps_installed_tools(self):
        state = {
            "scenario": "full_assessment",
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
                "tools": [
                    {"name": "sysbench", "status": "not_installed"},
                    {"name": "fio", "status": "installed"},
                    {"name": "iperf3", "status": "not_installed"},
                    {"name": "openssl_speed", "status": "installed"},
                ],
            }
        )

        result = await check_environment(
            state,
            tools={
                "list_servers": list_servers_tool,
                "list_tools": list_tools_tool,
            },
        )

        self.assertIn("fio", result["available_tools"])
        self.assertIn("openssl_speed", result["available_tools"])
        self.assertNotIn("sysbench", result["available_tools"])
        self.assertNotIn("iperf3", result["available_tools"])

    async def test_check_environment_prefers_preselected_server_id(self):
        state = {
            "scenario": "full_assessment",
            "server_id": "srv-118",
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        list_servers_tool = _SyncTool(
            lambda args: {
                "success": True,
                "servers": [
                    {
                        "server_id": "srv-49",
                        "ip": "49.234.47.133",
                        "agent_id": "",
                        "agent_status": "not_deployed",
                    },
                    {
                        "server_id": "srv-118",
                        "ip": "118.25.19.83",
                        "agent_id": "agent-118",
                        "agent_status": "online",
                    },
                ],
            }
        )
        list_tools_tool = _SyncTool(
            lambda args: {
                "success": True,
                "tools": [
                    {"name": "fio", "status": "installed"},
                ],
            }
        )

        result = await check_environment(
            state,
            tools={
                "list_servers": list_servers_tool,
                "list_tools": list_tools_tool,
            },
        )

        self.assertEqual(result["server_id"], "srv-118")
        self.assertEqual(result["server_ip"], "118.25.19.83")
        self.assertEqual(result["agent_status"], "online")

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

    async def test_generate_report_attaches_benchmark_knowledge_matches(self):
        state = {
            "scenario": "storage_focus",
            "server_ip": "127.0.0.1",
            "query": "分析 fio 随机读写性能",
            "results": {"fio": {"success": True, "metrics": {"read_iops": 1000}}},
            "errors": [],
            "node_statuses": {},
            "completed_nodes": [],
        }

        knowledge_tool = _SyncTool(
            lambda args: {
                "success": True,
                "matches": [
                    {
                        "title": "fio",
                        "path": "06-存储性能/fio.md",
                        "category": "storage",
                        "score": 42,
                        "snippet": "fio 可用于顺序读写、随机读写和延迟测试。",
                    }
                ],
            }
        )

        result = await generate_report(
            state,
            tools={"search_benchmark_knowledge": knowledge_tool},
        )

        self.assertEqual(result["node_statuses"]["generate_report"], "completed")
        self.assertEqual(result["knowledge_matches"][0]["path"], "06-存储性能/fio.md")
        self.assertIn("性能测试报告", result["final_report"])

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
