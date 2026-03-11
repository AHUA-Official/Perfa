"""
工具管理器
统一管理所有压力测试工具的生命周期
"""
import logging
from typing import Dict, List, Optional
from pathlib import Path

from .base import BaseTool, ToolStatus
from .cpu_tools import UnixBenchTool, SuperPiTool
from .mem_tools import StreamTool, MLCTool
from .disk_tools import FioTool
from .net_tools import Hping3Tool


logger = logging.getLogger(__name__)


class ToolManager:
    """工具管理器"""
    
    def __init__(self):
        """初始化工具管理器"""
        self.tools: Dict[str, BaseTool] = {}
        self._register_tools()
    
    def _register_tools(self):
        """注册所有工具"""
        # CPU测试工具
        self.tools["unixbench"] = UnixBenchTool()
        self.tools["superpi"] = SuperPiTool()
        
        # 内存测试工具
        self.tools["stream"] = StreamTool()
        self.tools["mlc"] = MLCTool()
        
        # 磁盘测试工具
        self.tools["fio"] = FioTool()
        
        # 网络测试工具
        self.tools["hping3"] = Hping3Tool()
    
    def install_tool(self, tool_name: str) -> Dict:
        """
        安装指定工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            安装结果字典
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found"
            }
        
        tool = self.tools[tool_name]
        logger.info(f"Installing tool: {tool_name}")
        
        try:
            success = tool.install()
            
            return {
                "success": success,
                "tool": tool_name,
                "message": f"Successfully installed {tool_name}" if success else f"Failed to install {tool_name}",
                "info": tool.get_info()
            }
        except Exception as e:
            logger.error(f"Error installing {tool_name}: {e}")
            return {
                "success": False,
                "tool": tool_name,
                "message": f"Error: {str(e)}"
            }
    
    def check_tool(self, tool_name: str) -> Dict:
        """
        检查指定工具状态
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具状态字典
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found"
            }
        
        tool = self.tools[tool_name]
        status = tool.check()
        
        return {
            "success": True,
            "tool": tool_name,
            **status,
            "info": tool.get_info()
        }
    
    def uninstall_tool(self, tool_name: str) -> Dict:
        """
        卸载指定工具
        
        Args:
            tool_name: 工具名称
        
        Returns:
            卸载结果字典
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found"
            }
        
        tool = self.tools[tool_name]
        logger.info(f"Uninstalling tool: {tool_name}")
        
        try:
            success = tool.uninstall()
            
            return {
                "success": success,
                "tool": tool_name,
                "message": f"Successfully uninstalled {tool_name}" if success else f"Failed to uninstall {tool_name}"
            }
        except Exception as e:
            logger.error(f"Error uninstalling {tool_name}: {e}")
            return {
                "success": False,
                "tool": tool_name,
                "message": f"Error: {str(e)}"
            }
    
    def list_tools(self, category: Optional[str] = None) -> Dict:
        """
        列出所有工具
        
        Args:
            category: 工具类别过滤 (cpu/mem/disk/net)，None表示所有类别
        
        Returns:
            工具列表字典
        """
        tools_list = []
        
        for name, tool in self.tools.items():
            if category is None or tool.category == category:
                status = tool.check()
                tools_list.append({
                    "name": name,
                    "description": tool.description,
                    "category": tool.category,
                    "status": status["status"],
                    "binary_path": status.get("binary_path"),
                    "version": status.get("version")
                })
        
        return {
            "success": True,
            "tools": tools_list,
            "count": len(tools_list)
        }
    
    def install_all(self, category: Optional[str] = None) -> Dict:
        """
        安装所有工具（或指定类别的工具）
        
        Args:
            category: 工具类别过滤
        
        Returns:
            安装结果字典
        """
        results = []
        success_count = 0
        fail_count = 0
        
        for name, tool in self.tools.items():
            if category is None or tool.category == category:
                result = self.install_tool(name)
                results.append({
                    "tool": name,
                    "success": result["success"],
                    "message": result["message"]
                })
                
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
        
        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }
    
    def check_all(self, category: Optional[str] = None, verify: bool = False) -> Dict:
        """
        检查所有工具状态（或指定类别的工具）
        
        Args:
            category: 工具类别过滤
            verify: 是否验证工具功能
        
        Returns:
            状态检查结果字典
        """
        results = []
        
        for name, tool in self.tools.items():
            if category is None or tool.category == category:
                status = tool.check()
                
                # 如果工具已安装且需要验证，则验证工具功能
                verified = False
                if verify and status["status"] == ToolStatus.INSTALLED:
                    verified = tool.verify()
                    if not verified:
                        status["status"] = ToolStatus.ERROR
                        status["message"] = f"{status['message']} (verification failed)"
                
                results.append({
                    "tool": name,
                    "category": tool.category,
                    "status": status["status"],
                    "binary_path": status.get("binary_path"),
                    "version": status.get("version"),
                    "message": status["message"],
                    "verified": verified if verify else None
                })
        
        return {
            "success": True,
            "tools": results,
            "count": len(results)
        }
    
    def uninstall_all(self, category: Optional[str] = None) -> Dict:
        """
        卸载所有工具（或指定类别的工具）
        
        Args:
            category: 工具类别过滤
        
        Returns:
            卸载结果字典
        """
        results = []
        success_count = 0
        fail_count = 0
        
        for name, tool in self.tools.items():
            if category is None or tool.category == category:
                result = self.uninstall_tool(name)
                results.append({
                    "tool": name,
                    "success": result["success"],
                    "message": result["message"]
                })
                
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
        
        return {
            "success": True,
            "total": len(results),
            "success_count": success_count,
            "fail_count": fail_count,
            "results": results
        }
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        获取工具实例
        
        Args:
            tool_name: 工具名称
        
        Returns:
            工具实例，不存在则返回None
        """
        return self.tools.get(tool_name)
