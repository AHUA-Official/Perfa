import json
import subprocess
import unittest


def _run_curl(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["curl", "-sS", "--max-time", "10", *args],
        capture_output=True,
        text=True,
    )


@unittest.skip("Requires a stable local webui-v2 dev server; run manually when the local stack is up")
class WebUILiveSmokeTests(unittest.TestCase):
    def test_home_page_is_reachable(self):
        result = subprocess.run(
            ["curl", "-I", "-sS", "--max-time", "10", "http://127.0.0.1:3002"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("200 OK", result.stdout)

    def test_proxy_models_endpoint(self):
        result = _run_curl(["http://127.0.0.1:3002/api/v1/models"])
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        data = json.loads(result.stdout)
        ids = [item["id"] for item in data.get("data", [])]
        self.assertIn("perfa-agent", ids)

    def test_proxy_servers_and_reports_endpoints(self):
        for url in [
            "http://127.0.0.1:3002/api/v1/servers",
            "http://127.0.0.1:3002/api/v1/reports",
        ]:
            result = _run_curl([url])
            self.assertEqual(result.returncode, 0, f"{url}\n{result.stderr or result.stdout}")
            self.assertTrue(result.stdout.strip().startswith("{"))

    def test_sync_chat_round_trip(self):
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--max-time",
                "20",
                "-X",
                "POST",
                "http://127.0.0.1:3002/api/v1/chat/completions",
                "-H",
                "Content-Type: application/json",
                "-d",
                '{"model":"perfa-agent","messages":[{"role":"user","content":"你好，简单介绍一下你自己"}],"stream":false}',
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        data = json.loads(result.stdout)
        self.assertIn("choices", data)


if __name__ == "__main__":
    unittest.main()
