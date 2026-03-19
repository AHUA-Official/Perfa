"""
Perfa LangChain Agent - 可执行包入口

使用方式:
    python -m src.langchain_agent [命令] [选项]

@author: Perfa Team
@date: 2026-03-18
"""

import sys
import os

# 将项目根目录添加到sys.path
# 这是解决导入问题的关键
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 将src目录添加到sys.path  
src_dir = os.path.join(project_root, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 现在可以安全地导入模块
from langchain_agent.main import main

if __name__ == "__main__":
    # 调用main函数时传递sys.argv[1:]（去掉第一个参数，即包名）
    sys.argv[0] = 'langchain_agent'  # 重置程序名称
    main()
