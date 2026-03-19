# Phase 2: Web 界面设计文档

## 1. 目标

实现 ChatGPT 风格的对话 WebUI，用户输入自然语言，Agent 自动调用工具完成任务。

## 2. 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    前端（webui/）                            │
│  ChatGPT-Next-Web（Git Submodule，独立仓库）                 │
│  - 对话界面                                                  │
│  - Markdown 渲染                                             │
│  - 流式输出                                                  │
└────────────────────────┬────────────────────────────────────┘
                         │ OpenAI 兼容 API
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                后端（langchain_agent/backend/）              │
│  FastAPI + OpenAI 兼容接口                                   │
│  ↓ 复用现有模块                                              │
│  AgentOrchestrator → ReActAgent → MCPToolAdapter            │
└─────────────────────────────────────────────────────────────┘
```

## 3. 目录结构

```
/home/ubuntu/Perfa/
├── src/
│   └── langchain_agent/
│       ├── backend/                 # 后端 API（新增）
│       │   ├── __init__.py
│       │   ├── main.py             # FastAPI 入口
│       │   ├── openai_api.py       # OpenAI 兼容接口
│       │   └── schemas.py          # 数据模型
│       │
│       ├── agents/                  # 已有
│       ├── core/                    # 已有
│       ├── tools/                   # 已有
│       └── main.py                  # CLI 入口
│
└── webui/                           # 前端（新增，独立 Git）
    └── chatgpt-next-web/            # Git Submodule
```

## 4. 前端管理

### 方式 1：使用 Git Submodule（推荐）

```bash
# 在项目根目录添加 submodule
cd /home/ubuntu/Perfa
git submodule add https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.git webui/chatgpt-next-web

# 更新前端
git submodule update --remote

# 克隆整个项目（包含 submodule）
git clone --recursive https://your-repo.git
```

### 方式 2：独立部署（不用拉源码）

```bash
# 直接使用 Docker，不需要前端源码
cd /home/ubuntu/Perfa
mkdir -p webui
cd webui

# 创建 docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3.8'
services:
  chatgpt-web:
    image: yidadaa/chatgpt-next-web:latest
    ports:
      - "3000:3000"
    environment:
      - OPENAI_API_KEY=any-key
      - BASE_URL=http://your-backend:9001/v1
EOF

# 启动
docker-compose up -d
```

## 5. 后端实现

### 5.1 核心文件（约 150 行）

| 文件 | 行数 | 说明 |
|------|------|------|
| `backend/main.py` | 30 | FastAPI 应用、CORS 配置 |
| `backend/openai_api.py` | 100 | OpenAI 兼容接口、SSE 流式输出 |
| `backend/schemas.py` | 20 | 数据模型定义 |

### 5.2 主要接口

```
POST /v1/chat/completions     # 对话接口（支持 SSE 流式输出）
GET  /v1/models               # 模型列表（可选）
```

### 5.3 核心代码结构

**backend/main.py**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Perfa Agent API")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由
from .openai_api import router
app.include_router(router)
```

**backend/openai_api.py**
```python
from fastapi import APIRouter
from .schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/v1")

@router.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    # 调用 AgentOrchestrator.process_query()
    # 支持 stream=true 时返回 SSE
    pass
```

**backend/schemas.py**
```python
from pydantic import BaseModel
from typing import List, Optional

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: bool = False

class ChatResponse(BaseModel):
    id: str
    choices: List[dict]
```

## 6. 开发步骤

### Step 1: 后端开发（1 天）

```bash
# 1. 创建目录
mkdir -p src/langchain_agent/backend

# 2. 安装依赖
pip install fastapi uvicorn sse-starlette

# 3. 实现文件
# - backend/__init__.py
# - backend/main.py
# - backend/openai_api.py
# - backend/schemas.py

# 4. 启动测试
uvicorn langchain_agent.backend.main:app --reload --port 8080

# 5. 测试接口
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"测试"}]}'
```

### Step 2: 前端部署（半天）

```bash
# 方式 1: Git Submodule
git submodule add https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web.git webui/chatgpt-next-web
cd webui/chatgpt-next-web
# 配置 .env 文件，设置 BASE_URL=http://localhost:8080/v1

# 方式 2: Docker（推荐，不需要源码）
cd webui
docker-compose up -d
```

### Step 3: 联调测试（半天）

```bash
# 测试流式输出
curl -X POST http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"test","messages":[{"role":"user","content":"测试"}],"stream":true}'

# 访问 Web UI
open http://localhost:3000

# 测试用例
# 1. 简单对话 - "有哪些服务器？"
# 2. 工具调用 - "检查 server-01 的状态"
# 3. 流式输出 - 观察思考过程
```

## 7. CLI 与 Web UI 输出一致性

### 实现方式

后端将 Agent 执行过程格式化为 Markdown，前端自动渲染。

### 输出格式示例

```markdown
## 💭 思考过程

正在分析您的需求...

**步骤 1**: 调用工具 `list_servers`
- 参数：`{}`
- 结果：找到 3 台服务器
- 耗时：0.07秒

**步骤 2**: 调用工具 `run_benchmark`
- 参数：`{"server_id": "xxx", "test_name": "unixbench"}`
- 结果：✅ 测试已启动
- 耗时：1.72秒

---

## ✅ 执行结果

已对 **server-01** (192.168.1.100) 启动 CPU 性能测试。

**Task ID**: `87951d2e-24a4-46e8-ae30-e9b90d04f9be`

---

⏱️ **性能统计**
- LLM 推理时间：15.2秒
- 工具执行时间：1.79秒
- 总执行时间：17.0秒
```

### 关键点

1. **Markdown 格式化** - Agent 返回结果是 Markdown
2. **流式输出** - 逐段推送，实时显示
3. **自动渲染** - ChatGPT-Next-Web 渲染 Markdown

## 8. 部署方案

### Docker Compose

```yaml
# webui/docker-compose.yml

version: '3.8'

services:
  chatgpt-web:
    image: yidadaa/chatgpt-next-web:latest
    container_name: perfa-chatgpt-web
    ports:
      - "3000:3000"
    environment:
      - OPENAI_API_KEY=any-key
      - BASE_URL=http://your-backend-host:9001/v1
    restart: unless-stopped
```

### 启动命令

```bash
cd /home/ubuntu/Perfa/webui
docker-compose up -d

# 访问
open http://localhost:3000
```

## 9. 技术栈

### 后端

- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **SSE-Starlette** - 流式输出

### 前端

- **ChatGPT-Next-Web** - 开源 ChatGPT UI
- **Next.js** - React 框架
- **TailwindCSS** - 样式

## 10. 预期效果

用户在 Web UI 输入：`"检查 server-01 的 CPU 性能"`

Web UI 显示（流式输出）：

```
正在分析您的需求...

正在查询服务器列表...
找到 3 台服务器

正在启动 UnixBench 测试...
测试已启动，Task ID: xxx

✅ 测试完成！

单核得分：1250
多核得分：8500

⏱️ 总耗时：17.0秒
```

与 CLI 输出一致，只是界面更美观。
