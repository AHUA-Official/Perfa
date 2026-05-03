#!/bin/bash
# 查看 OTel Collector + Jaeger 状态

set -e

echo "OTel Collector:"
if curl -sS --max-time 5 http://127.0.0.1:4318 >/dev/null 2>&1; then
    echo "  状态: ✅ 运行中"
else
    echo "  状态: ❌ 未运行"
fi

echo "Jaeger:"
if curl -I -sS --max-time 5 http://127.0.0.1:16686/api/monitor/jaeger >/dev/null 2>&1; then
    echo "  状态: ✅ 运行中"
    echo "  HTTP: http://127.0.0.1:16686/api/monitor/jaeger"
else
    echo "  状态: ❌ 未运行"
fi
