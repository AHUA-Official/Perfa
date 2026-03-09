from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from typing import Any


def setup_logging() -> logging.Logger:
    """配置日志格式，包含文件名、行号和执行信息"""
    logger = logging.getLogger("perfa-agent")
    logger.setLevel(logging.DEBUG)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)-4d | %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)

    return logger


log = setup_logging()


from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def _parse_mcp_result(result: Any) -> dict:
    """解析 MCP 工具返回格式 [{'type': 'text', 'text': '...json...'}]"""
    if isinstance(result, list) and len(result) > 0:
        text_content = result[0].get("text", "{}")
        return json.loads(text_content) if isinstance(text_content, str) else {}
    return result if isinstance(result, dict) else {}


async def get_mcp_tools(mcp_client) -> list:
    """获取 MCP 工具（langchain_mcp_adapters 已转换为 LangChain 格式）"""
    mcp_tools = await mcp_client.get_tools()
    log.debug(f"获取到 {len(mcp_tools)} 个 MCP 工具")
    return mcp_tools


SYSTEM_PROMPT = """你是一个服务器性能测试助手，帮助用户管理和测试远程服务器。

你有以下工具可用：
- register_server: 注册新服务器
- list_registered_servers: 列出已注册服务器
- check_connection: 检查服务器连接
- benchmark_cpu: 执行 CPU 性能测试
- get_cpu_benchmark_history: 获取历史测试记录

你的职责：
1. 理解用户的自然语言指令
2. 自主决定需要调用哪些工具
3. 根据工具结果决定下一步行动
4. 用中文与用户交流，解释你在做什么

示例对话：
用户: 帮我测试 demo 服务器的 CPU 性能
助手: 好的，我先检查 demo 服务器是否已注册，然后测试连接，最后执行 CPU 测试。

用户: 注册一个新服务器，IP 是 192.168.1.100
助手: 好的，我需要一些信息来注册服务器。请问用户名和密码是什么？

注意：
- 执行操作前先确认服务器已注册且连接正常
- 如果缺少必要信息，主动询问用户
- 测试完成后，给出简洁的结果分析
"""


async def main() -> None:
    log.info("=" * 60)
    log.info("Perfa Interactive Agent 启动")
    log.info("=" * 60)

    load_dotenv()
    log.debug("加载 .env 环境变量完成")

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not api_key:
        log.error("缺少 DEEPSEEK_API_KEY 环境变量")
        raise RuntimeError("缺少 DEEPSEEK_API_KEY")

    # 初始化 MCP 客户端
    log.info("初始化 MCP 客户端...")
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except Exception as exc:
        log.error("缺少依赖 langchain-mcp-adapters")
        raise RuntimeError(
            "缺少依赖 langchain-mcp-adapters，请先执行: pip install langchain-mcp-adapters"
        ) from exc

    mcp_client = MultiServerMCPClient(
        {
            "perfa-mvp1": {
                "command": sys.executable,
                "args": ["mcp_server.py"],
                "transport": "stdio",
            }
        }
    )
    log.debug("MCP 客户端配置完成")

    # 获取 MCP 工具（已转换为 LangChain 格式）
    log.info("获取 MCP 工具列表...")
    tools = await get_mcp_tools(mcp_client)
    log.info(f"可用工具: {[t.name for t in tools]}")

    # 创建 LLM
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=SecretStr(api_key),
        base_url=base_url,
        temperature=0,
    )

    # 绑定工具
    llm_with_tools = llm.bind_tools(tools)

    log.info("Agent 初始化完成，开始交互式对话")
    print("\n" + "=" * 60)
    print("Perfa Agent - 服务器性能测试助手")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60 + "\n")

    # 对话历史
    messages: list = [SystemMessage(content=SYSTEM_PROMPT)]

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        log.info(f"用户输入: {user_input}")
        messages.append(HumanMessage(content=user_input))

        # Agent 循环：思考 -> 行动 -> 观察
        iteration = 0
        max_iterations = 10

        while iteration < max_iterations:
            iteration += 1
            log.debug(f"Agent 迭代 {iteration}")

            # 调用 LLM
            response = await llm_with_tools.ainvoke(messages)
            messages.append(response)

            # 检查是否有工具调用
            tool_calls = response.tool_calls or []

            if not tool_calls:
                # 没有工具调用，输出最终回复
                content = response.content or ""
                print(f"\n助手: {content}\n")
                log.info(f"Agent 回复完成")
                break

            # 执行工具调用
            log.info(f"调用工具: {[tc['name'] for tc in tool_calls]}")

            for tool_call in tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_id = tool_call["id"]

                log.debug(f"  工具: {tool_name}, 参数: {tool_args}")

                # 查找并执行工具
                tool_func = next((t for t in tools if t.name == tool_name), None)
                if tool_func:
                    try:
                        raw_result = await tool_func.ainvoke(tool_args)
                        # 解析 MCP 返回格式
                        parsed = _parse_mcp_result(raw_result)
                        result = json.dumps(parsed, ensure_ascii=False, indent=2)
                        log.debug(f"  结果: {result[:200]}..." if len(result) > 200 else f"  结果: {result}")
                    except Exception as e:
                        result = f"工具执行失败: {e}"
                        log.error(f"  错误: {e}")

                    # 添加工具结果到消息历史
                    messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                else:
                    log.error(f"工具不存在: {tool_name}")
                    messages.append(
                        ToolMessage(content=f"错误：工具 {tool_name} 不存在", tool_call_id=tool_id)
                    )

        if iteration >= max_iterations:
            log.warning("达到最大迭代次数")
            print("\n助手: 抱歉，我无法在限定步数内完成任务，请简化您的请求。\n")


if __name__ == "__main__":
    asyncio.run(main())
