"""
MCP Server 主入口文件
负责注册所有工具和启动服务
"""

from mcp import Server
from tools import (
    agent,
    server_mgmt,
    environment,
    benchmark,
    monitoring,
    data_storage,
    timeseries,
    intelligence,
    task_mgmt,
    batch_ops,
    data_mgmt,
    sys_config,
    health
)
from resources import handlers as resources
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP Server实例
server = Server("perfa")


# ==================== 注册Agent管理类工具 ====================

@server.tool("deploy_agent")
async def deploy_agent(host: str, ssh_port: int, credentials: dict):
    """在目标服务器部署Agent"""
    logger.info(f"部署Agent到 {host}:{ssh_port}")
    return await agent.deploy_agent(host, ssh_port, credentials)


@server.tool("check_agent_status")
async def check_agent_status(agent_id: str):
    """检查Agent运行状态"""
    return await agent.check_agent_status(agent_id)


@server.tool("upgrade_agent")
async def upgrade_agent(agent_id: str, version: str = "latest"):
    """升级Agent版本"""
    return await agent.upgrade_agent(agent_id, version)


@server.tool("restart_agent")
async def restart_agent(agent_id: str):
    """重启Agent"""
    return await agent.restart_agent(agent_id)


@server.tool("get_agent_logs")
async def get_agent_logs(agent_id: str, lines: int = 100):
    """获取Agent日志"""
    return await agent.get_agent_logs(agent_id, lines)


@server.tool("uninstall_agent")
async def uninstall_agent(agent_id: str):
    """卸载Agent"""
    return await agent.uninstall_agent(agent_id)


@server.tool("configure_agent")
async def configure_agent(agent_id: str, config: dict):
    """配置Agent参数"""
    return await agent.configure_agent(agent_id, config)


# ==================== 注册服务器管理类工具 ====================

@server.tool("register_server")
async def register_server(host: str, ssh_port: int, auth_type: str, credentials: dict):
    """注册压测服务器"""
    return await server_mgmt.register_server(host, ssh_port, auth_type, credentials)


@server.tool("list_servers")
async def list_servers():
    """列出已注册服务器"""
    return await server_mgmt.list_servers()


@server.tool("remove_server")
async def remove_server(server_id: str):
    """移除服务器注册"""
    return await server_mgmt.remove_server(server_id)


@server.tool("get_server_hardware_info")
async def get_server_hardware_info(server_id: str):
    """获取服务器硬件信息"""
    return await server_mgmt.get_server_hardware_info(server_id)


@server.tool("update_server_info")
async def update_server_info(server_id: str, info: dict):
    """更新服务器信息"""
    return await server_mgmt.update_server_info(server_id, info)


# ==================== 注册环境管理类工具 ====================

@server.tool("setup_bench_env")
async def setup_bench_env(agent_id: str, provider: str = "pts"):
    """一键初始化压测环境"""
    return await environment.setup_bench_env(agent_id, provider)


@server.tool("check_hardware_inventory")
async def check_hardware_inventory(agent_id: str):
    """扫描服务器硬件拓扑"""
    return await environment.check_hardware_inventory(agent_id)


# ... 继续注册其他工具
# 为了简洁，这里省略部分工具注册
# 实际项目中会继续注册所有54个工具


# ==================== 注册压测执行类工具 ====================

@server.tool("run_benchmark")
async def run_benchmark(agent_id: str, test_name: str, params: dict = None):
    """执行硬件压测"""
    logger.info(f"在Agent {agent_id} 上执行 {test_name}")
    return await benchmark.run_benchmark(agent_id, test_name, params or {})


@server.tool("cancel_benchmark")
async def cancel_benchmark(task_id: str):
    """取消正在运行的测试"""
    return await benchmark.cancel_benchmark(task_id)


@server.tool("get_benchmark_status")
async def get_benchmark_status(task_id: str):
    """查询压测任务状态"""
    return await benchmark.get_benchmark_status(task_id)


# ==================== 注册监控查询类工具 ====================

@server.tool("start_monitoring")
async def start_monitoring(agent_id: str, metrics: list, interval: int = 5):
    """启动后台监控"""
    logger.info(f"在Agent {agent_id} 上启动监控")
    return await monitoring.start_monitoring(agent_id, metrics, interval)


@server.tool("query_monitoring_data")
async def query_monitoring_data(task_id: str, time_range: dict):
    """查询历史监控数据"""
    return await monitoring.query_monitoring_data(task_id, time_range)


# ==================== 注册智能分析类工具 ====================

@server.tool("generate_expert_report")
async def generate_expert_report(result_id: str):
    """生成专家级诊断报告"""
    return await intelligence.generate_expert_report(result_id)


@server.tool("query_knowledge_base")
async def query_knowledge_base(query: str, top_k: int = 5):
    """检索硬件手册和优化文档"""
    return await intelligence.query_knowledge_base(query, top_k)


# ==================== 注册MCP Resources ====================

@server.resource("mcp://agents/list")
async def list_agents_resource():
    """已部署Agent列表"""
    return await resources.list_agents()


@server.resource("mcp://benchmark/history")
async def benchmark_history_resource(query_params: dict = None):
    """历史测试汇总表"""
    return await resources.benchmark_history(query_params)


# ==================== 启动服务器 ====================

def main():
    """启动MCP Server"""
    logger.info("启动 Perfa MCP Server...")
    logger.info(f"已注册工具数: {len(server.tools)}")
    logger.info(f"已注册资源数: {len(server.resources)}")
    
    # 运行MCP Server
    server.run()


if __name__ == "__main__":
    main()
