"""
Perfa - LangChain Agent Module

@file: workflows/nodes.py
@desc: LangGraph 工作流通用节点函数
@author: Perfa Team
@date: 2026-04-27
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional, Callable

from langchain_agent.core.logger import get_logger
logger = get_logger()

from langchain_agent.workflows.state import WorkflowState, create_initial_state


def _get_otel_tracer():
    """延迟获取 OTel tracer"""
    try:
        from langchain_agent.observability.tracer import get_tracer
        return get_tracer()
    except Exception:
        return None


def _otel_span(name: str, attributes: dict = None):
    """OTel span 上下文管理器（简化版）"""
    class _SpanCtx:
        def __init__(self, span_name, attrs):
            self.span_name = span_name
            self.attrs = attrs or {}
            self.span = None
            self.token = None

        async def __aenter__(self):
            tracer = _get_otel_tracer()
            if tracer:
                try:
                    from opentelemetry import context as otel_ctx, trace
                    self.span = tracer.start_span(self.span_name, attributes=self.attrs)
                    ctx = trace.set_span_in_context(self.span)
                    self.token = otel_ctx.attach(ctx)
                except Exception:
                    self.span = None
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self.span:
                try:
                    if exc_type:
                        self.span.record_exception(exc_val)
                        from opentelemetry.sdk.trace import Status, StatusCode
                        self.span.set_status(Status(StatusCode.ERROR, description=str(exc_val)[:200]))
                    self.span.end()
                except Exception:
                    pass
            if self.token:
                try:
                    from opentelemetry import context as otel_ctx
                    otel_ctx.detach(self.token)
                except Exception:
                    pass
            return False

        def set_attr(self, key, value):
            if self.span:
                try:
                    self.span.set_attribute(key, value)
                except Exception:
                    pass

    return _SpanCtx(name, attributes)


def _update_node_status(state: WorkflowState, node_name: str, status: str) -> dict:
    """更新节点状态的辅助函数，返回需要更新的字段"""
    node_statuses = dict(state.get("node_statuses", {}))
    node_statuses[node_name] = status
    completed_nodes = list(state.get("completed_nodes", []))
    if status == "completed" and node_name not in completed_nodes:
        completed_nodes.append(node_name)
    return {
        "current_node": node_name,
        "node_statuses": node_statuses,
        "completed_nodes": completed_nodes,
    }


def _parse_tool_result_payload(result: Any) -> dict:
    """统一解析 MCP/LangChain 工具返回的 dict/string 结果"""
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def _extract_server_identity(server: dict) -> tuple[str, str, str, str]:
    """兼容不同服务器字段命名"""
    server_id = server.get("server_id") or server.get("id") or ""
    server_ip = server.get("ip") or server.get("host") or ""
    agent_id = server.get("agent_id") or ""
    agent_status = server.get("agent_status") or server.get("status") or "unknown"
    return server_id, server_ip, agent_id, agent_status


def make_node(fn: Callable, **kwargs) -> Callable:
    """
    节点工厂函数
    
    将 async 节点函数 + 固定参数 包装为 LangGraph 兼容的 async 节点。
    LangGraph 要求 add_node 接收的函数签名为 fn(state) -> dict，
    此工厂函数将额外参数（tools, llm 等）通过闭包绑定。
    
    同时自动注入 OTel span 追踪，记录节点输入/输出/决策。
    
    用法:
        graph.add_node("check_env", make_node(check_environment, tools=tools))
    """
    async def node(state: WorkflowState) -> dict:
        span_name = f"workflow.node.{fn.__name__}"
        scenario = state.get("scenario", "unknown")
        async with _otel_span(span_name, {"node": fn.__name__, "scenario": scenario}) as sctx:
            start = time.monotonic()
            try:
                # 记录节点输入摘要（给 AI 分析用）
                input_summary = {
                    "server_id": state.get("server_id", ""),
                    "server_ip": state.get("server_ip", ""),
                    "available_tools": state.get("available_tools", [])[:10],
                    "errors_count": len(state.get("errors", [])),
                    "completed_nodes": state.get("completed_nodes", []),
                }
                if sctx.span:
                    sctx.span.add_event("node.input", {
                        "state_summary": json.dumps(input_summary, ensure_ascii=False, default=str)[:1000],
                    })
                
                result = await fn(state, **kwargs)
                duration = time.monotonic() - start
                sctx.set_attr("duration_seconds", duration)
                # 记录节点完成状态
                node_status = result.get("node_statuses", {}).get(fn.__name__, "unknown")
                sctx.set_attr("node_status", node_status)
                
                # 记录节点输出摘要（给 AI 分析用）
                output_keys = list(result.keys())
                output_summary = {}
                for k in output_keys:
                    v = result[k]
                    if isinstance(v, (str, int, float, bool)):
                        output_summary[k] = v
                    elif isinstance(v, list):
                        output_summary[k] = f"[{len(v)} items]"
                    elif isinstance(v, dict):
                        output_summary[k] = f"{{{len(v)} keys}}"
                    else:
                        output_summary[k] = str(type(v).__name__)
                
                if sctx.span:
                    sctx.span.add_event("node.output", {
                        "status": node_status,
                        "output_keys": json.dumps(output_summary, ensure_ascii=False, default=str)[:500],
                        "duration_seconds": duration,
                    })
                
                # 记录压测指标
                if fn.__name__.startswith("run_") or "benchmark" in fn.__name__:
                    try:
                        from langchain_agent.observability.instrument_agent import record_benchmark_metrics
                        record_benchmark_metrics(
                            fn.__name__, duration,
                            node_status == "completed",
                            state.get("server_id", "")
                        )
                    except Exception:
                        pass
                return result
            except Exception as e:
                sctx.set_attr("error", str(e)[:200])
                if sctx.span:
                    sctx.span.add_event("node.error", {
                        "error_type": type(e).__name__,
                        "error_message": str(e)[:500],
                    })
                raise
    node.__name__ = fn.__name__
    return node


async def check_environment(state: WorkflowState, *, tools: dict = None) -> dict:
    """
    节点: 环境检查
    
    检查 MCP Server 连接是否正常，获取已注册服务器列表和可用工具列表。
    """
    logger.info(f"[Workflow] 环境检查节点开始，场景: {state.get('scenario')}")
    updates = _update_node_status(state, "check_environment", "running")
    
    # OTel: 获取当前 span 记录决策过程
    _current_span = None
    try:
        from opentelemetry import trace
        _current_span = trace.get_current_span()
    except Exception:
        pass
    
    try:
        # 调用 list_servers 获取服务器列表
        list_servers_tool = tools.get("list_servers")
        if list_servers_tool:
            if hasattr(list_servers_tool, 'ainvoke'):
                servers_result = await list_servers_tool.ainvoke({})
            else:
                servers_result = list_servers_tool.run({})
            
            servers = []
            parsed_servers_result = _parse_tool_result_payload(servers_result)
            if parsed_servers_result.get("success") is False:
                raise RuntimeError(parsed_servers_result.get("error", "list_servers 调用失败"))
            if parsed_servers_result:
                servers = parsed_servers_result.get("servers", [])
            
            if servers:
                first_server = servers[0]
                server_id, server_ip, agent_id, agent_status = _extract_server_identity(first_server)
                
                if server_id:
                    updates["server_id"] = server_id
                if server_ip:
                    updates["server_ip"] = server_ip
                updates["agent_id"] = agent_id
                updates["agent_status"] = agent_status
                
                # OTel: 记录服务器选择决策
                if _current_span and _current_span.is_recording():
                    _current_span.add_event("decision.server_selected", {
                        "server_ip": server_ip,
                        "server_id": server_id,
                        "agent_status": agent_status,
                        "total_servers_found": len(servers),
                        "reason": "first_available" if len(servers) == 1 else "default_first",
                    })
                
                logger.info(f"[Workflow] 找到服务器: {server_ip} (ID: {server_id})")
            else:
                logger.warning("[Workflow] 没有找到已注册的服务器")
                updates["errors"] = list(state.get("errors", [])) + [{
                    "node": "check_environment",
                    "error": "没有已注册的服务器",
                    "detail": "请先注册服务器并部署 Agent"
                }]
                updates["status"] = "failed"
                if _current_span and _current_span.is_recording():
                    _current_span.add_event("decision.no_server", {
                        "reason": "no_registered_servers",
                    })
        else:
            logger.warning("[Workflow] list_servers 工具不可用")
            if _current_span and _current_span.is_recording():
                _current_span.add_event("decision.tool_unavailable", {
                    "tool_name": "list_servers",
                })
        
        # 调用 list_tools 获取可用工具列表
        list_tools_tool = tools.get("list_tools")
        target_server_id = updates.get("server_id", state.get("server_id", ""))
        if list_tools_tool and target_server_id:
            if hasattr(list_tools_tool, 'ainvoke'):
                tools_result = await list_tools_tool.ainvoke({"server_id": target_server_id})
            else:
                tools_result = list_tools_tool.run({"server_id": target_server_id})
            
            available_tools = []
            parsed_tools_result = _parse_tool_result_payload(tools_result)
            if parsed_tools_result.get("success") is False:
                raise RuntimeError(parsed_tools_result.get("error", "list_tools 调用失败"))
            tool_list = parsed_tools_result.get("tools", [])
            available_tools = [t.get("name", "") for t in tool_list if isinstance(t, dict)]
            
            updates["available_tools"] = available_tools
            logger.info(f"[Workflow] 可用工具: {available_tools}")
        elif list_tools_tool and not target_server_id:
            logger.warning("[Workflow] 跳过 list_tools：当前没有有效的 server_id")
        
        updates.update(_update_node_status(state, "check_environment", "completed"))
        logger.info("[Workflow] 环境检查完成")
        
    except Exception as e:
        logger.error(f"[Workflow] 环境检查失败: {e}")
        updates.update(_update_node_status(state, "check_environment", "failed"))
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": "check_environment",
            "error": str(e),
            "detail": "环境检查过程中发生异常"
        }]
    
    return updates


async def select_server(state: WorkflowState, *, tools: dict = None) -> dict:
    """
    节点: 选择服务器
    
    如果 check_environment 已选定服务器则直接使用，否则尝试从查询中解析服务器信息。
    """
    logger.info("[Workflow] 选择服务器节点开始")
    updates = _update_node_status(state, "select_server", "running")
    
    if state.get("server_id"):
        logger.info(f"[Workflow] 使用已选定的服务器: {state.get('server_ip')}")
        updates.update(_update_node_status(state, "select_server", "completed"))
        return updates
    
    list_servers_tool = tools.get("list_servers")
    if list_servers_tool:
        try:
            if hasattr(list_servers_tool, 'ainvoke'):
                servers_result = await list_servers_tool.ainvoke({})
            else:
                servers_result = list_servers_tool.run({})

            servers = []
            parsed_servers_result = _parse_tool_result_payload(servers_result)
            if parsed_servers_result.get("success") is False:
                raise RuntimeError(parsed_servers_result.get("error", "list_servers 调用失败"))
            if parsed_servers_result:
                servers = parsed_servers_result.get("servers", [])

            if servers:
                # 尝试匹配用户查询中的 IP
                query = state.get("query", "")
                selected = None
                for s in servers:
                    server_ip = s.get("ip", s.get("host", ""))
                    server_alias = s.get("alias", s.get("name", ""))
                    if server_ip and server_ip in query:
                        selected = s
                        break
                    if server_alias and server_alias in query:
                        selected = s
                        break

                # 没匹配到就用第一台
                if not selected:
                    selected = servers[0]

                server_id, server_ip, agent_id, agent_status = _extract_server_identity(selected)
                updates["server_id"] = server_id
                updates["server_ip"] = server_ip
                updates["agent_id"] = agent_id
                updates["agent_status"] = agent_status
                logger.info(f"[Workflow] 选择服务器: {updates['server_ip']} (id={updates['server_id']})")
        except Exception as e:
            logger.error(f"[Workflow] 选择服务器失败: {e}")
    
    if not updates.get("server_id"):
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": "select_server",
            "error": "无法选择目标服务器",
            "detail": "没有可用的服务器"
        }]
        updates["status"] = "failed"
        updates.update(_update_node_status(state, "select_server", "failed"))
    else:
        updates.update(_update_node_status(state, "select_server", "completed"))
    
    return updates


async def check_tools(state: WorkflowState, *, required_tools: list = None, tools: dict = None) -> dict:
    """
    节点: 检查所需工具是否已安装
    """
    logger.info(f"[Workflow] 检查工具节点开始，所需工具: {required_tools}")
    updates = _update_node_status(state, "check_tools", "running")

    if not state.get("server_id"):
        updates["missing_tools"] = list(required_tools or [])
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": "check_tools",
            "error": "无法检查工具",
            "detail": "当前没有有效的 server_id",
        }]
        updates.update(_update_node_status(state, "check_tools", "failed"))
        return updates
    
    available = set(state.get("available_tools", []))
    required = set(required_tools or [])
    missing = required - available
    
    updates["missing_tools"] = list(missing)
    updates["available_tools"] = list(available)
    
    if missing:
        logger.warning(f"[Workflow] 缺少工具: {missing}")
    else:
        logger.info("[Workflow] 所需工具均已安装")
    
    updates.update(_update_node_status(state, "check_tools", "completed"))
    return updates


async def install_tools(state: WorkflowState, *, tools: dict = None) -> dict:
    """
    节点: 安装缺失工具
    """
    missing = state.get("missing_tools", [])
    logger.info(f"[Workflow] 安装工具节点开始，缺失工具: {missing}")
    updates = _update_node_status(state, "install_tools", "running")
    
    server_id = state.get("server_id", "")
    install_tool = tools.get("install_tool")

    if not server_id:
        updates["tool_install_failed"] = True
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": "install_tools",
            "error": "无法安装工具",
            "detail": "当前没有有效的 server_id",
        }]
        updates.update(_update_node_status(state, "install_tools", "failed"))
        return updates
    
    if not missing or not install_tool:
        logger.info("[Workflow] 无需安装工具或 install_tool 不可用")
        updates.update(_update_node_status(state, "install_tools", "completed"))
        return updates
    
    installed = []
    failed_tools = []
    errors = list(state.get("errors", []))
    for tool_name in missing:
        try:
            args = {"server_id": server_id, "tool_name": tool_name}
            if hasattr(install_tool, 'ainvoke'):
                result = await install_tool.ainvoke(args)
            else:
                result = install_tool.run(args)
            
            if isinstance(result, dict) and result.get("success"):
                installed.append(tool_name)
                logger.info(f"[Workflow] 工具 {tool_name} 安装成功")
            else:
                logger.warning(f"[Workflow] 工具 {tool_name} 安装失败: {result}")
                failed_tools.append(tool_name)
                errors.append({
                    "node": "install_tools",
                    "error": f"工具 {tool_name} 安装失败",
                    "detail": str(result),
                })
        except Exception as e:
            logger.error(f"[Workflow] 安装工具 {tool_name} 异常: {e}")
            failed_tools.append(tool_name)
            errors.append({
                "node": "install_tools",
                "error": f"工具 {tool_name} 安装异常",
                "detail": str(e),
            })
    
    available = set(state.get("available_tools", []))
    available.update(installed)
    updates["available_tools"] = list(available)
    updates["missing_tools"] = [t for t in missing if t not in installed]
    updates["tool_install_failed"] = bool(failed_tools)
    if failed_tools:
        updates["errors"] = errors
        updates.update(_update_node_status(state, "install_tools", "failed"))
    else:
        updates.update(_update_node_status(state, "install_tools", "completed"))
    return updates


async def run_benchmark(state: WorkflowState, *, test_name: str, test_params: dict = None, tools: dict = None, result_key: str = None) -> dict:
    """
    节点: 执行压测
    
    调用 run_benchmark 工具启动测试，然后轮询等待结果。
    """
    key = result_key or test_name
    logger.info(f"[Workflow] 执行压测节点开始: {test_name}")
    updates = _update_node_status(state, f"run_{test_name}", "running")
    
    # OTel: 获取当前 span
    _current_span = None
    try:
        from opentelemetry import trace
        _current_span = trace.get_current_span()
    except Exception:
        pass
    
    server_id = state.get("server_id", "")
    run_tool = tools.get("run_benchmark")
    status_tool = tools.get("get_benchmark_status")
    result_tool = tools.get("get_benchmark_result")
    missing_tools = set(state.get("missing_tools", []))

    if state.get("tool_install_failed") or test_name in missing_tools:
        detail = "依赖工具安装失败" if state.get("tool_install_failed") else f"{test_name} 仍未安装"
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": f"run_{test_name}",
            "error": f"跳过 {test_name} 测试",
            "detail": detail,
        }]
        updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
        return updates
    
    if not run_tool:
        logger.error("[Workflow] run_benchmark 工具不可用")
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": f"run_{test_name}",
            "error": "run_benchmark 工具不可用",
            "detail": f"无法执行 {test_name} 测试"
        }]
        updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
        if _current_span and _current_span.is_recording():
            _current_span.add_event("benchmark.tool_unavailable", {
                "test_name": test_name,
                "server_id": server_id,
            })
        return updates
    
    try:
        args = {
            "server_id": server_id,
            "test_name": test_name,
        }
        if test_params:
            args["params"] = json.dumps(test_params)
        
        # OTel: 记录压测启动参数
        if _current_span and _current_span.is_recording():
            _current_span.add_event("benchmark.starting", {
                "test_name": test_name,
                "server_id": server_id,
                "params": json.dumps(test_params or {}, ensure_ascii=False)[:500],
            })
        
        if hasattr(run_tool, 'ainvoke'):
            start_result = await run_tool.ainvoke(args)
        else:
            start_result = run_tool.run(args)
        
        task_id = None
        if isinstance(start_result, dict):
            task_id = start_result.get("task_id")
        elif isinstance(start_result, str):
            try:
                parsed = json.loads(start_result)
                task_id = parsed.get("task_id")
            except json.JSONDecodeError:
                pass
        
        if not task_id:
            logger.error(f"[Workflow] 启动 {test_name} 测试失败，未返回 task_id")
            updates["errors"] = list(state.get("errors", [])) + [{
                "node": f"run_{test_name}",
                "error": "未获取到 task_id",
                "detail": str(start_result)
            }]
            updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
            if _current_span and _current_span.is_recording():
                _current_span.add_event("benchmark.start_failed", {
                    "test_name": test_name,
                    "start_result": str(start_result)[:500],
                })
            return updates
        
        logger.info(f"[Workflow] {test_name} 测试已启动，task_id: {task_id}")
        
        # OTel: 记录启动成功
        if _current_span and _current_span.is_recording():
            _current_span.add_event("benchmark.started", {
                "test_name": test_name,
                "task_id": task_id,
                "server_id": server_id,
            })
        
        task_ids = dict(state.get("task_ids", {}))
        task_ids[key] = task_id
        updates["task_ids"] = task_ids
        
        # 轮询等待结果
        max_wait_by_test = {
            "unixbench": 3600,
            "fio": 1800,
            "stream": 900,
            "superpi": 900,
            "mlc": 900,
            "hping3": 300,
        }
        max_wait = max_wait_by_test.get(test_name, 600)
        poll_interval = 5
        elapsed = 0
        last_status = ""
        
        while elapsed < max_wait:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            
            if status_tool:
                try:
                    status_args = {"server_id": server_id, "task_id": task_id}
                    if hasattr(status_tool, 'ainvoke'):
                        status_result = await status_tool.ainvoke(status_args)
                    else:
                        status_result = status_tool.run(status_args)
                    
                    status = ""
                    if isinstance(status_result, dict):
                        status = status_result.get("status", "")
                    elif isinstance(status_result, str):
                        try:
                            parsed = json.loads(status_result)
                            status = parsed.get("status", "")
                        except json.JSONDecodeError:
                            pass
                    
                    last_status = status
                    logger.info(f"[Workflow] {test_name} 状态: {status} (已等待 {elapsed}s)")
                    
                    if status in ("completed", "done", "success"):
                        break
                    elif status in ("failed", "error"):
                        updates["errors"] = list(state.get("errors", [])) + [{
                            "node": f"run_{test_name}",
                            "error": f"{test_name} 测试失败",
                            "detail": str(status_result)
                        }]
                        updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
                        # OTel: 记录测试失败
                        if _current_span and _current_span.is_recording():
                            _current_span.add_event("benchmark.failed", {
                                "test_name": test_name,
                                "task_id": task_id,
                                "status": status,
                                "waited_seconds": elapsed,
                                "error_detail": str(status_result)[:500],
                            })
                        return updates
                except Exception as e:
                    logger.warning(f"[Workflow] 查询状态异常: {e}")

        if elapsed >= max_wait and last_status not in ("completed", "done", "success"):
            logger.error(f"[Workflow] {test_name} 测试超时，最后状态: {last_status}")
            updates["errors"] = list(state.get("errors", [])) + [{
                "node": f"run_{test_name}",
                "error": f"{test_name} 测试超时",
                "detail": f"等待 {elapsed}s 后仍未完成，最后状态: {last_status or 'unknown'}"
            }]
            updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
            if _current_span and _current_span.is_recording():
                _current_span.add_event("benchmark.timeout", {
                    "test_name": test_name,
                    "task_id": task_id,
                    "last_status": last_status or "unknown",
                    "waited_seconds": elapsed,
                })
            return updates
        
        # OTel: 记录轮询完成
        if _current_span and _current_span.is_recording():
            _current_span.add_event("benchmark.polling_complete", {
                "test_name": test_name,
                "task_id": task_id,
                "last_status": last_status,
                "total_wait_seconds": elapsed,
                "timed_out": elapsed >= max_wait,
            })
        
        # 获取结果
        if result_tool:
            try:
                result_args = {"server_id": server_id, "task_id": task_id}
                if hasattr(result_tool, 'ainvoke'):
                    test_result = await result_tool.ainvoke(result_args)
                else:
                    test_result = result_tool.run(result_args)
                
                results = dict(state.get("results", {}))
                results[key] = test_result
                updates["results"] = results
                
                # OTel: 记录结果摘要
                if _current_span and _current_span.is_recording():
                    result_str = json.dumps(test_result, ensure_ascii=False, default=str)[:1000] if test_result else ""
                    _current_span.add_event("benchmark.result", {
                        "test_name": test_name,
                        "task_id": task_id,
                        "result_preview": result_str,
                    })
                
                logger.info(f"[Workflow] {test_name} 结果获取成功")
            except Exception as e:
                logger.error(f"[Workflow] 获取 {test_name} 结果失败: {e}")
                results = dict(state.get("results", {}))
                results[key] = {"success": False, "error": str(e)}
                updates["results"] = results
                if _current_span and _current_span.is_recording():
                    _current_span.add_event("benchmark.result_fetch_failed", {
                        "test_name": test_name,
                        "task_id": task_id,
                        "error": str(e)[:300],
                    })
        
        updates.update(_update_node_status(state, f"run_{test_name}", "completed"))
        
    except Exception as e:
        logger.error(f"[Workflow] 执行 {test_name} 测试异常: {e}")
        updates["errors"] = list(state.get("errors", [])) + [{
            "node": f"run_{test_name}",
            "error": str(e),
            "detail": f"执行 {test_name} 测试过程中发生异常"
        }]
        updates.update(_update_node_status(state, f"run_{test_name}", "failed"))
        if _current_span and _current_span.is_recording():
            _current_span.add_event("benchmark.exception", {
                "test_name": test_name,
                "error_type": type(e).__name__,
                "error_message": str(e)[:500],
            })
    
    return updates


async def collect_results(state: WorkflowState, **kwargs) -> dict:
    """
    节点: 收集所有测试结果
    """
    logger.info("[Workflow] 收集结果节点开始")
    updates = _update_node_status(state, "collect_results", "running")
    
    results = state.get("results", {})
    errors = state.get("errors", [])
    
    summary_parts = []
    for test_name, result in results.items():
        if isinstance(result, dict):
            success = result.get("success", True)
            if success:
                summary_parts.append(f"✅ {test_name}: 成功")
            else:
                summary_parts.append(f"❌ {test_name}: 失败 - {result.get('error', '未知错误')}")
        else:
            summary_parts.append(f"📋 {test_name}: {str(result)[:200]}")
    
    if errors:
        summary_parts.append(f"\n⚠️ 错误数: {len(errors)}")
        for err in errors:
            summary_parts.append(f"  - {err.get('node', 'unknown')}: {err.get('error', '')}")
    
    updates["result_summary"] = "\n".join(summary_parts)
    updates.update(_update_node_status(state, "collect_results", "completed"))
    logger.info("[Workflow] 结果收集完成")
    
    return updates


async def generate_report(state: WorkflowState, *, llm=None, tools: dict = None) -> dict:
    """
    节点: 生成分析报告
    """
    logger.info("[Workflow] 生成报告节点开始")
    updates = _update_node_status(state, "generate_report", "running")
    
    results = state.get("results", {})
    errors = state.get("errors", [])
    scenario = state.get("scenario", "")
    server_ip = state.get("server_ip", "unknown")
    query = state.get("query", "")
    
    # 如果有 generate_report 工具，先用它
    report_tool = tools.get("generate_report") if tools else None
    server_id = state.get("server_id", "")
    if report_tool and server_id:
        try:
            args = {"server_id": server_id}
            if hasattr(report_tool, 'ainvoke'):
                report_result = await report_tool.ainvoke(args)
            else:
                report_result = report_tool.run(args)
            
            if isinstance(report_result, dict) and report_result.get("success"):
                updates["final_report"] = report_result.get("report", report_result.get("data", ""))
                updates.update(_update_node_status(state, "generate_report", "completed"))
                return updates
        except Exception as e:
            logger.warning(f"[Workflow] generate_report 工具调用失败: {e}，降级到 LLM 生成")
    elif report_tool and not server_id:
        logger.warning("[Workflow] 跳过 generate_report 工具：当前没有有效的 server_id，降级到 LLM 生成")
    
    # 降级: 使用 LLM 生成报告
    if llm:
        try:
            results_str = json.dumps(results, ensure_ascii=False, indent=2, default=str)[:3000]
            errors_str = json.dumps(errors, ensure_ascii=False, indent=2)[:1000]
            
            prompt = f"""你是一位专业的服务器性能测试分析师。请根据以下测试结果生成一份专业的性能评估报告。

## 测试场景
{scenario}

## 服务器
{server_ip}

## 用户需求
{query}

## 测试结果
```json
{results_str}
```

## 错误信息
```json
{errors_str}
```

请生成 Markdown 格式的报告，包含：
1. 测试概述
2. 各项指标分析
3. 性能评估总结
4. 优化建议（如有）
"""
            
            response = await llm.ainvoke(prompt)
            updates["final_report"] = response.content if hasattr(response, "content") else str(response)
        except Exception as e:
            logger.error(f"[Workflow] LLM 生成报告失败: {e}")
            updates["final_report"] = _generate_simple_report(state)
    else:
        updates["final_report"] = _generate_simple_report(state)
    
    updates["status"] = "completed"
    updates.update(_update_node_status(state, "generate_report", "completed"))
    logger.info("[Workflow] 报告生成完成")
    
    return updates


async def handle_error(state: WorkflowState, **kwargs) -> dict:
    """
    节点: 错误处理
    
    收集错误信息，尝试调用 AI 故障分析器生成诊断报告。
    """
    logger.info("[Workflow] 错误处理节点开始")
    errors = state.get("errors", [])
    
    # 尝试 AI 故障分析
    analysis_reports = []
    try:
        from langchain_agent.observability.failure_analyzer import FailureAnalyzer
        llm = kwargs.get("llm")
        analyzer = FailureAnalyzer(llm=llm)
        
        for err in errors[-3:]:  # 最多分析最近 3 个错误
            try:
                task_context = {
                    "server_id": state.get("server_id", ""),
                    "test_name": state.get("scenario", ""),
                    "params": {},
                }
                report = await analyzer.analyze(err, task_context)
                diagnosis = report.get("diagnosis", {})
                analysis_reports.append({
                    "node": err.get("node", "未知"),
                    "classification": diagnosis.get("classification", "其他"),
                    "root_cause": diagnosis.get("root_cause", ""),
                    "fix_suggestion": diagnosis.get("fix_suggestion", ""),
                    "impact": diagnosis.get("impact", "中"),
                })
            except Exception as e:
                logger.warning(f"[Workflow] 故障分析失败: {e}")
    except ImportError:
        logger.debug("[Workflow] failure_analyzer 模块不可用")
    
    error_parts = ["## ❌ 执行过程中出现错误\n"]
    for err in errors:
        error_parts.append(f"### {err.get('node', '未知节点')}")
        error_parts.append(f"- **错误**: {err.get('error', '未知错误')}")
        if err.get('detail'):
            error_parts.append(f"- **详情**: {err.get('detail')}")
        error_parts.append("")
    
    # 附加故障分析结果
    if analysis_reports:
        error_parts.append("## 🔍 AI 故障诊断\n")
        for ar in analysis_reports:
            error_parts.append(f"### {ar['node']}")
            error_parts.append(f"- **分类**: {ar['classification']}")
            error_parts.append(f"- **根因**: {ar['root_cause']}")
            error_parts.append(f"- **修复建议**: {ar['fix_suggestion']}")
            error_parts.append(f"- **影响**: {ar['impact']}")
            error_parts.append("")
    
    error_parts.append("请检查服务器状态和网络连接，然后重试。")
    
    return {
        "final_report": "\n".join(error_parts),
        "status": "failed",
    }


def _generate_simple_report(state: WorkflowState) -> str:
    """生成简单的文本报告（降级方案）"""
    results = state.get("results", {})
    errors = state.get("errors", [])
    scenario = state.get("scenario", "")
    server_ip = state.get("server_ip", "unknown")
    
    parts = [
        f"# 性能测试报告",
        f"",
        f"- **服务器**: {server_ip}",
        f"- **测试场景**: {scenario}",
        f"- **测试项数**: {len(results)}",
        f"- **错误数**: {len(errors)}",
        f"",
        f"## 测试结果",
        f"",
    ]
    
    for test_name, result in results.items():
        parts.append(f"### {test_name}")
        if isinstance(result, dict):
            parts.append(f"```json")
            parts.append(json.dumps(result, ensure_ascii=False, indent=2)[:1000])
            parts.append(f"```")
        else:
            parts.append(str(result)[:500])
        parts.append("")
    
    if errors:
        parts.append("## 错误信息")
        parts.append("")
        for err in errors:
            parts.append(f"- {err.get('node', '')}: {err.get('error', '')}")
    
    return "\n".join(parts)


def route_after_tool_check(state: WorkflowState) -> str:
    """
    条件边: 工具检查后的路由
    """
    node_statuses = state.get("node_statuses", {})
    if node_statuses.get("check_tools") == "failed" or not state.get("server_id"):
        return "handle_error"
    missing = state.get("missing_tools", [])
    if missing:
        return "install_tools"
    return "proceed"


def route_after_server_selection(state: WorkflowState) -> str:
    """
    条件边: 服务器选择后的路由
    """
    node_statuses = state.get("node_statuses", {})
    if node_statuses.get("select_server") == "failed" or not state.get("server_id"):
        return "handle_error"
    return "proceed"


def route_after_install(state: WorkflowState) -> str:
    """
    条件边: 工具安装后的路由
    """
    node_statuses = state.get("node_statuses", {})
    if node_statuses.get("install_tools") == "failed" or state.get("tool_install_failed"):
        return "handle_error"
    return "proceed"
