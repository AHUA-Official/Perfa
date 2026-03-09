from __future__ import annotations

from dataclasses import asdict

from mcp.server.fastmcp import FastMCP

from perfa_mvp1.config import SSHConfig
from perfa_mvp1.cpu_benchmark import run_cpu_test
from perfa_mvp1.db import get_cpu_history, get_server, init_db, list_servers, save_cpu_result, upsert_server
from perfa_mvp1.ssh_executor import SSHExecutor

mcp = FastMCP("perfa-mvp1")
init_db()


@mcp.tool()
def register_server(
    alias: str,
    host: str,
    username: str,
    port: int = 22,
    password: str | None = None,
    key_file: str | None = None,
    timeout: int = 15,
) -> dict:
    """注册或更新服务器配置（支持多台服务器）。"""
    if not password and not key_file:
        return {"ok": False, "error": "password 和 key_file 至少提供一个"}

    upsert_server(
        alias=alias,
        host=host,
        port=port,
        username=username,
        password=password,
        key_file=key_file,
        timeout=timeout,
    )
    return {"ok": True, "message": f"服务器 {alias} 已保存"}


@mcp.tool()
def list_registered_servers() -> dict:
    """列出已注册服务器（不返回密码）。"""
    return {"ok": True, "servers": list_servers()}


@mcp.tool()
def check_connection(server_alias: str) -> dict:
    """检查指定服务器的 SSH 连接是否可用。"""
    server = get_server(server_alias)
    if not server:
        return {"ok": False, "error": f"服务器不存在: {server_alias}，请先 register_server"}

    config = SSHConfig(
        host=server["host"],
        port=server["port"],
        username=server["username"],
        password=server["password"],
        key_file=server["key_file"],
        timeout=server["timeout"],
    )

    try:
        with SSHExecutor(config) as executor:
            code, stdout, stderr = executor.run("echo connection_ok", timeout=20)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"连接失败: {exc}"}

    return {
        "ok": code == 0,
        "server_alias": server_alias,
        "exit_code": code,
        "stdout": stdout.strip(),
        "stderr": stderr.strip(),
    }


@mcp.tool()
def benchmark_cpu(server_alias: str, threads: int = 1, save_result: bool = True) -> dict:
    """在指定服务器执行 sysbench CPU 测试，并可持久化结果到 SQLite。"""
    server = get_server(server_alias)
    if not server:
        return {"ok": False, "error": f"服务器不存在: {server_alias}，请先 register_server"}

    config = SSHConfig(
        host=server["host"],
        port=server["port"],
        username=server["username"],
        password=server["password"],
        key_file=server["key_file"],
        timeout=server["timeout"],
    )

    try:
        with SSHExecutor(config) as executor:
            result = run_cpu_test(executor, threads=threads)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"执行失败: {exc}"}

    result_dict = asdict(result)
    if save_result:
        save_cpu_result(server_alias, result_dict)

    return {
        "ok": result.exit_code == 0,
        "server_alias": server_alias,
        "result": result_dict,
        "saved": save_result,
    }


@mcp.tool()
def get_cpu_benchmark_history(server_alias: str, limit: int = 10) -> dict:
    """读取指定服务器历史 CPU 测试记录。"""
    server = get_server(server_alias)
    if not server:
        return {"ok": False, "error": f"服务器不存在: {server_alias}"}

    return {"ok": True, "server_alias": server_alias, "items": get_cpu_history(server_alias, limit=limit)}


if __name__ == "__main__":
    mcp.run()
