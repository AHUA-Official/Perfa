import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEBUI_SRC = PROJECT_ROOT / "webui-v2" / "src"


class WebUIPageContractTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (WEBUI_SRC / relative).read_text(encoding="utf-8")

    def test_home_page_contains_all_primary_navigation_entries(self):
        content = self.read("app/page.tsx")
        for label in ["对话", "服务器", "报告", "监控"]:
            self.assertIn(label, content)
        for key in ["key: 'chat'", "key: 'servers'", "key: 'reports'", "key: 'monitor'"]:
            self.assertIn(key, content)

    def test_chat_page_wires_sse_and_history_loading(self):
        content = self.read("components/chat/ChatPage.tsx")
        self.assertIn("consumeSSEStream", content)
        self.assertIn("listServers", content)
        self.assertIn("listSessions", content)
        self.assertIn("/v1/chat/completions", content)
        self.assertIn("workflowStatus", content)
        self.assertIn("traceId", content)

    def test_servers_page_covers_register_and_agent_actions(self):
        content = self.read("components/servers/ServersPage.tsx")
        self.assertIn("/api/v1/servers/register", content)
        self.assertIn("deployServerAgent", content)
        self.assertIn("uninstallServerAgent", content)
        self.assertIn("安装 Agent", content)
        self.assertIn("重装 Agent", content)
        self.assertIn("卸载 Agent", content)

    def test_reports_and_monitor_pages_have_runtime_empty_state_and_proxies(self):
        reports = self.read("components/reports/ReportsPage.tsx")
        monitor = self.read("components/monitor/MonitorPage.tsx")
        self.assertIn("暂无测试报告", reports)
        for proxy in ["/api/jaeger", "/api/grafana", "/api/vm"]:
            self.assertIn(proxy, monitor)
        self.assertIn("Perfa Agent API", monitor)
        self.assertIn("Jaeger 分布式链路追踪", monitor)


if __name__ == "__main__":
    unittest.main()
