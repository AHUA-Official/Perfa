import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
MCP_DIR = SRC_DIR / "mcp_server"
sys.path.insert(0, str(SRC_DIR))
sys.path.insert(0, str(MCP_DIR))

from mcp_server.storage.database import Database
from mcp_server.storage.models import Server


class DatabaseTestCase(unittest.TestCase):
    def test_init_migrates_privilege_columns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "legacy.db"
            conn = sqlite3.connect(db_path)
            conn.execute(
                """
                CREATE TABLE servers (
                    server_id TEXT PRIMARY KEY,
                    ip TEXT NOT NULL,
                    port INTEGER DEFAULT 22,
                    alias TEXT DEFAULT '',
                    agent_id TEXT,
                    agent_port INTEGER,
                    ssh_user TEXT DEFAULT '',
                    ssh_password_encrypted TEXT,
                    ssh_key_path TEXT,
                    tags TEXT DEFAULT '[]',
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )
            conn.commit()
            conn.close()

            Database(str(db_path))

            conn = sqlite3.connect(db_path)
            columns = {
                row[1] for row in conn.execute("PRAGMA table_info(servers)").fetchall()
            }
            conn.close()

            self.assertIn("privilege_mode", columns)
            self.assertIn("sudo_password_encrypted", columns)

    def test_create_and_update_server_persists_privilege_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Database(str(Path(tmpdir) / "test.db"))
            now = datetime.now()
            server = Server(
                server_id="srv-1",
                ip="10.0.0.1",
                port=22,
                alias="web",
                agent_id="agent-1",
                agent_port=8080,
                ssh_user="ubuntu",
                ssh_password_encrypted="ssh-secret",
                ssh_key_path=None,
                privilege_mode="sudo_password",
                sudo_password_encrypted="sudo-secret",
                tags=["prod"],
                created_at=now,
                updated_at=now,
            )

            self.assertTrue(db.create_server(server))
            stored = db.get_server("srv-1")
            self.assertIsNotNone(stored)
            self.assertEqual(stored.privilege_mode, "sudo_password")
            self.assertEqual(stored.sudo_password_encrypted, "sudo-secret")

            server.alias = "web-2"
            server.privilege_mode = "sudo_nopasswd"
            db.update_server(server)

            updated = db.get_server("srv-1")
            self.assertEqual(updated.alias, "web-2")
            self.assertEqual(updated.privilege_mode, "sudo_nopasswd")


if __name__ == "__main__":
    unittest.main()
