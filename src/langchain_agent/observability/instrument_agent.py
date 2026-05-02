"""
Agent 侧 OTel Instrumentation 辅助模块

提供 span 上下文管理器和装饰器，简化手动埋点。
"""

import time
import functools
from typing import Optional, Dict, Any, Callable

from langchain_agent.core.logger import get_logger
logger = get_logger()


def get_otel_tracer():
    """获取 OTel tracer（延迟导入，避免循环依赖）"""
    try:
        from langchain_agent.observability.tracer import get_tracer
        return get_tracer()
    except Exception:
        return None


def get_otel_metrics():
    """获取 OTel metrics 模块（延迟导入）"""
    try:
        from langchain_agent.observability.metrics import record_tool_call, record_benchmark, record_llm_request
        return record_tool_call, record_benchmark, record_llm_request
    except Exception:
        return None, None, None


class SpanContext:
    """OTel Span 上下文管理器"""

    def __init__(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        record_exception: bool = True,
    ):
        self.name = name
        self.attributes = attributes or {}
        self.record_exception = record_exception
        self._span = None
        self._tracer = None

    async def __aenter__(self):
        self._tracer = get_otel_tracer()
        if self._tracer:
            self._span = self._tracer.start_span(
                self.name,
                attributes=self.attributes,
            )
            # 设置为当前 span
            from opentelemetry import context, trace
            ctx = trace.set_span_in_context(self._span)
            self._token = context.attach(ctx)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._span:
            if exc_type and self.record_exception:
                self._span.record_exception(exc_val)
                self._span.set_status(
                    self._get_status_for_exception(exc_val)
                )
            self._span.end()
            from opentelemetry import context
            context.detach(self._token)
        return False  # 不吞异常

    def set_attribute(self, key: str, value: Any):
        if self._span:
            self._span.set_attribute(key, value)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        if self._span:
            self._span.add_event(name, attributes or {})

    @staticmethod
    def _get_status_for_exception(exc):
        from opentelemetry.sdk.trace import Status, StatusCode
        return Status(StatusCode.ERROR, description=str(exc)[:200])


def traced(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    异步函数 OTel span 装饰器

    用法:
        @traced("my_operation", attributes={"key": "value"})
        async def my_func():
            ...
    """
    def decorator(func: Callable):
        span_name = name or f"perfa.{func.__name__}"

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            tracer = get_otel_tracer()
            if not tracer:
                return await func(*args, **kwargs)

            attrs = dict(attributes or {})
            # 自动从 self 提取类名
            if args and hasattr(args[0], '__class__'):
                attrs.setdefault("class", args[0].__class__.__name__)

            start_time = time.monotonic()
            with tracer.start_as_current_span(span_name, attributes=attrs) as span:
                try:
                    result = await func(*args, **kwargs)
                    duration = time.monotonic() - start_time
                    span.set_attribute("duration_seconds", duration)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    from opentelemetry.sdk.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, description=str(e)[:200]))
                    raise

        return wrapper
    return decorator


def traced_sync(name: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None):
    """
    同步函数 OTel span 装饰器
    """
    def decorator(func: Callable):
        span_name = name or f"perfa.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_otel_tracer()
            if not tracer:
                return func(*args, **kwargs)

            attrs = dict(attributes or {})
            if args and hasattr(args[0], '__class__'):
                attrs.setdefault("class", args[0].__class__.__name__)

            start_time = time.monotonic()
            with tracer.start_as_current_span(span_name, attributes=attrs) as span:
                try:
                    result = func(*args, **kwargs)
                    duration = time.monotonic() - start_time
                    span.set_attribute("duration_seconds", duration)
                    return result
                except Exception as e:
                    span.record_exception(e)
                    from opentelemetry.sdk.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, description=str(e)[:200]))
                    raise

        return wrapper
    return decorator


def record_tool_call_metrics(tool_name: str, duration: float, success: bool = True):
    """记录工具调用指标"""
    record_tool_call, _, _ = get_otel_metrics()
    if record_tool_call:
        try:
            record_tool_call(tool_name, duration, success)
        except Exception as e:
            logger.debug(f"记录工具调用指标失败: {e}")


def record_benchmark_metrics(benchmark_type: str, duration: float, success: bool, server_id: str = ""):
    """记录压测指标"""
    _, record_benchmark, _ = get_otel_metrics()
    if record_benchmark:
        try:
            record_benchmark(benchmark_type, duration, success, server_id)
        except Exception as e:
            logger.debug(f"记录压测指标失败: {e}")


def record_llm_metrics(duration: float, tokens: int = 0):
    """记录 LLM 请求指标"""
    _, _, record_llm_request = get_otel_metrics()
    if record_llm_request:
        try:
            record_llm_request(duration, tokens)
        except Exception as e:
            logger.debug(f"记录 LLM 指标失败: {e}")
