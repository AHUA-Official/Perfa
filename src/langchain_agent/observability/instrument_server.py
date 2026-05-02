"""
MCP Server 侧 OTel Instrumentation

自动注入 StarletteInstrumentor 到 MCP Server 的 Starlette 应用。
"""

import os
from langchain_agent.core.logger import get_logger
logger = get_logger()


def setup_server_tracing(
    service_name: str = "perfa-mcp-server",
    otlp_endpoint: str = None,
):
    """
    初始化 MCP Server 的 OTel 追踪

    Args:
        service_name: 服务名称
        otlp_endpoint: OTLP gRPC 端点
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({
            "service.name": service_name,
            "service.version": "0.1.0",
        })

        provider = TracerProvider(resource=resource)

        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info(f"✅ MCP Server OTel: OTLP 导出 → {endpoint}")
            except ImportError:
                logger.warning("⚠️ opentelemetry-exporter-otlp-proto-grpc 未安装")

        trace.set_tracer_provider(provider)
        logger.info(f"✅ MCP Server OTel Tracing 初始化完成: {service_name}")

    except ImportError:
        logger.warning("⚠️ opentelemetry 未安装，MCP Server 追踪不可用")
    except Exception as e:
        logger.warning(f"⚠️ MCP Server OTel 初始化失败: {e}")


def instrument_starlette_app(app):
    """
    对 Starlette 应用注入自动 Instrumentation

    在 app 创建后、uvicorn.run() 之前调用。

    Args:
        app: Starlette 应用实例
    """
    try:
        from opentelemetry.instrumentation.starlette import StarletteInstrumentor
        StarletteInstrumentor().instrument_app(app)
        logger.info("✅ StarletteInstrumentor 注入成功")
    except ImportError:
        logger.warning("⚠️ opentelemetry-instrumentation-starlette 未安装，跳过自动注入")
    except Exception as e:
        logger.warning(f"⚠️ StarletteInstrumentor 注入失败: {e}")
