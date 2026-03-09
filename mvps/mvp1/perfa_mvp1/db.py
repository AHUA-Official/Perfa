from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

_DEFAULT_DB = Path(__file__).resolve().parents[1] / "perfa.db"


def get_db_path() -> Path:
    raw = os.getenv("PERFA_DB_PATH", "").strip()
    return Path(raw) if raw else _DEFAULT_DB


def _conn() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS servers (
                alias TEXT PRIMARY KEY,
                host TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 22,
                username TEXT NOT NULL,
                password TEXT,
                key_file TEXT,
                timeout INTEGER NOT NULL DEFAULT 15,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cpu_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_alias TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER NOT NULL,
                events_per_second REAL,
                total_time_sec REAL,
                latency_avg_ms REAL,
                raw_stdout TEXT NOT NULL,
                raw_stderr TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(server_alias) REFERENCES servers(alias)
            )
            """
        )


def upsert_server(
    *,
    alias: str,
    host: str,
    port: int,
    username: str,
    password: str | None,
    key_file: str | None,
    timeout: int,
) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO servers (alias, host, port, username, password, key_file, timeout, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET
                host=excluded.host,
                port=excluded.port,
                username=excluded.username,
                password=excluded.password,
                key_file=excluded.key_file,
                timeout=excluded.timeout,
                updated_at=excluded.updated_at
            """,
            (alias, host, port, username, password, key_file, timeout, now, now),
        )


def get_server(alias: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM servers WHERE alias = ?", (alias,)).fetchone()
    return dict(row) if row else None


def list_servers() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT alias, host, port, username, key_file, timeout, created_at, updated_at FROM servers ORDER BY alias"
        ).fetchall()
    return [dict(r) for r in rows]


def save_cpu_result(server_alias: str, result: dict[str, Any]) -> None:
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO cpu_results (
                server_alias, command, exit_code, events_per_second, total_time_sec,
                latency_avg_ms, raw_stdout, raw_stderr, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                server_alias,
                result["command"],
                result["exit_code"],
                result.get("events_per_second"),
                result.get("total_time_sec"),
                result.get("latency_avg_ms"),
                result.get("raw_stdout", ""),
                result.get("raw_stderr", ""),
                datetime.utcnow().isoformat(timespec="seconds"),
            ),
        )


def get_cpu_history(server_alias: str, limit: int = 10) -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, server_alias, command, exit_code, events_per_second, total_time_sec,
                   latency_avg_ms, created_at
            FROM cpu_results
            WHERE server_alias = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (server_alias, limit),
        ).fetchall()
    return [dict(r) for r in rows]
