"""
OpenTelemetry Metrics 配置

定义 8 个核心指标，支持导出到 OTLP (Prometheus/VictoriaMetrics)。
"""

import os
from typing import Optional

from langchain_agent.core.logger import get_logger
logger = get_logger()

# 全局 Meter 实例
_meter = None
_metrics = {}


def setup_metrics(
    service_name: str = "perfa-agent",
    otlp_endpoint: Optional[str] = None,
) -> None:
    """
    初始化 OpenTelemetry 指标采集

    定义 8 个核心指标:
    1. perfa_benchmark_duration_seconds — 压测执行耗时
    2. perfa_benchmark_total — 压测任务总数
    3. perfa_benchmark_errors — 压测任务失败数
    4. perfa_tool_call_duration_seconds — 工具调用耗时
    5. perfa_tool_call_total — 工具调用总数
    6. perfa_llm_request_duration_seconds — LLM 请求耗时
    7. perfa_llm_token_usage — LLM Token 使用量
    8. perfa_agent_session_active — 活跃会话数
    """
    global _meter, _metrics

    try:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": service_name,
            "service.version": "0.1.0",
        })

        readers = []

        # OTLP 导出
        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
                    OTLPMetricExporter,
                )
                otlp_reader = PeriodicExportingMetricReader(
                    OTLPMetricExporter(endpoint=endpoint, insecure=True),
                    export_interval_millis=15000,
                )
                readers.append(otlp_reader)
                logger.info(f"✅ OTel Metrics: OTLP 导出 → {endpoint}")
            except ImportError:
                logger.warning("⚠️ opentelemetry-exporter-otlp-proto-grpc 未安装，跳过 OTLP Metrics 导出")

        # Console 导出 (调试)
        if os.getenv("OTEL_CONSOLE_EXPORT", "").lower() == "true":
            from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
            console_reader = PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=30000,
            )
            readers.append(console_reader)

        # 创建 MeterProvider
        provider = MeterProvider(resource=resource, metric_readers=readers)
        metrics.set_meter_provider(provider)
        _meter = metrics.get_meter(service_name, "0.1.0")

        # 定义指标
        _metrics["benchmark_duration"] = _meter.create_histogram(
            name="perfa_benchmark_duration_seconds",
            description="压测执行耗时",
            unit="s",
        )
        _metrics["benchmark_total"] = _meter.create_counter(
            name="perfa_benchmark_total",
            description="压测任务总数",
        )
        _metrics["benchmark_errors"] = _meter.create_counter(
            name="perfa_benchmark_errors",
            description="压测任务失败数",
        )
        _metrics["tool_call_duration"] = _meter.create_histogram(
            name="perfa_tool_call_duration_seconds",
            description="工具调用耗时",
            unit="s",
        )
        _metrics["tool_call_total"] = _meter.create_counter(
            name="perfa_tool_call_total",
            description="工具调用总数",
        )
        _metrics["llm_request_duration"] = _meter.create_histogram(
            name="perfa_llm_request_duration_seconds",
            description="LLM 请求耗时",
            unit="s",
        )
        _metrics["llm_token_usage"] = _meter.create_histogram(
            name="perfa_llm_token_usage",
            description="LLM Token 使用量",
            unit="tokens",
        )
        _metrics["session_active"] = _meter.create_up_down_counter(
            name="perfa_agent_session_active",
            description="活跃会话数",
        )

        logger.info(f"✅ OTel Metrics 初始化完成: {len(_metrics)} 个指标")

    except ImportError:
        logger.warning("⚠️ opentelemetry-api/sdk 未安装，指标功能不可用")
    except Exception as e:
        logger.warning(f"⚠️ OTel Metrics 初始化失败: {e}")


def get_meter():
    """获取全局 Meter 实例"""
    return _meter


def get_metric(name: str):
    """获取指定名称的指标实例"""
    return _metrics.get(name)


def record_benchmark(benchmark_type: str, duration: float, success: bool, server_id: str = ""):
    """记录一次压测执行"""
    m = _metrics
    if not m:
        return
    attrs = {"benchmark_type": benchmark_type, "server_id": server_id}
    m["benchmark_duration"].record(duration, attrs)
    m["benchmark_total"].add(1, attrs)
    if not success:
        m["benchmark_errors"].add(1, attrs)


def record_tool_call(tool_name: str, duration: float, success: bool = True):
    """记录一次工具调用"""
    m = _metrics
    if not m:
        return
    attrs = {"tool_name": tool_name, "success": str(success)}
    m["tool_call_duration"].record(duration, attrs)
    m["tool_call_total"].add(1, attrs)


def record_llm_request(duration: float, tokens: int = 0):
    """记录一次 LLM 请求"""
    m = _metrics
    if not m:
        return
    m["llm_request_duration"].record(duration)
    if tokens > 0:
        m["llm_token_usage"].record(tokens)
