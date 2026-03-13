"""MCP Server 入口"""
from config import Config
from server import MCPServer


def main():
    """主函数"""
    # 加载配置
    config = Config.from_env()
    
    # 创建服务器
    server = MCPServer(config)
    
    # 启动服务器
    server.run()


if __name__ == "__main__":
    main()
