"""
AI 故障分析器

当压测任务失败时，自动收集 trace+metrics+error 信息，
调用 LLM 生成结构化故障诊断报告。

增强功能：
- 接入 Jaeger API 查询完整 trace（含 AI 思考过程、决策、工具调用细节）
- 将 trace 中的 span events 提取为结构化上下文
- 提供给 LLM 的诊断 Prompt 包含完整可观测性数据
"""

import json
import time
import os
import asyncio
from typing import Optional, Dict, Any, List

from langchain_agent.core.logger import get_logger
logger = get_logger()


class FailureAnalyzer:
    """AI 故障分析器"""

    def __init__(self, llm=None, otlp_endpoint: str = None, jaeger_url: str = None):
        """
        初始化故障分析器

        Args:
            llm: LLM 实例（ChatOpenAI）
            otlp_endpoint: OTLP 端点（用于查询 trace 数据）
            jaeger_url: Jaeger API URL（如 http://localhost:16686）
        """
        self.llm = llm
        self.otlp_endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        self.jaeger_url = jaeger_url or os.getenv("JAEGER_API_URL", "http://localhost:16686")

    async def analyze(
        self,
        error_info: Dict[str, Any],
        task_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        分析故障并生成诊断报告

        Args:
            error_info: 错误信息，包含 node, error, detail 等字段
            task_context: 任务上下文，包含 server_id, test_name, params 等

        Returns:
            故障诊断报告字典
        """
        start_time = time.monotonic()

        # 1. 收集上下文（含 Jaeger trace 查询）
        context = await self._collect_context(error_info, task_context)

        # 2. 尝试 LLM 诊断
        diagnosis = None
        if self.llm:
            try:
                diagnosis = await self._llm_diagnose(context)
            except Exception as e:
                logger.warning(f"LLM 故障诊断失败: {e}")

        # 3. 生成结构化报告
        report = self._build_report(context, diagnosis)
        report["analysis_duration_seconds"] = time.monotonic() - start_time

        # 4. 记录 OTel span event
        self._record_analysis_span(report)

        logger.info(f"故障分析完成: {error_info.get('error', 'unknown')[:80]}")
        return report

    async def _collect_context(
        self,
        error_info: Dict[str, Any],
        task_context: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """收集故障上下文信息（含 Jaeger trace 查询）"""
        context = {
            "error": error_info,
            "task": task_context or {},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "system": self._get_system_info(),
        }

        # 从 Jaeger API 查询相关 trace
        trace_info = await self._query_jaeger_traces(error_info, task_context)
        if trace_info:
            context["trace"] = trace_info

        return context

    def _get_system_info(self) -> Dict[str, str]:
        """获取系统基本信息"""
        try:
            import platform
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
            }
        except Exception:
            return {}

    async def _query_jaeger_traces(
        self,
        error_info: Dict[str, Any],
        task_context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        从 Jaeger API 查询与故障相关的 trace 信息

        查询策略：
        1. 按 service=perfa-agent 查询最近的 error trace
        2. 如果有 task_id，尝试按 tag 过滤
        3. 提取 trace 中的 span events（AI 思考过程、决策、工具调用）
        """
        try:
            import aiohttp
        except ImportError:
            logger.debug("aiohttp 未安装，无法查询 Jaeger API")
            return self._query_trace_info_fallback(error_info, task_context)

        try:
            # 构建查询参数
            service = "perfa-agent"
            # 查询最近 30 分钟的 trace
            lookback = 1800000000  # 30 minutes in microseconds

            url = f"{self.jaeger_url}/api/traces"
            params = {
                "service": service,
                "lookback": str(lookback),
                "limit": "5",
            }

            # 如果有 task_id，添加 tag 过滤
            task_id = task_context.get("task_id", "") if task_context else ""
            if task_id:
                params["tags"] = json.dumps({"task_id": task_id})

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.debug(f"Jaeger API 返回非 200 状态: {resp.status}")
                        return None

                    data = await resp.json()

            traces = data.get("data", [])
            if not traces:
                logger.debug("Jaeger 中未找到相关 trace")
                return None

            # 提取最有价值的 trace 信息
            return self._extract_trace_details(traces, error_info)

        except asyncio.TimeoutError:
            logger.debug("Jaeger API 查询超时")
            return None
        except Exception as e:
            logger.debug(f"Jaeger API 查询失败: {e}")
            return None

    def _extract_trace_details(self, traces: list, error_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        从 Jaeger trace 数据中提取关键信息

        提取内容：
        - 每个 span 的操作名、耗时、状态
        - span events（AI 思考过程、决策、工具调用细节）
        - 错误 span 的详细信息
        """
        result = {
            "trace_count": len(traces),
            "traces": [],
        }

        for trace in traces[:3]:  # 最多处理 3 条 trace
            trace_id = trace.get("traceID", "")
            spans = trace.get("spans", [])

            trace_detail = {
                "trace_id": trace_id,
                "span_count": len(spans),
                "spans": [],
            }

            for span in spans:
                span_info = {
                    "operation": span.get("operationName", ""),
                    "duration_ms": span.get("duration", 0) / 1000,
                    "start_time": span.get("startTime", 0),
                    "tags": {},
                    "events": [],
                    "has_error": False,
                }

                # 提取 tags
                for tag in span.get("tags", []):
                    key = tag.get("key", "")
                    value = tag.get("value", "")
                    if key in ("error", "success", "tool_name", "node", "scenario",
                               "is_final", "node_status", "is_success"):
                        span_info["tags"][key] = value
                    if key == "error" and value:
                        span_info["has_error"] = True

                # 提取 logs（即 span events，包含 AI 思考和决策）
                for log in span.get("logs", []):
                    event = {
                        "timestamp": log.get("timestamp", 0),
                        "fields": {},
                    }
                    for field in log.get("fields", []):
                        key = field.get("key", "")
                        value = field.get("value", "")
                        # 关键字段：AI 推理、决策、工具调用
                        if key in ("reasoning_content", "decision_type", "tool_name",
                                   "tool_args", "result_preview", "answer_preview",
                                   "error_message", "error_type", "reason",
                                   "routed_scenario", "state_summary", "output_keys",
                                   "test_name", "task_id", "server_id",
                                   "tool_chain", "final_result_preview",
                                   "error_detail", "last_status", "total_wait_seconds",
                                   "server_ip", "agent_status"):
                            # 截断超长值
                            if isinstance(value, str) and len(value) > 800:
                                value = value[:800] + "...[truncated]"
                            event["fields"][key] = value

                    if event["fields"]:
                        span_info["events"].append(event)

                trace_detail["spans"].append(span_info)

            # 只保留有 events 或有 error 的 span（减少噪音）
            interesting_spans = [
                s for s in trace_detail["spans"]
                if s["events"] or s["has_error"]
                   or any(k in s["operation"] for k in ("think", "act", "run", "benchmark", "error", "orchestrator"))
            ]
            if interesting_spans:
                trace_detail["spans"] = interesting_spans
                result["traces"].append(trace_detail)

        return result if result["traces"] else None

    def _query_trace_info_fallback(
        self,
        error_info: Dict[str, Any],
        task_context: Optional[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Jaeger API 不可用时的降级方案"""
        # 尝试从当前 OTel context 获取 trace_id
        try:
            from opentelemetry import trace
            current_span = trace.get_current_span()
            if current_span and current_span.is_recording():
                ctx = current_span.get_span_context()
                return {
                    "trace_count": 1,
                    "traces": [{
                        "trace_id": format(ctx.trace_id, '032x'),
                        "note": "当前请求的 trace_id，请到 Jaeger UI 查看详情",
                        "jaeger_url": f"{self.jaeger_url}/api/traces/{format(ctx.trace_id, '032x')}",
                    }],
                }
        except Exception:
            pass
        return None

    async def _llm_diagnose(self, context: Dict[str, Any]) -> str:
        """调用 LLM 进行故障诊断（含完整 trace 上下文）"""
        error = context["error"]
        task = context["task"]
        system = context["system"]
        trace_data = context.get("trace", {})

        # 构建可读的 trace 摘要
        trace_summary = "无可用 trace 数据"
        if trace_data and trace_data.get("traces"):
            trace_lines = []
            for t in trace_data["traces"][:2]:
                trace_lines.append(f"### Trace {t.get('trace_id', 'unknown')[:16]}...")
                for span in t.get("spans", []):
                    op = span.get("operation", "unknown")
                    dur = span.get("duration_ms", 0)
                    tags = span.get("tags", {})
                    events = span.get("events", [])

                    trace_lines.append(f"\n**{op}** ({dur:.0f}ms)")

                    if tags:
                        trace_lines.append(f"  标签: {json.dumps(tags, ensure_ascii=False)}")

                    for evt in events:
                        fields = evt.get("fields", {})
                        # AI 思考过程
                        if "reasoning_content" in fields:
                            trace_lines.append(f"  💭 AI推理: {fields['reasoning_content'][:300]}")
                        # AI 决策
                        if "decision_type" in fields:
                            decision = fields["decision_type"]
                            if decision == "tool_call":
                                trace_lines.append(f"  🎯 决策: 调用工具 {fields.get('tool_name', '?')}, 参数: {fields.get('tool_args', '{}')[:200]}")
                            elif decision == "final_answer":
                                trace_lines.append(f"  🎯 决策: 给出最终答案 - {fields.get('answer_preview', '')[:200]}")
                        # 工具调用结果
                        if "result_preview" in fields:
                            trace_lines.append(f"  📋 工具结果: {fields['result_preview'][:300]}")
                        # 工具错误
                        if "error_message" in fields:
                            trace_lines.append(f"  ❌ 错误: {fields.get('error_type', '')}: {fields['error_message'][:200]}")
                        # 路由决策
                        if "routed_scenario" in fields:
                            trace_lines.append(f"  🔀 路由: → {fields['routed_scenario']} ({fields.get('reason', '')})")
                        # 压测状态
                        if "test_name" in fields and "task_id" in fields:
                            trace_lines.append(f"  ⚡ 压测: {fields['test_name']} task={fields['task_id'][:16]}...")

            trace_summary = "\n".join(trace_lines)

        prompt = f"""你是一位专业的服务器性能测试故障诊断专家。

## 故障信息
- **节点**: {error.get('node', '未知')}
- **错误**: {error.get('error', '未知错误')}
- **详情**: {error.get('detail', '无')}

## 任务上下文
- **服务器**: {task.get('server_id', '未知')}
- **测试类型**: {task.get('test_name', '未知')}
- **测试参数**: {json.dumps(task.get('params', {}), ensure_ascii=False)}

## 系统信息
- **平台**: {system.get('platform', '未知')}
- **主机**: {system.get('hostname', '未知')}

## 分布式追踪信息（含 AI 思考链和决策过程）
{trace_summary}

---

请基于以上信息（特别是追踪中的 AI 思考过程和工具调用链），分析故障原因。

重点关注：
1. AI 在哪个步骤做了什么决策？决策是否合理？
2. 工具调用的参数和返回结果是什么？哪一步出了问题？
3. 是否存在重试/超时/资源竞争等问题？

请用 JSON 格式输出：
{{
  "classification": "网络/权限/资源/配置/逻辑错误/其他",
  "root_cause": "简明扼要地解释根本原因",
  "decision_analysis": "AI 的决策链分析，指出是否有决策失误",
  "fix_suggestion": "可操作的修复步骤（1-3步）",
  "impact": "低/中/高",
  "prevention": "如何避免类似问题"
}}"""

        response = await self.llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)
        return content

    def _build_report(
        self,
        context: Dict[str, Any],
        diagnosis: Optional[str],
    ) -> Dict[str, Any]:
        """构建结构化故障报告"""
        error = context["error"]

        report = {
            "report_type": "failure_analysis",
            "timestamp": context["timestamp"],
            "error_node": error.get("node", "unknown"),
            "error_message": error.get("error", "unknown"),
            "error_detail": error.get("detail", ""),
            "task_info": context.get("task", {}),
            "trace_available": bool(context.get("trace")),
        }

        # 解析 LLM 诊断结果
        if diagnosis:
            try:
                # 尝试解析 JSON 格式的诊断
                # LLM 可能返回 markdown 包裹的 JSON
                cleaned = diagnosis.strip()
                if cleaned.startswith("```"):
                    lines = cleaned.split("\n")
                    cleaned = "\n".join(lines[1:-1])

                parsed = json.loads(cleaned)
                report["diagnosis"] = parsed
            except json.JSONDecodeError:
                # 无法解析为 JSON，作为原始文本保存
                report["diagnosis"] = {
                    "raw_analysis": diagnosis,
                    "classification": "uncategorized",
                    "root_cause": "LLM 诊断结果无法结构化解析",
                }
        else:
            # 无 LLM 诊断，使用规则推断
            report["diagnosis"] = self._rule_based_diagnosis(error)

        return report

    def _rule_based_diagnosis(self, error_info: Dict[str, Any]) -> Dict[str, str]:
        """基于规则的简易故障诊断（LLM 不可用时的降级方案）"""
        error_msg = str(error_info.get("error", "")).lower()
        detail = str(error_info.get("detail", "")).lower()

        # 规则匹配
        if "timeout" in error_msg or "timed out" in error_msg:
            return {
                "classification": "网络",
                "root_cause": "请求超时，可能是网络延迟或目标服务器无响应",
                "fix_suggestion": "1. 检查网络连接 2. 增加超时时间 3. 确认目标服务正常运行",
                "impact": "中",
                "prevention": "配置合理的超时时间，实现重试机制",
            }
        elif "connection" in error_msg or "refused" in error_msg:
            return {
                "classification": "网络",
                "root_cause": "连接被拒绝，目标服务可能未启动或端口被阻止",
                "fix_suggestion": "1. 检查目标服务状态 2. 确认防火墙设置 3. 验证端口配置",
                "impact": "高",
                "prevention": "实现健康检查和自动重连机制",
            }
        elif "permission" in error_msg or "denied" in error_msg or "auth" in error_msg:
            return {
                "classification": "权限",
                "root_cause": "权限不足或认证失败",
                "fix_suggestion": "1. 检查 SSH 凭据 2. 确认用户权限 3. 验证 API Key",
                "impact": "高",
                "prevention": "定期验证凭据有效性，使用密钥管理",
            }
        elif "not found" in error_msg or "不存在" in detail:
            return {
                "classification": "配置",
                "root_cause": "资源不存在或配置错误",
                "fix_suggestion": "1. 确认服务器已注册 2. 检查工具是否安装 3. 验证配置参数",
                "impact": "中",
                "prevention": "执行前进行环境预检",
            }
        elif "memory" in error_msg or "oom" in error_msg:
            return {
                "classification": "资源",
                "root_cause": "内存不足",
                "fix_suggestion": "1. 释放内存 2. 减少并发数 3. 增加系统内存",
                "impact": "高",
                "prevention": "监控内存使用，设置资源限制",
            }
        elif "busy" in error_msg or "running" in detail:
            return {
                "classification": "资源",
                "root_cause": "目标 Agent 正忙，有其他任务在执行",
                "fix_suggestion": "1. 等待当前任务完成 2. 增加并发能力 3. 实现任务队列",
                "impact": "低",
                "prevention": "实现任务排队和优先级调度",
            }
        else:
            return {
                "classification": "其他",
                "root_cause": f"未知错误: {error_info.get('error', '')[:200]}",
                "fix_suggestion": "1. 查看详细日志 2. 重试操作 3. 联系技术支持",
                "impact": "中",
                "prevention": "完善错误处理和日志记录",
            }

    def _record_analysis_span(self, report: Dict[str, Any]):
        """在 OTel span 中记录分析事件"""
        try:
            from langchain_agent.observability.tracer import get_tracer
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span("failure_analyzer.analyze") as span:
                    span.set_attribute("error_node", report.get("error_node", ""))
                    span.set_attribute("classification",
                        report.get("diagnosis", {}).get("classification", "unknown"))
                    span.set_attribute("impact",
                        report.get("diagnosis", {}).get("impact", "unknown"))
                    span.set_attribute("trace_available", report.get("trace_available", False))
                    span.add_event("failure_analysis_completed", {
                        "error_message": report.get("error_message", "")[:200],
                        "root_cause": report.get("diagnosis", {}).get("root_cause", "")[:300],
                        "decision_analysis": report.get("diagnosis", {}).get("decision_analysis", "")[:300],
                    })
        except Exception as e:
            logger.debug(f"记录分析 span 失败: {e}")
