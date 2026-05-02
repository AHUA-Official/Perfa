#!/bin/bash
# 查看本地完整开发链路状态

set -e

echo "Node Agent:"
curl -sS --max-time 5 http://127.0.0.1:8080/health || true
echo ""
echo "MCP Server:"
curl -I -sS --max-time 5 "http://127.0.0.1:9000/sse?api_key=test-key-123" || true
echo ""
echo "LangChain Backend:"
curl -sS --max-time 5 http://127.0.0.1:10000/health || true
echo ""
echo "WebUI V2:"
curl -I -sS --max-time 5 http://127.0.0.1:3002 || true
