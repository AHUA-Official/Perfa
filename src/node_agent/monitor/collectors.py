"""
系统指标采集器
使用 prometheus_client 暴露指标
"""

import logging
from typing import Dict, Any
from abc import ABC, abstractmethod

import psutil
from prometheus_client import Gauge, Counter, Info

from .info import system_info

logger = logging.getLogger(__name__)


# 全局系统信息指标（Info 类型，包含所有静态信息）
_node_info = Info('node_info', '系统静态信息')
_node_info.info(system_info.info)


class BaseCollector(ABC):
    """采集器基类"""
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """采集指标"""
        pass


class CPUCollector(BaseCollector):
    """CPU 指标采集器"""
    
    # Prometheus 指标定义（带 machine_id 标签）
    cpu_percent = Gauge('node_cpu_percent', 'CPU 使用率百分比', ['machine_id', 'hostname'])
    cpu_count = Gauge('node_cpu_count', 'CPU 核心数', ['machine_id', 'hostname'])
    cpu_freq_current = Gauge('node_cpu_freq_current_mhz', 'CPU 当前频率 (MHz)', ['machine_id', 'hostname'])
    cpu_freq_min = Gauge('node_cpu_freq_min_mhz', 'CPU 最小频率 (MHz)', ['machine_id', 'hostname'])
    cpu_freq_max = Gauge('node_cpu_freq_max_mhz', 'CPU 最大频率 (MHz)', ['machine_id', 'hostname'])
    
    def __init__(self):
        """初始化，获取系统标签"""
        self.labels = system_info.get_labels()
    
    def collect(self) -> Dict[str, Any]:
        """采集 CPU 指标"""
        cpu_percent = psutil.cpu_percent(interval=1.0)
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        
        # 更新 Prometheus 指标（带标签）
        self.cpu_percent.labels(**self.labels).set(cpu_percent)
        self.cpu_count.labels(**self.labels).set(cpu_count)
        
        metrics = {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
        }
        
        if cpu_freq:
            self.cpu_freq_current.labels(**self.labels).set(cpu_freq.current)
            self.cpu_freq_min.labels(**self.labels).set(cpu_freq.min)
            self.cpu_freq_max.labels(**self.labels).set(cpu_freq.max)
            metrics['cpu_freq_current_mhz'] = cpu_freq.current
            metrics['cpu_freq_min_mhz'] = cpu_freq.min
            metrics['cpu_freq_max_mhz'] = cpu_freq.max
        
        logger.debug(f"CPU 采集: cpu_percent={cpu_percent}%")
        return metrics


class MemoryCollector(BaseCollector):
    """内存指标采集器"""
    
    # Prometheus 指标定义（带 machine_id 标签）
    memory_total = Gauge('node_memory_total_bytes', '内存总量 (bytes)', ['machine_id', 'hostname'])
    memory_available = Gauge('node_memory_available_bytes', '可用内存 (bytes)', ['machine_id', 'hostname'])
    memory_used = Gauge('node_memory_used_bytes', '已用内存 (bytes)', ['machine_id', 'hostname'])
    memory_percent = Gauge('node_memory_percent', '内存使用率百分比', ['machine_id', 'hostname'])
    swap_total = Gauge('node_swap_total_bytes', 'Swap 总量 (bytes)', ['machine_id', 'hostname'])
    swap_used = Gauge('node_swap_used_bytes', 'Swap 已用 (bytes)', ['machine_id', 'hostname'])
    swap_percent = Gauge('node_swap_percent', 'Swap 使用率百分比', ['machine_id', 'hostname'])
    
    def __init__(self):
        """初始化，获取系统标签"""
        self.labels = system_info.get_labels()
    
    def collect(self) -> Dict[str, Any]:
        """采集内存指标"""
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # 更新 Prometheus 指标（带标签）
        self.memory_total.labels(**self.labels).set(mem.total)
        self.memory_available.labels(**self.labels).set(mem.available)
        self.memory_used.labels(**self.labels).set(mem.used)
        self.memory_percent.labels(**self.labels).set(mem.percent)
        self.swap_total.labels(**self.labels).set(swap.total)
        self.swap_used.labels(**self.labels).set(swap.used)
        self.swap_percent.labels(**self.labels).set(swap.percent)
        
        metrics = {
            'memory_total_gb': mem.total / (1024**3),
            'memory_available_gb': mem.available / (1024**3),
            'memory_used_gb': mem.used / (1024**3),
            'memory_percent': mem.percent,
            'swap_total_gb': swap.total / (1024**3),
            'swap_used_gb': swap.used / (1024**3),
            'swap_percent': swap.percent,
        }
        
        logger.debug(f"内存采集: memory_percent={mem.percent}%")
        return metrics


class DiskCollector(BaseCollector):
    """磁盘指标采集器"""
    
    # Prometheus 指标定义（带 machine_id 和 path 标签）
    disk_total = Gauge('node_disk_total_bytes', '磁盘总量 (bytes)', ['machine_id', 'hostname', 'path'])
    disk_used = Gauge('node_disk_used_bytes', '磁盘已用 (bytes)', ['machine_id', 'hostname', 'path'])
    disk_free = Gauge('node_disk_free_bytes', '磁盘可用 (bytes)', ['machine_id', 'hostname', 'path'])
    disk_percent = Gauge('node_disk_percent', '磁盘使用率百分比', ['machine_id', 'hostname', 'path'])
    disk_read_bytes = Counter('node_disk_read_bytes_total', '磁盘读取总字节数', ['machine_id', 'hostname'])
    disk_write_bytes = Counter('node_disk_write_bytes_total', '磁盘写入总字节数', ['machine_id', 'hostname'])
    
    def __init__(self, path: str = '/'):
        """初始化磁盘采集器
        
        Args:
            path: 要监控的磁盘路径
        """
        self.path = path
        self.labels = {**system_info.get_labels(), 'path': path}
    
    def collect(self) -> Dict[str, Any]:
        """采集磁盘指标"""
        disk = psutil.disk_usage(self.path)
        disk_io = psutil.disk_io_counters()
        
        # 更新 Prometheus 指标（带标签）
        self.disk_total.labels(**self.labels).set(disk.total)
        self.disk_used.labels(**self.labels).set(disk.used)
        self.disk_free.labels(**self.labels).set(disk.free)
        self.disk_percent.labels(**self.labels).set(disk.percent)
        
        metrics = {
            'disk_total_gb': disk.total / (1024**3),
            'disk_used_gb': disk.used / (1024**3),
            'disk_free_gb': disk.free / (1024**3),
            'disk_percent': disk.percent,
        }
        
        if disk_io:
            # Counter 类型不能 set，只能 inc，这里用 _total 命名表示累计值
            metrics['disk_read_bytes'] = disk_io.read_bytes
            metrics['disk_write_bytes'] = disk_io.write_bytes
            metrics['disk_read_count'] = disk_io.read_count
            metrics['disk_write_count'] = disk_io.write_count
        
        logger.debug(f"磁盘采集: disk_percent={disk.percent}%")
        return metrics


class NetworkCollector(BaseCollector):
    """网络指标采集器"""
    
    # Prometheus 指标定义（带 machine_id 标签）
    network_bytes_sent = Counter('node_network_sent_bytes_total', '网络发送总字节数', ['machine_id', 'hostname'])
    network_bytes_recv = Counter('node_network_recv_bytes_total', '网络接收总字节数', ['machine_id', 'hostname'])
    network_packets_sent = Counter('node_network_sent_packets_total', '网络发送总包数', ['machine_id', 'hostname'])
    network_packets_recv = Counter('node_network_recv_packets_total', '网络接收总包数', ['machine_id', 'hostname'])
    network_connections = Gauge('node_network_connections', '网络连接数', ['machine_id', 'hostname'])
    
    def __init__(self):
        """初始化，获取系统标签"""
        self.labels = system_info.get_labels()
    
    def collect(self) -> Dict[str, Any]:
        """采集网络指标"""
        net_io = psutil.net_io_counters()
        net_connections = len(psutil.net_connections())
        
        # 更新 Prometheus 指标（带标签）
        self.network_connections.labels(**self.labels).set(net_connections)
        
        metrics = {
            'network_bytes_sent': net_io.bytes_sent,
            'network_bytes_recv': net_io.bytes_recv,
            'network_packets_sent': net_io.packets_sent,
            'network_packets_recv': net_io.packets_recv,
            'network_connections': net_connections,
        }
        
        logger.debug(f"网络采集: connections={net_connections}")
        return metrics
