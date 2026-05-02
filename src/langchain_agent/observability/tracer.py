"""
OpenTelemetry Tracer 配置

提供统一的 TracerProvider 和 tracer 实例。
支持导出到 OTLP (Collector) 和控制台。
"""

import os
from typing import Optional

from langchain_agent.core.logger import get_logger
logger = get_logger()

# 全局 Tracer 实例
_tracer = None
_provider = None


def setup_tracing(
    service_name: str = "perfa-agent",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> None:
    """
    初始化 OpenTelemetry 追踪

    Args:
        service_name: 服务名称
        otlp_endpoint: OTLP gRPC 端点 (如 localhost:4317)
        enable_console: 是否启用控制台导出 (调试用)
    """
    global _tracer, _provider

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        # 创建 Resource
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "0.1.0",
        })

        # 创建 TracerProvider
        _provider = TracerProvider(resource=resource)

        # OTLP 导出器
        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                _provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(f"✅ OTel Tracing: OTLP 导出 → {endpoint}")
            except ImportError:
                logger.warning("⚠️ opentelemetry-exporter-otlp-proto-grpc 未安装，跳过 OTLP 导出")

        # 控制台导出 (调试)
        if enable_console or os.getenv("OTEL_CONSOLE_EXPORT", "").lower() == "true":
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            _provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
            logger.info("✅ OTel Tracing: 控制台导出已启用")

        # 如果没有配置任何导出器，使用默认的 noop
        trace.set_tracer_provider(_provider)
        _tracer = trace.get_tracer(service_name, "0.1.0")

        logger.info(f"✅ OTel Tracing 初始化完成: {service_name}")

    except ImportError:
        logger.warning("⚠️ opentelemetry-api/sdk 未安装，追踪功能不可用")
        _tracer = None
    except Exception as e:
        logger.warning(f"⚠️ OTel Tracing 初始化失败: {e}")
        _tracer = None


def get_tracer():
    """获取全局 Tracer 实例"""
    return _tracer
