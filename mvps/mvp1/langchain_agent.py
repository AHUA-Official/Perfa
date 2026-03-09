from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from pydantic import SecretStr



async def main() -> None:
    load_dotenv()

    api_key = os.getenv("DEEPSEEK_API_KEY")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

    if not api_key:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY")


    async with MultiServerMCPClient(
        {
            "perfa-mvp1": {
                "command": "python",
                "args": ["mcp_server.py"],
                "transport": "stdio",
            }
        }
    ) as mcp_client:
        tools = mcp_client.get_tools()

        llm = ChatOpenAI(
            model="deepseek-chat",
            api_key=SecretStr(api_key),

            base_url=base_url,
            temperature=0,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "你是服务器性能测试助手。先确认是否已注册服务器；未注册则调用 register_server。随后调用 check_connection 与 benchmark_cpu。",
                ),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
        executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        query = (
            "请先查看已注册服务器。"
            "如果不存在目标服务器，请提示我先调用 register_server 提供连接信息。"
            "若已存在可用服务器，则先 check_connection，再执行一次 threads=1 的 CPU 测试，并给出结果摘要。"
        )
        result = await executor.ainvoke({"input": query})

        print(result["output"])


if __name__ == "__main__":
    asyncio.run(main())
