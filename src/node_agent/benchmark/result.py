"""
结果采集器
负责收集、存储和查询压测结果
"""
import configparser
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import platform

from .task import BenchmarkTask


logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """压测结果数据结构"""
    task_id: str
    test_name: str
    status: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    hostname: Optional[str] = None
    os_info: Optional[str] = None
    kernel_version: Optional[str] = None
    cpu_model: Optional[str] = None
    log_file: Optional[str] = None
    raw_output_file: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        for f in ['start_time', 'end_time', 'created_at']:
            if result.get(f) and isinstance(result[f], datetime):
                result[f] = result[f].isoformat()
        return result


class ResultCollector:
    """测试结果采集器"""

    def __init__(self, data_dir: str = "/var/lib/node_agent"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "benchmark_results.db"
        self.log_dir = self.data_dir / "logs"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS benchmark_results (
                task_id TEXT PRIMARY KEY, test_name TEXT NOT NULL, status TEXT NOT NULL,
                start_time TIMESTAMP, end_time TIMESTAMP, duration_seconds REAL,
                params TEXT, metrics TEXT, hostname TEXT, os_info TEXT,
                kernel_version TEXT, cpu_model TEXT, log_file TEXT,
                raw_output_file TEXT, error_message TEXT, created_at TIMESTAMP
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_test_name ON benchmark_results(test_name)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_start_time ON benchmark_results(start_time)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_status ON benchmark_results(status)")
        conn.commit()
        conn.close()

    def create_log_file(self, task: BenchmarkTask) -> Path:
        ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = self.log_dir / f"{ts}_{task.test_name}_{task.short_id}.log"
        with open(path, "w") as f:
            f.write("="*60 + "\n")
            f.write("Benchmark Task Log\n")
            f.write("="*60 + "\n\n")
            f.write(f"Task ID:     {task.task_id}\n")
            f.write(f"Test Name:   {task.test_name}\n")
            f.write(f"Start Time:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"\nParameters:\n{json.dumps(task.params, indent=2)}\n")
            f.write("\n" + "="*60 + "\n")
            f.write("Execution Log\n")
            f.write("="*60 + "\n\n")
        return path

    def append_log(self, log_path: Path, content: str):
        with open(log_path, "a") as f:
            f.write(content if content.endswith("\n") else content + "\n")

    def collect(self, task: BenchmarkTask, metrics: Optional[Dict] = None) -> BenchmarkResult:
        sys_info = self._get_system_info()
        metrics_with_evidence = dict(metrics or {})
        if task.environment_snapshot:
            metrics_with_evidence["environment_snapshot"] = task.environment_snapshot
        result = BenchmarkResult(
            task_id=task.task_id, test_name=task.test_name, status=task.status.value,
            start_time=task.start_time, end_time=task.end_time, duration_seconds=task.duration_seconds,
            params=task.params, metrics=metrics_with_evidence or None, hostname=sys_info['hostname'],
            os_info=sys_info['os_info'], kernel_version=sys_info['kernel_version'],
            cpu_model=sys_info['cpu_model'], log_file=task.log_file,
            raw_output_file=task.output_file, error_message=task.error, created_at=datetime.now()
        )
        self._save(result)
        return result

    def _get_system_info(self) -> Dict[str, str]:
        cpu = "Unknown"
        try:
            with open('/proc/cpuinfo') as f:
                for line in f:
                    if 'model name' in line:
                        cpu = line.split(':')[1].strip()
                        break
        except: pass
        
        # 正确获取系统信息
        os_info = "Unknown"
        try:
            # 读取 /etc/os-release 获取发行版信息
            with open('/etc/os-release') as f:
                lines = f.readlines()
                for line in lines:
                    if line.startswith('PRETTY_NAME='):
                        os_info = line.split('=')[1].strip().strip('"')
                        break
        except: pass
        
        return {
            'hostname': platform.node(),
            'os_info': os_info,
            'kernel_version': f"{platform.system()} {platform.release()}",  # Linux 5.15.0-xxx
            'cpu_model': cpu
        }

    def _save(self, r: BenchmarkResult):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""INSERT OR REPLACE INTO benchmark_results VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
            r.task_id, r.test_name, r.status,
            r.start_time.isoformat() if r.start_time else None,
            r.end_time.isoformat() if r.end_time else None,
            r.duration_seconds, json.dumps(r.params) if r.params else None,
            json.dumps(r.metrics) if r.metrics else None,
            r.hostname, r.os_info, r.kernel_version, r.cpu_model,
            r.log_file, r.raw_output_file, r.error_message,
            r.created_at.isoformat() if r.created_at else None
        ))
        conn.commit()
        conn.close()

    def get_result(self, task_id: str) -> Optional[BenchmarkResult]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM benchmark_results WHERE task_id=?", (task_id,))
        row = c.fetchone()
        conn.close()
        return self._row_to_result(row) if row else None

    def get_log_path(self, task_id: str) -> Optional[Path]:
        r = self.get_result(task_id)
        if r and r.log_file:
            p = Path(r.log_file)
            return p if p.exists() else None
        return None

    def list_results(self, test_name: str = None, status: str = None, limit: int = 100) -> List[BenchmarkResult]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        q, p = "SELECT * FROM benchmark_results WHERE 1=1", []
        if test_name: q, p = q + " AND test_name=?", p + [test_name]
        if status: q, p = q + " AND status=?", p + [status]
        c.execute(q + " ORDER BY start_time DESC LIMIT ?", p + [limit])
        rows = c.fetchall()
        conn.close()
        return [self._row_to_result(r) for r in rows]

    def _row_to_result(self, row) -> BenchmarkResult:
        return BenchmarkResult(
            task_id=row[0], test_name=row[1], status=row[2],
            start_time=datetime.fromisoformat(row[3]) if row[3] else None,
            end_time=datetime.fromisoformat(row[4]) if row[4] else None,
            duration_seconds=row[5], params=json.loads(row[6]) if row[6] else None,
            metrics=json.loads(row[7]) if row[7] else None,
            hostname=row[8], os_info=row[9], kernel_version=row[10], cpu_model=row[11],
            log_file=row[12], raw_output_file=row[13], error_message=row[14],
            created_at=datetime.fromisoformat(row[15]) if row[15] else None
        )

    def cleanup_old_logs(self, keep_days: int = 30) -> int:
        cutoff = datetime.now() - timedelta(days=keep_days)
        count = 0
        for f in self.log_dir.glob("*.log"):
            try:
                d = datetime.strptime(f.stem.split("_")[0], "%Y-%m-%d")
                if d < cutoff:
                    f.unlink()
                    count += 1
            except: pass
        return count
