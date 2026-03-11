#!/usr/bin/env python3
"""
工具管理器使用示例
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from node_agent.tool import ToolManager


def main():
    # 初始化工具管理器
    manager = ToolManager()
    
    # 1. 列出所有工具
    print("=" * 60)
    print("1. 列出所有工具")
    print("=" * 60)
    result = manager.list_tools()
    for tool in result['tools']:
        print(f"  {tool['name']:12} [{tool['category']:4}] {tool['status']:15}")
    
    # 2. 检查fio状态
    print("\n" + "=" * 60)
    print("2. 检查fio状态")
    print("=" * 60)
    status = manager.check_tool("fio")
    print(f"  状态: {status['status']}")
    print(f"  消息: {status['message']}")
    
    # 3. 批量检查磁盘和网络工具
    print("\n" + "=" * 60)
    print("3. 批量检查磁盘工具状态")
    print("=" * 60)
    result = manager.check_all(category="disk")
    for tool in result['tools']:
        print(f"  {tool['tool']:12} [{tool['category']:4}] {tool['status']:15}")
    
    print("\n提示: 要安装工具，请使用 manager.install_tool('tool_name')")
    print("示例: manager.install_tool('fio')")


if __name__ == "__main__":
    main()
