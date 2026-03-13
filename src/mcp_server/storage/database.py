"""数据库操作"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from .models import Server, Agent, Task


class Database:
    """SQLite 数据库操作"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 服务器表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS servers (
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
        """)
        
        # Agent 表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                status TEXT DEFAULT 'offline',
                version TEXT DEFAULT '',
                last_seen TIMESTAMP,
                created_at TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(server_id)
            )
        """)
        
        # 任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                server_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                test_name TEXT NOT NULL,
                params TEXT,
                status TEXT DEFAULT 'pending',
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                created_at TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(server_id),
                FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    # Server 操作
    
    def create_server(self, server: Server) -> bool:
        """创建服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO servers 
                (server_id, ip, port, alias, agent_id, agent_port, 
                 ssh_user, ssh_password_encrypted, ssh_key_path, tags, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                server.server_id, server.ip, server.port, server.alias,
                server.agent_id, server.agent_port, server.ssh_user,
                server.ssh_password_encrypted, server.ssh_key_path,
                json.dumps(server.tags), server.created_at, server.updated_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_server(self, server_id: str) -> Optional[Server]:
        """获取服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_server(row)
        return None
    
    def get_server_by_ip(self, ip: str) -> Optional[Server]:
        """通过 IP 获取服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers WHERE ip = ?", (ip,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_server(row)
        return None
    
    def list_servers(self) -> List[Server]:
        """列出所有服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM servers ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_server(row) for row in rows]
    
    def update_server(self, server: Server) -> bool:
        """更新服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE servers SET
                ip = ?, port = ?, alias = ?, agent_id = ?, agent_port = ?,
                ssh_user = ?, ssh_password_encrypted = ?, ssh_key_path = ?,
                tags = ?, updated_at = ?
                WHERE server_id = ?
            """, (
                server.ip, server.port, server.alias, server.agent_id, server.agent_port,
                server.ssh_user, server.ssh_password_encrypted, server.ssh_key_path,
                json.dumps(server.tags), server.updated_at, server.server_id
            ))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    
    def delete_server(self, server_id: str) -> bool:
        """删除服务器"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM servers WHERE server_id = ?", (server_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def _row_to_server(self, row: sqlite3.Row) -> Server:
        """将数据库行转换为 Server 对象"""
        return Server(
            server_id=row["server_id"],
            ip=row["ip"],
            port=row["port"],
            alias=row["alias"],
            agent_id=row["agent_id"],
            agent_port=row["agent_port"],
            ssh_user=row["ssh_user"],
            ssh_password_encrypted=row["ssh_password_encrypted"],
            ssh_key_path=row["ssh_key_path"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )
    
    # Agent 操作
    
    def create_agent(self, agent: Agent) -> bool:
        """创建 Agent"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO agents (agent_id, server_id, status, version, last_seen, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agent.agent_id, agent.server_id, agent.status,
                agent.version, agent.last_seen, agent.created_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取 Agent"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Agent(
                agent_id=row["agent_id"],
                server_id=row["server_id"],
                status=row["status"],
                version=row["version"],
                last_seen=datetime.fromisoformat(row["last_seen"]) if row["last_seen"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        return None
    
    def update_agent_status(self, agent_id: str, status: str, last_seen: Optional[datetime] = None):
        """更新 Agent 状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agents SET status = ?, last_seen = ? WHERE agent_id = ?
        """, (status, last_seen, agent_id))
        conn.commit()
        conn.close()
    
    # Task 操作
    
    def create_task(self, task: Task) -> bool:
        """创建任务"""
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO tasks 
                (task_id, server_id, agent_id, test_name, params, status, started_at, completed_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.task_id, task.server_id, task.agent_id, task.test_name,
                json.dumps(task.params), task.status, task.started_at, task.completed_at, task.created_at
            ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Task(
                task_id=row["task_id"],
                server_id=row["server_id"],
                agent_id=row["agent_id"],
                test_name=row["test_name"],
                params=json.loads(row["params"]),
                status=row["status"],
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            )
        return None
    
    def update_task_status(self, task_id: str, status: str, 
                          started_at: Optional[datetime] = None,
                          completed_at: Optional[datetime] = None):
        """更新任务状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks SET status = ?, started_at = ?, completed_at = ? WHERE task_id = ?
        """, (status, started_at, completed_at, task_id))
        conn.commit()
        conn.close()
    
    def list_tasks(self, server_id: Optional[str] = None, limit: int = 100) -> List[Task]:
        """列出任务"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        if server_id:
            cursor.execute("""
                SELECT * FROM tasks WHERE server_id = ? ORDER BY created_at DESC LIMIT ?
            """, (server_id, limit))
        else:
            cursor.execute("""
                SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?
            """, (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        tasks = []
        for row in rows:
            tasks.append(Task(
                task_id=row["task_id"],
                server_id=row["server_id"],
                agent_id=row["agent_id"],
                test_name=row["test_name"],
                params=json.loads(row["params"]),
                status=row["status"],
                started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
                completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
                created_at=datetime.fromisoformat(row["created_at"]),
            ))
        
        return tasks
