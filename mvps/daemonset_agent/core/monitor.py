"""
监控采集器
本地采集系统指标并直接写入InfluxDB
"""

import threading
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class Monitor:
    """监控管理器"""
    
    def __init__(
        self,
        agent_id: str,
        influxdb_writer,
        config: Dict[str, Any]
    ):
        """
        初始化监控管理器
        
        Args:
            agent_id: Agent ID
            influxdb_writer: InfluxDB写入器
            config: 监控配置
        """
        self.agent_id = agent_id
        self.influxdb_writer = influxdb_writer
        self.config = config
        
        # 监控状态
        self.running = False
        self.interval = config.get('interval', 5)  # 采样间隔
        self.enabled_metrics = config.get('metrics', [
            'cpu_percent', 'memory_used', 'cpu_temp', 'power'
        ])
        
        # 当前任务ID（如果有）
        self.current_task_id: Optional[str] = None
        
        # 采集器实例
        self.collectors = self._init_collectors()
        
        logger.info(f"监控管理器初始化完成，采样间隔: {self.interval}秒")
    
    def _init_collectors(self) -> Dict:
        """初始化采集器"""
        from collectors.cpu_collector import CPUCollector
        from collectors.memory_collector import MemoryCollector
        from collectors.gpu_collector import GPUCollector
        from collectors.thermal_collector import ThermalCollector
        from collectors.power_collector import PowerCollector
        
        collectors = {}
        
        if 'cpu_percent' in self.enabled_metrics:
            collectors['cpu'] = CPUCollector()
        
        if 'memory_used' in self.enabled_metrics:
            collectors['memory'] = MemoryCollector()
        
        if 'gpu_temp' in self.enabled_metrics or 'gpu_freq' in self.enabled_metrics:
            collectors['gpu'] = GPUCollector()
        
        if 'cpu_temp' in self.enabled_metrics:
            collectors['thermal'] = ThermalCollector()
        
        if 'power' in self.enabled_metrics:
            collectors['power'] = PowerCollector()
        
        logger.info(f"已初始化采集器: {list(collectors.keys())}")
        return collectors
    
    def start(self):
        """启动监控（阻塞运行）"""
        logger.info("监控线程启动")
        self.running = True
        
        while self.running:
            try:
                # 采集指标
                metrics = self._collect_metrics()
                
                # 直接写入InfluxDB
                self._write_to_influxdb(metrics)
                
                # 等待下一次采集
                time.sleep(self.interval)
                
            except Exception as e:
                logger.error(f"监控采集失败: {e}", exc_info=True)
                time.sleep(self.interval)
        
        logger.info("监控线程已停止")
    
    def stop(self):
        """停止监控"""
        logger.info("停止监控...")
        self.running = False
    
    def set_task_id(self, task_id: Optional[str]):
        """设置当前任务ID"""
        self.current_task_id = task_id
        logger.info(f"监控关联任务: {task_id}")
    
    def _collect_metrics(self) -> Dict[str, Any]:
        """采集所有指标"""
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'agent_id': self.agent_id
        }
        
        # 如果有关联任务，添加task_id
        if self.current_task_id:
            metrics['task_id'] = self.current_task_id
        
        # CPU指标
        if 'cpu' in self.collectors:
            cpu_metrics = self.collectors['cpu'].collect()
            metrics.update(cpu_metrics)
        
        # 内存指标
        if 'memory' in self.collectors:
            memory_metrics = self.collectors['memory'].collect()
            metrics.update(memory_metrics)
        
        # GPU指标
        if 'gpu' in self.collectors:
            gpu_metrics = self.collectors['gpu'].collect()
            metrics.update(gpu_metrics)
        
        # 温度指标
        if 'thermal' in self.collectors:
            thermal_metrics = self.collectors['thermal'].collect()
            metrics.update(thermal_metrics)
        
        # 功耗指标
        if 'power' in self.collectors:
            power_metrics = self.collectors['power'].collect()
            metrics.update(power_metrics)
        
        return metrics
    
    def _write_to_influxdb(self, metrics: Dict[str, Any]):
        """
        直接写入InfluxDB（不走MCP）
        
        这是关键设计：Agent本地采集后直接写入数据库
        """
        try:
            # 构建InfluxDB数据点
            point = {
                "measurement": "system_metrics",
                "tags": {
                    "agent_id": self.agent_id
                },
                "fields": {}
            }
            
            # 添加task_id标签（如果有关联任务）
            if 'task_id' in metrics:
                point['tags']['task_id'] = metrics['task_id']
            
            # 提取指标值
            for key, value in metrics.items():
                if key not in ['timestamp', 'agent_id', 'task_id']:
                    point['fields'][key] = value
            
            # 写入InfluxDB
            self.influxdb_writer.write_point(point)
            
            logger.debug(f"已写入InfluxDB: {point['fields']}")
            
        except Exception as e:
            logger.error(f"写入InfluxDB失败: {e}")


# ==================== 采集器接口 ====================

class BaseCollector:
    """采集器基类"""
    
    def collect(self) -> Dict[str, Any]:
        """采集指标"""
        raise NotImplementedError


# ==================== 示例采集器 ====================

class CPUCollector(BaseCollector):
    """CPU指标采集器"""
    
    def collect(self) -> Dict[str, Any]:
        """采集CPU指标"""
        import psutil
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=0.1),
            'cpu_freq_mhz': psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            'cpu_count': psutil.cpu_count()
        }


class MemoryCollector(BaseCollector):
    """内存指标采集器"""
    
    def collect(self) -> Dict[str, Any]:
        """采集内存指标"""
        import psutil
        
        mem = psutil.virtual_memory()
        return {
            'memory_used_gb': mem.used / (1024**3),
            'memory_available_gb': mem.available / (1024**3),
            'memory_percent': mem.percent
        }


class ThermalCollector(BaseCollector):
    """温度指标采集器"""
    
    def collect(self) -> Dict[str, Any]:
        """采集温度指标"""
        try:
            import psutil
            
            temps = psutil.sensors_temperatures()
            if temps:
                # 获取CPU温度（假设第一个核心）
                for name, entries in temps.items():
                    if entries:
                        return {
                            'cpu_temp_c': entries[0].current
                        }
        except:
            pass
        
        return {'cpu_temp_c': 0}


class GPUCollector(BaseCollector):
    """GPU指标采集器"""
    
    def collect(self) -> Dict[str, Any]:
        """采集GPU指标"""
        try:
            import pynvml
            pynvml.nvmlInit()
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            
            return {
                'gpu_temp_c': pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU),
                'gpu_util_percent': pynvml.nvmlDeviceGetUtilizationRates(handle).gpu,
                'gpu_memory_used_mb': pynvml.nvmlDeviceGetMemoryInfo(handle).used / (1024**2),
                'gpu_freq_mhz': pynvml.nvmlDeviceGetClockInfo(handle, pynvml.NVML_CLOCK_GRAPHICS)
            }
        except Exception as e:
            logger.warning(f"GPU采集失败: {e}")
            return {}
        finally:
            try:
                pynvml.nvmlShutdown()
            except:
                pass


class PowerCollector(BaseCollector):
    """功耗指标采集器"""
    
    def collect(self) -> Dict[str, Any]:
        """采集功耗指标"""
        # 这需要特定的硬件支持
        # 简化实现：返回0
        return {
            'power_w': 0.0
        }
