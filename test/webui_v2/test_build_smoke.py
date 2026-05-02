import subprocess
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEBUI_DIR = PROJECT_ROOT / "webui-v2"


class WebUIBuildSmokeTests(unittest.TestCase):
    def test_next_build_succeeds(self):
        result = subprocess.run(
            ["npm", "run", "build"],
            cwd=WEBUI_DIR,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            self.fail(
                "webui-v2 build failed\n"
                f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            )


if __name__ == "__main__":
    unittest.main()
