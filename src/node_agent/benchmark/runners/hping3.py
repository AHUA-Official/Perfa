"""
hping3 网络探测和压力测试运行器
"""
import re
from typing import Dict, Any, List, Optional

from .base import BaseRunner
from ..task import BenchmarkTask


class Hping3Runner(BaseRunner):
    """
    hping3 网络探测和压力测试运行器
    
    hping3 是网络探测工具，可以发送自定义TCP/IP数据包
    测试时间根据配置而定
    """
    
    name = "hping3"
    description = "hping3 - Network probing and stress test tool"
    category = "net"
    typical_duration_seconds = 60  # 1分钟
    requires_async = False
    
    def prepare(self, task: BenchmarkTask, tool_manager) -> bool:
        """准备测试环境"""
        tool = tool_manager.get_tool("hping3")
        if not tool:
            return False
        
        status = tool.check()
        status_value = status.get("status")
        # 支持 Enum 和字符串两种格式
        if hasattr(status_value, 'value'):
            status_value = status_value.value
        
        if status_value != "installed":
            return False
        
        self.binary_path = tool.binary_path
        return True
    
    def build_command(self, task: BenchmarkTask) -> List[str]:
        """
        构建执行命令
        
        hping3 常用参数：
        - --flood: 洪水模式（需要root权限）
        - -S: SYN包
        - -p: 目标端口
        - --rand-source: 随机源地址
        """
        params = task.params or {}
        target = params.get("target", "localhost")
        mode = params.get("mode", "ping")  # ping, flood, syn
        port = params.get("port", 80)
        count = params.get("count", 10)
        
        cmd = ["sudo", self.binary_path]
        
        if mode == "ping":
            # 普通ICMP ping
            cmd.extend(["-1", "-c", str(count), target])
        elif mode == "syn":
            # SYN扫描
            cmd.extend(["-S", "-p", str(port), "-c", str(count), target])
        elif mode == "flood":
            # SYN flood (需要root)
            cmd.extend(["--flood", "-S", "-p", str(port), target])
        else:
            # 默认TCP ping
            cmd.extend(["-c", str(count), target])
        
        return cmd
    
    def collect_result(self, task: BenchmarkTask, output: str) -> Dict[str, Any]:
        """
        解析 hping3 输出
        
        典型输出：
        HPING localhost (lo 127.0.0.1): NO FLAGS are set, 40 headers + 0 data bytes
        len=40 ip=127.0.0.1 ttl=64 id=12345 sport=80 flags=RA seq=0 win=0 rtt=0.3 ms
        len=40 ip=127.0.0.1 ttl=64 id=12346 sport=80 flags=RA seq=1 win=0 rtt=0.2 ms
        
        --- localhost hping statistic ---
        10 packets transmitted, 10 packets received, 0% packet loss
        round-trip min/avg/max = 0.2/0.3/0.5 ms
        """
        metrics = {
            "mode": task.params.get("mode", "ping"),
            "target": task.params.get("target", "localhost"),
            "packets_sent": None,
            "packets_received": None,
            "packet_loss_percent": None,
            "rtt_min_ms": None,
            "rtt_avg_ms": None,
            "rtt_max_ms": None,
        }
        
        # 解析丢包统计
        # 格式: X packets transmitted, Y packets received, Z% packet loss
        stats_match = re.search(
            r"(\d+)\s+packets?\s+transmitted[,\s]+(\d+)\s+packets?\s+received[,\s]+(\d+)%?\s*packet\s+loss",
            output, 
            re.IGNORECASE
        )
        if stats_match:
            metrics["packets_sent"] = int(stats_match.group(1))
            metrics["packets_received"] = int(stats_match.group(2))
            metrics["packet_loss_percent"] = float(stats_match.group(3))
        
        # 解析RTT统计
        # 格式: round-trip min/avg/max = 0.2/0.3/0.5 ms
        rtt_match = re.search(
            r"round-trip[^=]*=\s*([\d.]+)/([\d.]+)/([\d.]+)\s*ms",
            output,
            re.IGNORECASE
        )
        if rtt_match:
            metrics["rtt_min_ms"] = float(rtt_match.group(1))
            metrics["rtt_avg_ms"] = float(rtt_match.group(2))
            metrics["rtt_max_ms"] = float(rtt_match.group(3))
        
        return metrics
    
    def get_cleanup_patterns(self) -> List[str]:
        """获取需要清理的文件模式"""
        return ["hping3_*"]
    
    def get_timeout(self, params: Dict[str, Any]) -> Optional[int]:
        """获取超时时间"""
        count = params.get("count", 10)
        mode = params.get("mode", "ping")
        
        if mode == "flood":
            return 120  # 洪水模式最多2分钟
        else:
            # 每个包约1秒 + 缓冲
            return max(30, count + 30)
    
    def validate_params(self, params: Dict[str, Any]) -> List[str]:
        """验证参数"""
        errors = []
        
        target = params.get("target", "localhost")
        if not target:
            errors.append("target is required")
        
        mode = params.get("mode", "ping")
        valid_modes = ["ping", "syn", "flood"]
        if mode not in valid_modes:
            errors.append(f"Invalid mode: {mode}, must be one of {valid_modes}")
        
        count = params.get("count", 10)
        if count < 1 or count > 100000:
            errors.append("count must be between 1 and 100000")
        
        return errors
