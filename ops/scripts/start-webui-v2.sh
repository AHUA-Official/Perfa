#!/bin/bash
# 启动 webui-v2

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WEBUI_DIR="$PROJECT_DIR/webui-v2"

cd "$WEBUI_DIR"
npm run dev
