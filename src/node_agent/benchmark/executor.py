"""
压测任务执行器
"""
import os
import signal
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from pathlib import Path
import subprocess

from .task import BenchmarkTask, TaskStatus
from .result import ResultCollector
from .cleaner import Cleaner
from .runners.base import BaseRunner


logger = logging.getLogger(__name__)


class BenchmarkError(Exception):
    """压测错误基类"""
    pass


class ToolNotInstalledError(BenchmarkError):
    """工具未安装"""
    pass


class TaskRunningError(BenchmarkError):
    """已有任务在运行"""
    pass


class BenchmarkExecutor:
    """
    压测任务执行器
    
    负责：
    1. 管理任务的生命周期
    2. 确保同时只有一个任务运行（串行执行）
    3. 执行前后的现场清理
    4. 收集测试结果
    """

    def __init__(self, tool_manager, data_dir: str = "/var/lib/node_agent",
                 working_dir: str = "/tmp/benchmark_work"):
        """
        初始化执行器
        
        Args:
            tool_manager: 工具管理器实例
            data_dir: 数据存储目录
            working_dir: 工作目录
        """
        self.tool_manager = tool_manager
        self.result_collector = ResultCollector(data_dir)
        self.cleaner = Cleaner()
        self.working_dir = Path(working_dir)
        
        # 任务管理
        self._current_task: Optional[BenchmarkTask] = None
        self._task_lock = threading.Lock()
        self._tasks: Dict[str, BenchmarkTask] = {}
        
        # 运行器注册
        self._runners: Dict[str, BaseRunner] = {}
        
        # 回调函数
        self._on_status_change: Optional[Callable] = None
        self._on_log: Optional[Callable] = None
        
        # 确保工作目录存在
        self.working_dir.mkdir(parents=True, exist_ok=True)

    def register_runner(self, runner: BaseRunner):
        """注册运行器"""
        self._runners[runner.name] = runner
        logger.info(f"Registered runner: {runner.name}")

    def set_callbacks(self, on_status_change: Callable = None, on_log: Callable = None):
        """
        设置回调函数
        
        Args:
            on_status_change: 状态变化回调 (task_id, status)
            on_log: 日志回调 (task_id, log_line)
        """
        self._on_status_change = on_status_change
        self._on_log = on_log

    def is_busy(self) -> bool:
        """是否有任务在运行"""
        return self._current_task is not None

    def get_current_task(self) -> Optional[BenchmarkTask]:
        """获取当前运行的任务"""
        return self._current_task

    def run_benchmark(self, test_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行压测（阻塞或异步）
        
        Args:
            test_name: 测试名称
            params: 测试参数
        
        Returns:
            同步任务: {"task_id": "xxx", "status": "completed", "result": {...}}
            异步任务: {"task_id": "xxx", "status": "running"}
        """
        # 检查运行器
        if test_name not in self._runners:
            raise BenchmarkError(f"No runner registered for: {test_name}")
        
        runner = self._runners[test_name]

        # 检查是否忙碌
        with self._task_lock:
            if self.is_busy():
                raise TaskRunningError(
                    f"Task {self._current_task.task_id} is running, "
                    "only one benchmark can run at a time"
                )

            # 创建任务
            task = BenchmarkTask(
                task_id="",
                test_name=test_name,
                params=params
            )
            task.working_dir = str(self.working_dir / runner.get_working_subdir(task))
            self._tasks[task.task_id] = task
            self._current_task = task

        logger.info(f"Starting benchmark: {test_name}, task_id={task.task_id}")

        # 根据是否需要异步执行
        if runner.requires_async:
            return self._run_async(task, runner)
        else:
            return self._run_sync(task, runner)

    def _run_sync(self, task: BenchmarkTask, runner: BaseRunner) -> Dict[str, Any]:
        """同步执行"""
        try:
            self._execute_task(task, runner)
            return {
                "task_id": task.task_id,
                "status": task.status.value,
                "result": task.result,
                "error": task.error
            }
        finally:
            with self._task_lock:
                self._current_task = None

    def _run_async(self, task: BenchmarkTask, runner: BaseRunner) -> Dict[str, Any]:
        """异步执行"""
        def _run_in_thread():
            try:
                self._execute_task(task, runner)
            finally:
                with self._task_lock:
                    self._current_task = None

        thread = threading.Thread(target=_run_in_thread, daemon=True)
        thread.start()

        return {
            "task_id": task.task_id,
            "status": TaskStatus.RUNNING.value
        }

    def _execute_task(self, task: BenchmarkTask, runner: BaseRunner):
        """
        执行任务的核心逻辑
        """
        log_path = None
        
        try:
            # ========== 准备阶段 ==========
            self._update_status(task, TaskStatus.PREPARING)
            
            # 检查工具
            tool_status = self.tool_manager.check_tool(task.test_name)
            status = tool_status.get("status")
            # 支持 Enum 和字符串两种格式
            status_value = status.value if hasattr(status, 'value') else status
            if status_value != "installed":
                raise ToolNotInstalledError(
                    f"Tool {task.test_name} not installed: {tool_status}"
                )
            
            # 准备运行器
            if not runner.prepare(task, self.tool_manager):
                raise BenchmarkError("Runner prepare failed")
            
            # 创建工作目录
            os.makedirs(task.working_dir, exist_ok=True)
            
            # 创建日志文件
            log_path = self.result_collector.create_log_file(task)
            task.log_file = str(log_path)
            
            # 测试前清理
            self.cleaner.cleanup_before(task.working_dir, task.test_name)
            
            # ========== 执行阶段 ==========
            self._update_status(task, TaskStatus.RUNNING)
            task.start_time = datetime.now()
            
            # 构建命令
            cmd = runner.build_command(task)
            self._append_log(log_path, f"Command: {' '.join(cmd)}\n\n")
            
            # 获取超时时间
            timeout = runner.get_timeout(task.params)
            
            # 执行命令
            task.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=task.working_dir
            )
            
            # 读取输出
            output_lines = []
            while True:
                line = task.process.stdout.readline()
                if not line:
                    if task.process.poll() is not None:
                        break
                    continue
                
                output_lines.append(line)
                self._append_log(log_path, line)
                self._notify_log(task.task_id, line)
            
            returncode = task.process.wait()
            task.end_time = datetime.now()
            
            output = ''.join(output_lines)
            self._append_log(log_path, f"\n{'='*60}\n")
            self._append_log(log_path, f"Execution Finished\n")
            self._append_log(log_path, f"{'='*60}\n")
            self._append_log(log_path, f"End Time:    {task.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._append_log(log_path, f"Duration:    {task.duration_seconds:.2f} seconds\n")
            self._append_log(log_path, f"Exit Code:   {returncode}\n")
            if returncode != 0:
                self._append_log(log_path, f"Status:      FAILED\n")
            
            # ========== 采集结果 ==========
            self._update_status(task, TaskStatus.COLLECTING)
            
            if returncode == 0:
                metrics = runner.collect_result(task, output)
                result = self.result_collector.collect(task, metrics)
                task.result = result.to_dict()
            else:
                task.error = f"Process exited with code {returncode}"
            
            # ========== 清理阶段 ==========
            self._update_status(task, TaskStatus.CLEANING)
            self.cleaner.cleanup_after(task.working_dir, task.test_name, keep_log=True)
            
            # ========== 完成 ==========
            status = TaskStatus.COMPLETED if returncode == 0 else TaskStatus.FAILED
            self._update_status(task, status)
            
            # 保存结果
            self.result_collector.collect(task, task.result)
            
        except Exception as e:
            logger.error(f"Task {task.task_id} failed: {e}")
            task.error = str(e)
            task.end_time = datetime.now()
            self._update_status(task, TaskStatus.FAILED)
            
            # 记录错误日志
            if log_path:
                self._append_log(log_path, f"\n{'='*60}\n")
                self._append_log(log_path, f"ERROR\n")
                self._append_log(log_path, f"{'='*60}\n")
                self._append_log(log_path, f"Error: {e}\n")
            
            # 清理
            try:
                self.cleaner.cleanup_after(task.working_dir, task.test_name, keep_log=True)
            except:
                pass
            
            # 保存失败结果
            self.result_collector.collect(task, None)
            
        finally:
            task.process = None

    def _update_status(self, task: BenchmarkTask, status: TaskStatus):
        """更新任务状态"""
        task.status = status
        logger.info(f"Task {task.task_id} status: {status.value}")
        if self._on_status_change:
            try:
                self._on_status_change(task.task_id, status.value)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def _append_log(self, log_path: Path, content: str):
        """追加日志"""
        if log_path:
            self.result_collector.append_log(log_path, content)

    def _notify_log(self, task_id: str, line: str):
        """通知日志回调"""
        if self._on_log:
            try:
                self._on_log(task_id, line)
            except Exception as e:
                logger.error(f"Log callback error: {e}")

    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否取消成功
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"Task not found: {task_id}")
            return False
        
        if task.status not in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            logger.warning(f"Task {task_id} is not running, cannot cancel")
            return False
        
        if task.process:
            try:
                # 先 SIGTERM
                task.process.terminate()
                try:
                    task.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 然后 SIGKILL
                    task.process.kill()
                    task.process.wait()
                
                # 杀死进程树
                self.cleaner.kill_process_tree(task.process.pid)
                
            except Exception as e:
                logger.error(f"Failed to kill process: {e}")
        
        task.status = TaskStatus.CANCELLED
        task.end_time = datetime.now()
        task.error = "Cancelled by user"
        
        logger.info(f"Task {task_id} cancelled")
        return True

    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否暂停成功
        """
        task = self._tasks.get(task_id)
        if not task or not task.process:
            return False
        
        if task.status != TaskStatus.RUNNING:
            return False
        
        try:
            os.kill(task.process.pid, signal.SIGSTOP)
            task.status = TaskStatus.PAUSED
            logger.info(f"Task {task_id} paused")
            return True
        except Exception as e:
            logger.error(f"Failed to pause task: {e}")
            return False

    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
        
        Returns:
            是否恢复成功
        """
        task = self._tasks.get(task_id)
        if not task or not task.process:
            return False
        
        if task.status != TaskStatus.PAUSED:
            return False
        
        try:
            os.kill(task.process.pid, signal.SIGCONT)
            task.status = TaskStatus.RUNNING
            logger.info(f"Task {task_id} resumed")
            return True
        except Exception as e:
            logger.error(f"Failed to resume task: {e}")
            return False

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询任务状态
        
        Args:
            task_id: 任务ID
        
        Returns:
            任务状态信息
        """
        task = self._tasks.get(task_id)
        if not task:
            # 从数据库查询
            result = self.result_collector.get_result(task_id)
            if result:
                return result.to_dict()
            return None
        
        return task.to_dict()

    def list_tasks(self, status: str = None, limit: int = 50) -> list:
        """
        列出任务
        
        Args:
            status: 状态过滤
            limit: 数量限制
        
        Returns:
            任务列表
        """
        return [t.to_dict() for t in self._tasks.values()][-limit:]

    def get_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取测试结果
        
        Args:
            task_id: 任务ID
        
        Returns:
            结果字典
        """
        result = self.result_collector.get_result(task_id)
        return result.to_dict() if result else None

    def get_log_path(self, task_id: str) -> Optional[str]:
        """
        获取日志文件路径
        
        Args:
            task_id: 任务ID
        
        Returns:
            日志文件路径
        """
        path = self.result_collector.get_log_path(task_id)
        return str(path) if path else None
    
    def shutdown(self):
        """
        关闭执行器，清理资源
        """
        logger.info("Shutting down BenchmarkExecutor...")
        
        # 取消当前任务
        if self._current_task and self._current_task.status in [TaskStatus.RUNNING, TaskStatus.PAUSED]:
            logger.info(f"Cancelling running task: {self._current_task.task_id}")
            self.cancel_task(self._current_task.task_id)
        
        logger.info("BenchmarkExecutor shutdown complete")
