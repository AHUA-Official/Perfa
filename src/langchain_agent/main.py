"""
Perfa - LangChain Agent Module

@file: main.py
@desc: CLI入口
@author: Perfa Team
@date: 2026-03-18
"""

# 标准库导入
import asyncio
import argparse
from typing import Optional
import uuid
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 第三方库导入
from dotenv import load_dotenv

# 加载环境变量
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# 本地模块导入 - 使用统一日志
from langchain_agent.core.logger import setup_logger, get_logger
from langchain_agent.core.config import ConfigManager
from langchain_agent.core.orchestrator import AgentOrchestrator
from langchain_agent.tools.mcp_adapter import MCPToolAdapter

# 初始化日志（CLI 模式默认写文件）
logger = get_logger()


async def interactive_mode(orchestrator: AgentOrchestrator):
    """
    交互式模式
    
    Args:
        orchestrator: Agent编排器
    """
    logger.info("进入交互式模式，输入 'exit' 或 'quit' 退出")
    print("\n" + "="*60)
    print("Perfa LangChain Agent 交互模式")
    print("="*60)
    print("提示：输入 'exit' 或 'quit' 退出，'help' 查看帮助")
    print("="*60 + "\n")
    
    session_id = f"cli_session_{uuid.uuid4().hex[:16]}"
    
    while True:
        try:
            # 获取用户输入
            query = input("\nPerfa> ").strip()
            
            # 退出命令
            if query.lower() in ["exit", "quit", "q"]:
                logger.info("用户退出交互式模式")
                print("\n感谢使用，再见！")
                break
            
            # 帮助命令
            if query.lower() in ["help", "h", "?"]:
                show_help()
                continue
            
            # 清空命令
            if query.lower() in ["clear", "cls"]:
                print("\n" * 50)  # 简单清屏
                continue
            
            # 空输入
            if not query:
                continue
            
            # 执行查询
            print("\n" + "-"*60)
            print("处理中...")
            print("-"*60)
            
            response = await orchestrator.process_query(query, session_id=session_id)
            
            # 显示结果
            print_result(response)
            
        except KeyboardInterrupt:
            logger.info("用户中断（Ctrl+C）")
            print("\n\n操作已中断，输入 'exit' 退出")
        except Exception as e:
            logger.error(f"交互式模式异常: {str(e)}")
            print(f"\n发生错误: {str(e)}")


def show_help():
    """显示帮助信息"""
    print("\n" + "="*60)
    print("Perfa LangChain Agent - 帮助信息")
    print("="*60)
    print("""
可用命令：
  exit, quit, q  - 退出交互模式
  help, h, ?     - 显示此帮助信息
  clear, cls     - 清屏

使用示例：
  测试 server-01 的CPU性能
  对比 server-01 和 server-02 的数据库性能
  查看所有服务器的状态
  在 server-01 上安装 unixbench 工具

提示：
  - 支持自然语言输入
  - 系统会自动选择合适的工具执行
  - 可以使用中文或英文查询
""")
    print("="*60)


def print_result(response):
    """
    打印执行结果
    
    Args:
        response: Agent响应（字典或对象）
    """
    print("\n" + "="*60)
    print("执行结果")
    print("="*60)
    
    # 兼容字典和对象两种格式
    if isinstance(response, dict):
        is_success = response.get('is_success', False)
        execution_time = response.get('execution_time', 0)
        result = response.get('result', '')
        tool_calls = response.get('tool_calls', [])
        error_message = response.get('error', '')
        thinking_process = response.get('thinking_process')
        reasoning_time = response.get('reasoning_time', 0)
    else:
        is_success = response.is_success
        execution_time = response.execution_time
        result = response.result
        tool_calls = response.tool_calls
        error_message = response.error_message
        thinking_process = response.thinking_process if hasattr(response, 'thinking_process') else None
        reasoning_time = response.reasoning_time if hasattr(response, 'reasoning_time') else 0
    
    if is_success:
        # 显示性能统计
        if reasoning_time and reasoning_time > 0:
            print("\n" + "-"*60)
            print("⏱️ 性能统计")
            print("-"*60)
            print(f"LLM推理时间: {reasoning_time:.2f}秒")
            tool_time = sum(call.get('execution_time', 0) if isinstance(call, dict) else call.execution_time for call in tool_calls)
            print(f"工具执行时间: {tool_time:.2f}秒")
            print(f"总执行时间: {execution_time:.2f}秒")
        
        print("\n" + "="*60)
        print(f"✓ 执行成功")
        print("="*60)
        print(f"\n{result}\n")
        
        # 显示工具调用信息
        if tool_calls:
            print("-"*60)
            print(f"工具调用（共 {len(tool_calls)} 次）:")
            print("-"*60)
            for i, call in enumerate(tool_calls, 1):
                if isinstance(call, dict):
                    tool_name = call.get('tool_name', '未知')
                    call_time = call.get('execution_time', 0)
                    args = call.get('arguments', {})
                else:
                    tool_name = call.tool_name
                    call_time = call.execution_time
                    args = call.arguments
                print(f"\n{i}. 工具: {tool_name}")
                print(f"   耗时: {call_time:.2f}秒")
                if args:
                    print(f"   参数: {args}")
    else:
        print(f"\n✗ 执行失败（耗时: {execution_time:.2f}秒）")
        print(f"\n错误信息: {error_message}\n")
        
        # 显示已执行的工具
        if tool_calls:
            print("-"*60)
            print(f"已执行的工具（共 {len(tool_calls)} 次）:")
            print("-"*60)
            for i, call in enumerate(tool_calls, 1):
                if isinstance(call, dict):
                    tool_name = call.get('tool_name', '未知')
                    call_time = call.get('execution_time', 0)
                else:
                    tool_name = call.tool_name
                    call_time = call.execution_time
                print(f"\n{i}. 工具: {tool_name}")
                print(f"   耗时: {call_time:.2f}秒")


async def single_query_mode(orchestrator: AgentOrchestrator, query: str):
    """
    单次查询模式
    
    Args:
        orchestrator: Agent编排器
        query: 查询内容
    """
    logger.info(f"执行单次查询: {query}")
    
    session_id = f"single_session_{uuid.uuid4().hex[:16]}"
    
    try:
        response = await orchestrator.process_query(query, session_id=session_id)
        print_result(response)
        
        # 如果有错误，退出码非0
        if isinstance(response, dict):
            if not response.get('is_success', False):
                exit(1)
        else:
            if not response.is_success:
                exit(1)
            
    except Exception as e:
        logger.error(f"单次查询异常: {str(e)}")
        print(f"\n执行失败: {str(e)}")
        exit(1)


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Perfa LangChain Agent CLI")
    parser.add_argument("--interactive", "-i", action="store_true", help="交互式模式")
    parser.add_argument("--query", "-q", type=str, help="单次查询模式，直接输入查询内容")
    parser.add_argument("--config", "-c", type=str, help="配置文件路径（可选）")
    parser.add_argument("--log-level", "-l", type=str, default="INFO", help="日志级别（DEBUG, INFO, WARNING, ERROR）")
    parser.add_argument("--log-file", "-f", type=str, help="日志文件路径（可选）")
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logger(args.log_level, args.log_file)
    
    logger.info("="*60)
    logger.info("Perfa LangChain Agent 启动")
    logger.info("="*60)
    
    try:
        # 加载配置
        logger.info("加载配置...")
        config = ConfigManager()
        
        # 验证配置
        validation = config.validate_configs()
        if validation["errors"]:
            logger.error(f"配置验证失败: {validation['errors']}")
            print("配置错误:")
            for error in validation["errors"]:
                print(f"  - {error}")
            exit(1)
        
        if validation["warnings"]:
            logger.warning(f"配置警告: {validation['warnings']}")
            print("配置警告:")
            for warning in validation["warnings"]:
                print(f"  - {warning}")
        
        # 创建MCP工具适配器
        logger.info("创建MCP工具适配器...")
        mcp_adapter = MCPToolAdapter(config.mcp.sse_url, config.mcp.api_key)
        
        # 连接到MCP Server
        logger.info("连接MCP Server...")
        connection_test = await mcp_adapter.test_connection()
        
        if not connection_test["success"]:
            logger.error(f"MCP Server连接失败: {connection_test['error']}")
            print(f"\n无法连接到MCP Server: {connection_test['error']}")
            print("请确保MCP Server已启动: python -m src.mcp_server.main")
            exit(1)
        
        print(f"\n✓ MCP Server连接成功")
        print(f"  - 可用工具: {connection_test['tool_count']} 个")
        print(f"  - 工具列表: {', '.join(connection_test['tool_names'][:5])}{'...' if connection_test['tool_count'] > 5 else ''}")
        
        # 创建Agent编排器
        logger.info("创建Agent编排器...")
        orchestrator = AgentOrchestrator(
            mcp_adapter=mcp_adapter,
            memory_max_turns=config.agent.memory_max_turns,
            memory_max_age_hours=config.agent.memory_max_age_hours
        )
        
        # 启动模式
        if args.interactive:
            await interactive_mode(orchestrator)
        elif args.query:
            await single_query_mode(orchestrator, args.query)
        else:
            # 默认进入交互式模式
            print("\n未指定查询，进入交互式模式...")
            await interactive_mode(orchestrator)
    
    except KeyboardInterrupt:
        logger.info("用户中断（Ctrl+C）")
        print("\n\n程序已终止")
    except Exception as e:
        logger.exception(f"程序异常: {str(e)}")
        print(f"\n程序发生严重错误: {str(e)}")
        exit(1)
    finally:
        logger.info("Perfa LangChain Agent 退出")


if __name__ == "__main__":
    asyncio.run(main())
