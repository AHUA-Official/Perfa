import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEBUI_DIR = PROJECT_ROOT / "webui-v2"
TSC_BIN = WEBUI_DIR / "node_modules" / ".bin" / "tsc"


class WebUIRuntimeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="perfa_webui_test_dist_"))
        compile_cmd = [
            str(TSC_BIN),
            "--module",
            "commonjs",
            "--target",
            "es2020",
            "--lib",
            "es2020,dom",
            "--esModuleInterop",
            "--skipLibCheck",
            "--outDir",
            str(cls.tmpdir),
            "src/lib/api.ts",
            "src/lib/sse.ts",
            "src/store/useChatStore.ts",
        ]
        subprocess.run(compile_cmd, cwd=WEBUI_DIR, check=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def run_node(self, script: str):
        env = os.environ.copy()
        env["NODE_PATH"] = str(WEBUI_DIR / "node_modules")
        result = subprocess.run(
            ["node", "-e", script],
            cwd=WEBUI_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_api_chat_completion_uses_expected_endpoint_and_payload(self):
        script = textwrap.dedent(
            f"""
            const calls = [];
            global.fetch = async (url, init) => {{
              calls.push({{ url, init }});
              return {{
                ok: true,
                json: async () => ({{
                  choices: [{{ message: {{ content: "ok" }} }}]
                }})
              }};
            }};
            const api = require({json.dumps(str(self.tmpdir / "lib" / "api.js"))});
            (async () => {{
              const result = await api.chatCompletion(
                [{{ role: "user", content: "hello" }}],
                {{ model: "perfa-agent", temperature: 0.2 }}
              );
              console.log(JSON.stringify({{ result, call: calls[0] }}));
            }})().catch((err) => {{
              console.error(err);
              process.exit(1);
            }});
            """
        )
        data = self.run_node(script)
        self.assertEqual(data["result"], "ok")
        self.assertEqual(data["call"]["url"], "/api/v1/chat/completions")
        payload = json.loads(data["call"]["init"]["body"])
        self.assertTrue(payload["stream"] is False)
        self.assertEqual(payload["messages"][0]["content"], "hello")

    def test_api_list_servers_degrades_to_empty_list_on_http_error(self):
        script = textwrap.dedent(
            f"""
            global.fetch = async () => ({{ ok: false, json: async () => ({{}}) }});
            const api = require({json.dumps(str(self.tmpdir / "lib" / "api.js"))});
            (async () => {{
              const result = await api.listServers();
              console.log(JSON.stringify({{ result }}));
            }})().catch((err) => {{
              console.error(err);
              process.exit(1);
            }});
            """
        )
        data = self.run_node(script)
        self.assertEqual(data["result"], [])

    def test_api_exposes_trace_and_latest_report_helpers(self):
        script = textwrap.dedent(
            f"""
            const calls = [];
            global.fetch = async (url) => {{
              calls.push(url);
              if (url === "/api/v1/reports") {{
                return {{ ok: true, json: async () => ({{ reports: [{{ id: "r1", server_id: "srv-1", created_at: "2026-05-02T10:00:00", status: "completed", type: "cpu_focus" }}] }}) }};
              }}
              if (url === "/api/v1/reports/r1") {{
                return {{ ok: true, json: async () => ({{ id: "r1", server_id: "srv-1", created_at: "2026-05-02T10:00:00", status: "completed", type: "cpu_focus", summary: "ok" }}) }};
              }}
              if (url === "/api/jaeger/api/traces/trace-1") {{
                return {{ ok: true, json: async () => ({{ data: [{{ spans: [{{ spanID: "s1", operationName: "run_fio", duration: 120000, tags: [{{ key: "error", value: false }}] }}] }}] }}) }};
              }}
              throw new Error("unexpected url " + url);
            }};
            const api = require({json.dumps(str(self.tmpdir / "lib" / "api.js"))});
            (async () => {{
              const report = await api.getLatestReport("srv-1");
              const trace = await api.getTraceSummary("trace-1");
              console.log(JSON.stringify({{ report, trace, calls }}));
            }})().catch((err) => {{
              console.error(err);
              process.exit(1);
            }});
            """
        )
        data = self.run_node(script)
        self.assertEqual(data["report"]["id"], "r1")
        self.assertEqual(data["trace"]["trace_id"], "trace-1")
        self.assertEqual(data["trace"]["span_count"], 1)

    def test_sse_parser_extracts_metadata_and_workflow(self):
        block = """data: {"choices":[{"delta":{},"index":0}],"metadata":{"type":"workflow_progress","current_node":"run_fio","status":"running","scenario":"storage_focus"},"session_id":"session-1","conversation_id":"conversation-1","trace_id":"trace-1","jaeger_url":"/api/jaeger/trace/trace-1","workflow":{"scenario":"storage_focus","node_statuses":{"run_fio":"running"},"completed_nodes":[],"current_node":"run_fio"}}"""
        script = textwrap.dedent(
            f"""
            const sse = require({json.dumps(str(self.tmpdir / "lib" / "sse.js"))});
            const result = sse.parseSSEEventBlock({json.dumps(block)});
            console.log(JSON.stringify(result));
            """
        )
        data = self.run_node(script)
        self.assertEqual(data["event"]["type"], "workflow_progress")
        self.assertEqual(data["event"]["current_node"], "run_fio")
        self.assertEqual(data["workflow"]["scenario"], "storage_focus")
        self.assertEqual(data["session_id"], "session-1")
        self.assertEqual(data["trace_id"], "trace-1")

    def test_chat_store_session_lifecycle(self):
        script = textwrap.dedent(
            f"""
            const store = require({json.dumps(str(self.tmpdir / "store" / "useChatStore.js"))}).useChatStore;
            const createdId = store.getState().createSession();
            const userMsgId = store.getState().addMessage({{ role: "user", content: "cpu benchmark" }});
            store.getState().setSessionId("session-123");
            const state = store.getState();
            console.log(JSON.stringify({{
              createdId,
              userMsgId,
              activeSessionId: state.activeSessionId,
              sessionId: state.sessionId,
              conversationId: state.conversationId,
              sessionsCount: state.sessions.length,
              firstTitle: state.sessions[0]?.title,
              firstMessage: state.messages[0]?.content
            }}));
            """
        )
        data = self.run_node(script)
        self.assertTrue(data["createdId"].startswith("pending_session"))
        self.assertEqual(data["sessionId"], "session-123")
        self.assertEqual(data["activeSessionId"], "session-123")
        self.assertEqual(data["conversationId"], "session-123")
        self.assertGreaterEqual(data["sessionsCount"], 1)
        self.assertIn("cpu benchmark", data["firstTitle"])
        self.assertEqual(data["firstMessage"], "cpu benchmark")


if __name__ == "__main__":
    unittest.main()
