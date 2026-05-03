import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = PROJECT_ROOT / "ops" / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))


class OpsScriptsTestCase(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (OPS_DIR / name).read_text(encoding="utf-8")

    def test_core_scripts_exist_with_shebang(self):
        for script in [
            "start-all.sh",
            "stop-all.sh",
            "status-all.sh",
            "start-mcp-server.sh",
        ]:
            path = OPS_DIR / script
            self.assertTrue(path.exists(), script)
            content = self._read(script)
            self.assertTrue(content.startswith("#!/bin/bash"), script)

    def test_start_local_waits_for_all_core_services(self):
        content = self._read("start-all.sh")
        self.assertIn("wait_for_http", content)
        self.assertIn("http://127.0.0.1:9000/sse?api_key=test-key-123", content)
        self.assertIn("http://127.0.0.1:10000/health", content)
        self.assertIn("http://127.0.0.1:3002", content)

    def test_status_local_reports_unavailable_instead_of_hiding_failures(self):
        content = self._read("status-all.sh")
        self.assertIn("UNAVAILABLE", content)
        self.assertNotIn("|| true", content)


if __name__ == "__main__":
    unittest.main()
