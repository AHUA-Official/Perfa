#!/usr/bin/env python3
"""
测试工具管理器功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from node_agent.tool import ToolManager
import json


def test_list_tools():
    """测试工具列表"""
    print("\n" + "="*60)
    print("测试：列出所有工具")
    print("="*60)
    
    manager = ToolManager()
    result = manager.list_tools()
    
    print(f"\n找到 {result['count']} 个工具:")
    for tool in result['tools']:
        print(f"  - {tool['name']:12} [{tool['category']:4}] {tool['status']:15} - {tool['description']}")


def test_check_tool(tool_name):
    """测试检查工具状态"""
    print("\n" + "="*60)
    print(f"测试：检查工具状态 - {tool_name}")
    print("="*60)
    
    manager = ToolManager()
    result = manager.check_tool(tool_name)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


def test_install_tool(tool_name):
    """测试安装工具"""
    print("\n" + "="*60)
    print(f"测试：安装工具 - {tool_name}")
    print("="*60)
    
    manager = ToolManager()
    result = manager.install_tool(tool_name)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))


def test_check_all(category=None):
    """测试批量检查工具状态"""
    print("\n" + "="*60)
    print(f"测试：批量检查工具状态 (类别: {category or '全部'})")
    print("="*60)
    
    manager = ToolManager()
    result = manager.check_all(category)
    
    print(f"\n找到 {result['count']} 个工具:")
    for tool in result['tools']:
        print(f"  - {tool['tool']:12} [{tool['category']:4}] {tool['status']:15}")


def test_install_all(category=None):
    """测试批量安装工具"""
    print("\n" + "="*60)
    print(f"测试：批量安装工具 (类别: {category or '全部'})")
    print("="*60)
    
    manager = ToolManager()
    result = manager.install_all(category)
    
    print(f"\n总计: {result['total']}, 成功: {result['success_count']}, 失败: {result['fail_count']}")
    for item in result['results']:
        status = "✓" if item['success'] else "✗"
        print(f"  {status} {item['tool']:12} - {item['message']}")


def interactive_test():
    """交互式测试"""
    manager = ToolManager()
    
    while True:
        print("\n" + "="*60)
        print("工具管理器测试菜单")
        print("="*60)
        print("1. 列出所有工具")
        print("2. 检查工具状态")
        print("3. 安装工具")
        print("4. 卸载工具")
        print("5. 批量检查")
        print("6. 批量安装")
        print("7. 批量卸载")
        print("0. 退出")
        print()
        
        choice = input("请选择操作 (0-7): ").strip()
        
        if choice == '0':
            print("退出测试")
            break
        elif choice == '1':
            test_list_tools()
        elif choice == '2':
            tool_name = input("请输入工具名称: ").strip()
            test_check_tool(tool_name)
        elif choice == '3':
            tool_name = input("请输入工具名称: ").strip()
            test_install_tool(tool_name)
        elif choice == '4':
            tool_name = input("请输入工具名称: ").strip()
            result = manager.uninstall_tool(tool_name)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif choice == '5':
            category = input("请输入类别 (cpu/mem/disk/net 或留空): ").strip() or None
            test_check_all(category)
        elif choice == '6':
            category = input("请输入类别 (cpu/mem/disk/net 或留空): ").strip() or None
            confirm = input(f"确认要安装所有 {category or '全部'} 工具吗？(y/n): ").strip().lower()
            if confirm == 'y':
                test_install_all(category)
        elif choice == '7':
            category = input("请输入类别 (cpu/mem/disk/net 或留空): ").strip() or None
            confirm = input(f"确认要卸载所有 {category or '全部'} 工具吗？(y/n): ").strip().lower()
            if confirm == 'y':
                result = manager.uninstall_all(category)
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("无效选择，请重新输入")


if __name__ == "__main__":
    # 设置日志
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        # 命令行模式
        command = sys.argv[1]
        
        if command == "list":
            test_list_tools()
        elif command == "check":
            tool_name = sys.argv[2] if len(sys.argv) > 2 else None
            if tool_name:
                test_check_tool(tool_name)
            else:
                test_check_all()
        elif command == "install":
            tool_name = sys.argv[2] if len(sys.argv) > 2 else None
            if tool_name:
                test_install_tool(tool_name)
            else:
                category = sys.argv[2] if len(sys.argv) > 2 else None
                test_install_all(category)
        else:
            print(f"未知命令: {command}")
            print("用法: python test_tool_manager.py [list|check|install] [tool_name|category]")
    else:
        # 交互模式
        interactive_test()
