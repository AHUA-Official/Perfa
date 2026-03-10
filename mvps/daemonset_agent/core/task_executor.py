"""
任务执行器
负责执行压测任务并管理进程
"""

import threading
import subprocess
import time
import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskExecutor:
    """任务执行器"""
    
    def __init__(
        self,
        agent_id: str,
        sqlite_writer,
        influxdb_writer
    ):
        """
        初始化任务执行器
        
        Args:
            agent_id: Agent ID
            sqlite_writer: SQLite写入器
            influxdb_writer: InfluxDB写入器
        """
        self.agent_id = agent_id
        self.sqlite_writer = sqlite_writer
        self.influxdb_writer = influxdb_writer
        
        # 当前任务
        self.current_task: Optional[Dict] = None
        self.current_process: Optional[subprocess.Popen] = None
        self.task_thread: Optional[threading.Thread] = None
        
        logger.info("任务执行器初始化完成")
    
    def run_benchmark(
        self,
        test_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行压测任务
        
        Args:
            test_name: 测试名称（unixbench/superpi等）
            params: 测试参数
        
        Returns:
            {
                "task_id": "bench_xxx",
                "status": "running",
                "message": "任务已启动"
            }
        """
        logger.info(f"执行压测: {test_name}, 参数: {params}")
        
        # 1. 检查是否有正在运行的任务
        if self.current_task and self.current_task['status'] == TaskStatus.RUNNING:
            return {
                "task_id": self.current_task['task_id'],
                "status": "error",
                "message": "已有任务正在运行"
            }
        
        # 2. 生成任务ID
        task_id = f"bench_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 3. 创建任务记录
        task = {
            'task_id': task_id,
            'test_name': test_name,
            'params': params,
            'status': TaskStatus.PENDING,
            'created_at': datetime.now().isoformat(),
            'agent_id': self.agent_id
        }
        
        # 4. 保存到SQLite
        self.sqlite_writer.save_task(task)
        
        # 5. 启动任务线程
        self.current_task = task
        self.task_thread = threading.Thread(
            target=self._execute_task,
            args=(task,),
            daemon=True
        )
        self.task_thread.start()
        
        return {
            "task_id": task_id,
            "status": "running",
            "test_name": test_name,
            "message": "任务已启动"
        }
    
    def _execute_task(self, task: Dict[str, Any]):
        """执行任务（线程函数）"""
        task_id = task['task_id']
        test_name = task['test_name']
        params = task['params']
        
        try:
            # 更新状态为运行中
            task['status'] = TaskStatus.RUNNING
            task['started_at'] = datetime.now().isoformat()
            self.sqlite_writer.update_task(task)
            
            logger.info(f"开始执行任务: {task_id}")
            
            # 根据测试类型选择执行器
            if test_name in ['unixbench', 'superpi', 'c-ray']:
                result = self._run_pts_benchmark(task_id, test_name, params)
            elif test_name.startswith('docker_'):
                result = self._run_docker_benchmark(task_id, test_name, params)
            else:
                result = self._run_native_benchmark(task_id, test_name, params)
            
            # 更新任务状态为完成
            task['status'] = TaskStatus.COMPLETED
            task['completed_at'] = datetime.now().isoformat()
            task['result'] = result
            self.sqlite_writer.update_task(task)
            
            logger.info(f"任务完成: {task_id}")
            
        except Exception as e:
            logger.error(f"任务执行失败: {e}", exc_info=True)
            task['status'] = TaskStatus.FAILED
            task['error'] = str(e)
            task['completed_at'] = datetime.now().isoformat()
            self.sqlite_writer.update_task(task)
        
        finally:
            self.current_task = None
            self.current_process = None
    
    def _run_pts_benchmark(
        self,
        task_id: str,
        test_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行PTS测试
        
        Args:
            task_id: 任务ID
            test_name: 测试名称
            params: 参数
        
        Returns:
            测试结果
        """
        logger.info(f"执行PTS测试: {test_name}")
        
        # 构建PTS命令
        iterations = params.get('iterations', 3)
        
        # PTS命令示例
        cmd = [
            'phoronix-test-suite',
            'benchmark',
            test_name,
            '--results-format', 'json',
            '--benchmark-count', str(iterations)
        ]
        
        # 执行命令
        self.current_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 读取输出
        stdout, stderr = self.current_process.communicate()
        
        # 检查返回码
        if self.current_process.returncode != 0:
            raise Exception(f"PTS测试失败: {stderr}")
        
        # 解析结果
        result = self._parse_pts_result(stdout)
        
        # 写入SQLite
        self.sqlite_writer.save_result({
            'task_id': task_id,
            'test_name': test_name,
            'score': result.get('score'),
            'raw_output': stdout,
            'parsed_result': result
        })
        
        return result
    
    def _parse_pts_result(self, output: str) -> Dict[str, Any]:
        """解析PTS输出"""
        # 简化实现：提取分数
        # 实际需要解析JSON输出
        return {
            'score': 0.0,
            'unit': '',
            'details': {}
        }
    
    def _run_docker_benchmark(
        self,
        task_id: str,
        test_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行Docker测试"""
        logger.info(f"执行Docker测试: {test_name}")
        # 实现逻辑
        return {}
    
    def _run_native_benchmark(
        self,
        task_id: str,
        test_name: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行原生测试"""
        logger.info(f"执行原生测试: {test_name}")
        # 实现逻辑
        return {}
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """取消任务"""
        logger.info(f"取消任务: {task_id}")
        
        if not self.current_task or self.current_task['task_id'] != task_id:
            return {
                "task_id": task_id,
                "status": "error",
                "message": "任务不存在"
            }
        
        # 终止进程
        if self.current_process:
            self.current_process.terminate()
            try:
                self.current_process.wait(timeout=5)
            except:
                self.current_process.kill()
        
        # 更新状态
        self.current_task['status'] = TaskStatus.CANCELLED
        self.current_task['cancelled_at'] = datetime.now().isoformat()
        self.sqlite_writer.update_task(self.current_task)
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "任务已取消"
        }
    
    def pause_task(self, task_id: str) -> Dict[str, Any]:
        """暂停任务"""
        logger.info(f"暂停任务: {task_id}")
        
        if not self.current_task or self.current_task['task_id'] != task_id:
            return {
                "task_id": task_id,
                "status": "error",
                "message": "任务不存在"
            }
        
        # 暂停进程
        if self.current_process:
            self.current_process.send_signal(subprocess.signal.SIGSTOP)
        
        # 更新状态
        self.current_task['status'] = TaskStatus.PAUSED
        self.sqlite_writer.update_task(self.current_task)
        
        return {
            "task_id": task_id,
            "status": "paused",
            "message": "任务已暂停"
        }
    
    def resume_task(self, task_id: str) -> Dict[str, Any]:
        """恢复任务"""
        logger.info(f"恢复任务: {task_id}")
        
        if not self.current_task or self.current_task['task_id'] != task_id:
            return {
                "task_id": task_id,
                "status": "error",
                "message": "任务不存在"
            }
        
        # 恢复进程
        if self.current_process:
            self.current_process.send_signal(subprocess.signal.SIGCONT)
        
        # 更新状态
        self.current_task['status'] = TaskStatus.RUNNING
        self.sqlite_writer.update_task(self.current_task)
        
        return {
            "task_id": task_id,
            "status": "running",
            "message": "任务已恢复"
        }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        # 从SQLite查询
        task = self.sqlite_writer.get_task(task_id)
        
        if not task:
            return {
                "task_id": task_id,
                "status": "error",
                "message": "任务不存在"
            }
        
        # 如果任务正在运行，获取实时进度
        if task['status'] == TaskStatus.RUNNING and self.current_process:
            task['progress'] = self._calculate_progress(task)
        
        return task
    
    def _calculate_progress(self, task: Dict) -> float:
        """计算任务进度"""
        # 简化实现
        # 实际需要解析进程输出或读取临时文件
        return 0.0
