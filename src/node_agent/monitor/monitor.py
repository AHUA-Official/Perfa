"""
监控管理器
定期采集系统资源指标并输出日志
"""

import threading
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .collectors import (
    BaseCollector,
    CPUCollector,
    MemoryCollector,
    DiskCollector,
    NetworkCollector
)

logger = logging.getLogger(__name__)


class Monitor:
    """监控管理器"""
    
    def __init__(
        self,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化监控管理器
        
        Args:
            agent_id: Agent ID
            config: 监控配置
                - interval: 采样间隔(秒)，默认 5
                - enabled_metrics: 启用的指标列表，默认全部启用
        """
        self.agent_id = agent_id
        self.config = config or {}
        
        # 监控状态
        self.running = False
        self.interval = self.config.get('interval', 5)
        self.enabled_metrics = self.config.get('enabled_metrics', [
            'cpu', 'memory', 'disk', 'network'
        ])
        
        # 采集器实例
        self.collectors = self._init_collectors()
        
        # 监控线程
        self._thread: Optional[threading.Thread] = None
        
        logger.info(f"监控管理器初始化完成 [agent_id={agent_id}, interval={self.interval}s]")
    
    def _init_collectors(self) -> Dict[str, BaseCollector]:
        """初始化采集器"""
        collectors = {}
        
        if 'cpu' in self.enabled_metrics:
            collectors['cpu'] = CPUCollector()
        
        if 'memory' in self.enabled_metrics:
            collectors['memory'] = MemoryCollector()
        
        if 'disk' in self.enabled_metrics:
            collectors['disk'] = DiskCollector()
        
        if 'network' in self.enabled_metrics:
            collectors['network'] = NetworkCollector()
        
        logger.info(f"已初始化采集器: {list(collectors.keys())}")
        return collectors
    
    def start(self):
        """启动监控（非阻塞，在后台线程运行）"""
        if self.running:
            logger.warning("监控已在运行中")
            return
        
        logger.info("启动监控线程...")
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
    
    def stop(self):
        """停止监控"""
        if not self.running:
            return
        
        logger.info("停止监控...")
        self.running = False
        
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        
        logger.info("监控已停止")
    
    def _run(self):
        """监控主循环"""
        logger.info("监控线程启动")
        
        while self.running:
            try:
                # 采集指标
                metrics = self._collect_metrics()
                
                # 输出日志
                self._log_metrics(metrics)
                
                # 等待下一次采集
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"监控采集失败: {e}", exc_info=True)
                time.sleep(self.interval)
        
        logger.info("监控线程已退出")
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """采集所有指标"""
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': self.agent_id
        }
        
        # 遍历所有采集器采集数据
        for name, collector in self.collectors.items():
            try:
                data = collector.collect()
                metrics.update(data)
            except Exception as e:
                logger.error(f"{name} 采集器执行失败: {e}")
        
        return metrics
    
    def _log_metrics(self, metrics: Dict[str, Any]):
        """输出指标日志"""
        # 提取关键指标用于日志输出
        log_parts = []
        
        if 'cpu_percent' in metrics:
            log_parts.append(f"CPU={metrics['cpu_percent']:.1f}%")
        
        if 'memory_percent' in metrics:
            log_parts.append(f"Memory={metrics['memory_percent']:.1f}%")
        
        if 'disk_percent' in metrics:
            log_parts.append(f"Disk={metrics['disk_percent']:.1f}%")
        
        if 'network_connections' in metrics:
            log_parts.append(f"NetConn={metrics['network_connections']}")
        
        logger.info(f"系统监控 [{self.agent_id}]: {' | '.join(log_parts)}")
        
        # 输出详细指标（DEBUG 级别）
        logger.debug(f"详细指标: {metrics}")
    
    def is_running(self) -> bool:
        """检查监控是否在运行"""
        return self.running
