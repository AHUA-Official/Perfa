"""Agent HTTP 客户端"""
import requests
from typing import Optional, Dict, Any
from .models import AgentStatus, SystemInfo, SystemStatus, BenchmarkResult


class AgentClient:
    """Agent HTTP 客户端"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        初始化客户端
        
        Args:
            base_url: Agent 地址，如 http://192.168.1.100:8080
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
    
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送请求"""
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        
        data = response.json()
        if not data.get("success"):
            raise Exception(data.get("error", "Unknown error"))
        
        return data.get("data", {})
    
    def health_check(self) -> bool:
        """健康检查"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_status(self) -> AgentStatus:
        """获取 Agent 状态"""
        data = self._request("GET", "/api/status")
        # 兼容 Agent 不返回 status 字段的情况
        if "status" not in data:
            data["status"] = "online"
        return AgentStatus(**data)
    
    def get_system_info(self) -> SystemInfo:
        """获取系统信息（静态）"""
        data = self._request("GET", "/api/system/info")
        return SystemInfo(**data["system"])
    
    def get_system_status(self) -> SystemStatus:
        """获取系统状态（实时）"""
        data = self._request("GET", "/api/system/status")
        return SystemStatus.from_agent_response(data)
    
    # Tool 管理
    
    def list_tools(self) -> list:
        """列出工具"""
        data = self._request("GET", "/api/tools")
        return data.get("tools", [])
    
    def get_tool(self, tool_name: str) -> Dict[str, Any]:
        """获取工具信息"""
        return self._request("GET", f"/api/tools/{tool_name}")
    
    def install_tool(self, tool_name: str) -> Dict[str, Any]:
        """安装工具"""
        return self._request("POST", f"/api/tools/{tool_name}/install")
    
    def uninstall_tool(self, tool_name: str) -> Dict[str, Any]:
        """卸载工具"""
        return self._request("POST", f"/api/tools/{tool_name}/uninstall")
    
    # Benchmark 管理
    
    def run_benchmark(self, test_name: str, params: Dict[str, Any]) -> str:
        """
        执行压测
        
        Returns:
            task_id
        """
        data = self._request("POST", "/api/benchmark/run", json={
            "test_name": test_name,
            "params": params
        })
        return data["task_id"]
    
    def get_benchmark_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return self._request("GET", f"/api/benchmark/tasks/{task_id}")
    
    def get_benchmark_result(self, task_id: str) -> BenchmarkResult:
        """获取任务结果"""
        data = self._request("GET", f"/api/benchmark/results/{task_id}")
        return BenchmarkResult(**data)
    
    def list_benchmark_results(self, test_name: Optional[str] = None, limit: int = 100) -> list:
        """列出历史结果"""
        params = {"limit": limit}
        if test_name:
            params["test_name"] = test_name
        
        data = self._request("GET", "/api/benchmark/results", params=params)
        return data.get("results", [])
    
    def cancel_benchmark(self, task_id: str) -> bool:
        """取消任务"""
        data = self._request("POST", "/api/benchmark/cancel", json={"task_id": task_id})
        return data.get("cancelled", False)
    
    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """获取当前运行的任务"""
        try:
            data = self._request("GET", "/api/benchmark/current")
            return data.get("current_task")
        except:
            return None
    
    # 日志
    
    def get_logs(self, lines: int = 100, level: Optional[str] = None) -> str:
        """获取日志"""
        params = {"lines": lines}
        if level:
            params["level"] = level
        
        data = self._request("GET", "/api/storage/logs", params=params)
        return data.get("logs", "")
