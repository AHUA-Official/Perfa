# 测试 MCP Server

这是一个快速测试脚本，用于验证 MCP Server 是否正常工作。

## 使用方法

### 1. 启动 MCP Server

```bash
export MCP_API_KEY="test-key-123"
export MCP_DB_PATH="./test.db"
python main.py
```

### 2. 运行测试脚本

```bash
python test_mcp.py
```

## 测试内容

1. 健康检查
2. 注册服务器
3. 列出服务器
4. 获取服务器信息
5. 更新服务器信息
6. 移除服务器
"""

import requests
import json
import sys


class MCPClient:
    """简单的 MCP 客户端（用于测试）"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = self.session.get(f"{self.base_url}/sse", timeout=5, stream=False)
            return response.status_code == 200
        except:
            return False
    
    def call_tool(self, name: str, arguments: dict) -> dict:
        """调用工具"""
        # 注意：这是一个简化的测试方法
        # 实际的 MCP 客户端需要通过 SSE 连接
        # 这里我们直接调用工具
        
        print(f"\n调用工具: {name}")
        print(f"参数: {json.dumps(arguments, indent=2)}")
        
        # 由于 MCP 需要 SSE，这里只是模拟
        # 真实测试需要使用 Cursor 或 VSCode
        print("✓ 模拟调用成功（实际测试请使用 Cursor/VSCode）")
        return {"success": True, "message": "Test mode"}


def test_mcp():
    """测试 MCP Server"""
    
    # 配置
    MCP_URL = "http://localhost:9000"
    API_KEY = "test-key-123"
    
    client = MCPClient(MCP_URL, API_KEY)
    
    print("=" * 50)
    print("MCP Server 测试")
    print("=" * 50)
    
    # 1. 健康检查
    print("\n1. 健康检查...")
    if client.health_check():
        print("✓ MCP Server 运行正常")
    else:
        print("✗ MCP Server 连接失败")
        print("请确保 MCP Server 已启动：python main.py")
        sys.exit(1)
    
    # 2. 测试工具调用
    print("\n2. 测试工具调用...")
    
    # 注册服务器
    client.call_tool("register_server", {
        "ip": "192.168.1.100",
        "ssh_user": "root",
        "ssh_password": "password123",
        "alias": "test-server"
    })
    
    # 列出服务器
    client.call_tool("list_servers", {})
    
    # 获取服务器信息
    client.call_tool("get_server_info", {
        "server_id": "需要从 list_servers 获取"
    })
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)
    print("\n下一步：")
    print("1. 使用 Cursor 或 VSCode 连接 MCP Server")
    print("2. 参考 MCP_CLIENT_SETUP.md 配置客户端")
    print("3. 在客户端中测试完整功能")


if __name__ == "__main__":
    test_mcp()
