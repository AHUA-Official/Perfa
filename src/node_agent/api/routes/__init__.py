"""
路由模块
"""
from .health import bp as health_bp
from .monitor import bp as monitor_bp
from .tool import bp as tool_bp
from .benchmark import bp as benchmark_bp

__all__ = ['health_bp', 'monitor_bp', 'tool_bp', 'benchmark_bp']
