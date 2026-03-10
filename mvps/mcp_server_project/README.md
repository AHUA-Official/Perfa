# MCP Server 项目结构（模块化组织）

## 目录结构

```
mcp_server/
├── __init__.py
├── server.py              # 主MCP Server入口
│
├── tools/                 # 工具模块（按功能分类）
│   ├── __init__.py
│   ├── agent.py          # Agent管理工具（7个）
│   ├── server_mgmt.py    # 服务器管理工具（5个）
│   ├── environment.py    # 环境管理工具（5个）
│   ├── benchmark.py      # 压测执行工具（6个）
│   ├── monitoring.py     # 监控查询工具（4个）
│   ├── data_storage.py   # 数据存储工具（5个）
│   ├── timeseries.py     # 时序分析工具（4个）
│   ├── intelligence.py   # 智能分析工具（4个）
│   ├── task_mgmt.py      # 任务管理工具（4个）
│   ├── batch_ops.py      # 批量操作工具（2个）
│   ├── data_mgmt.py      # 数据管理工具（3个）
│   ├── sys_config.py     # 系统配置工具（3个）
│   └── health.py         # 系统健康工具（2个）
│
├── resources/             # MCP Resources
│   ├── __init__.py
│   └── handlers.py
│
├── models/                # 数据模型
│   ├── __init__.py
│   ├── agent.py
│   ├── server.py
│   ├── benchmark.py
│   └── monitoring.py
│
├── services/              # 业务逻辑服务
│   ├── __init__.py
│   ├── agent_service.py  # Agent通信服务
│   ├── db_service.py     # 数据库服务
│   └── rag_service.py    # RAG检索服务
│
└── utils/                 # 工具函数
    ├── __init__.py
    ├── ssh.py            # SSH工具
    ├── db.py             # 数据库工具
    └── logger.py         # 日志工具
```

## 关键优势

1. **职责清晰**：每个文件负责一类工具
2. **易于维护**：修改某类工具不影响其他模块
3. **团队协作**：不同成员可以负责不同模块
4. **易于测试**：每个模块可以独立测试

## 开发指南

1. 新增工具：在对应模块添加函数，然后在 `server.py` 注册
2. 新增分类：创建新模块文件，在 `server.py` 导入
3. 修改工具：只需修改对应模块，无需改其他文件
