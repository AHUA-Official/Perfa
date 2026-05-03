"""
现场清理器
负责测试前后的环境清理
"""
import os
import signal
import logging
import shutil
from pathlib import Path
from typing import List, Optional
import psutil


logger = logging.getLogger(__name__)


class Cleaner:
    """现场清理器"""
    
    # 默认清理模式
    DEFAULT_PATTERNS = [
        "benchmark_*",          # 通用临时目录/文件
        "*.tmp",                # 临时文件
        "*.fio",                # fio临时文件
        "mlc_*",                # mlc临时文件
        "stream_*",             # stream临时文件
    ]
    
    # 需要清理的进程名
    PROCESS_NAMES = {
        "unixbench": ["Run", "ubench"],
        "superpi": ["super_pi"],
        "stream": ["stream"],
        "mlc": ["mlc", "mlc_avx512"],
        "fio": ["fio"],
        "hping3": ["hping3"],
    }
    
    def __init__(self, min_disk_space_gb: float = 5.0):
        """
        初始化清理器
        
        Args:
            min_disk_space_gb: 最小磁盘空间要求（GB）
        """
        self.min_disk_space_gb = min_disk_space_gb
    
    def cleanup_before(self, working_dir: str, test_name: str) -> bool:
        """
        测试前清理
        
        Args:
            working_dir: 工作目录
            test_name: 测试名称
        
        Returns:
            清理是否成功
        """
        logger.info(f"Cleaning up before test: {test_name}")
        
        try:
            # 1. 清理工作目录中遗留的临时文件
            self._clean_working_dir(working_dir, test_name)
            
            # 2. 杀死残留进程
            self._kill_residual_processes(test_name)
            
            # 3. 检查磁盘空间
            if not self._check_disk_space(working_dir):
                logger.warning(f"Low disk space, minimum required: {self.min_disk_space_gb}GB")
            
            logger.info("Pre-test cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Pre-test cleanup failed: {e}")
            return False
    
    def cleanup_after(self, working_dir: str, test_name: str, 
                      output_file: Optional[str] = None,
                      keep_log: bool = True) -> bool:
        """
        测试后清理
        
        Args:
            working_dir: 工作目录
            test_name: 测试名称
            output_file: 输出文件路径
            keep_log: 是否保留日志文件
        
        Returns:
            清理是否成功
        """
        logger.info(f"Cleaning up after test: {test_name}")
        
        try:
            # 1. 清理工作目录中的临时文件
            self._clean_working_dir(working_dir, test_name)
            
            # 2. 删除输出文件（如果不需要保留）
            if output_file and os.path.exists(output_file):
                if not keep_log:
                    os.remove(output_file)
                    logger.info(f"Removed output file: {output_file}")
            
            # 3. 确保进程已终止
            self._kill_residual_processes(test_name)
            
            logger.info("Post-test cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Post-test cleanup failed: {e}")
            return False
    
    def _clean_working_dir(self, working_dir: str, test_name: str):
        """清理工作目录"""
        if not os.path.exists(working_dir):
            os.makedirs(working_dir, exist_ok=True)
            return
        
        work_path = Path(working_dir)
        
        # 获取该测试特定的清理模式
        patterns = self._get_cleanup_patterns(test_name)
        
        cleaned_count = 0
        for pattern in patterns:
            for file_path in work_path.glob(pattern):
                try:
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    cleaned_count += 1
                    logger.debug(f"Cleaned: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean {file_path}: {e}")
        
        if cleaned_count > 0:
            logger.info(f"Cleaned {cleaned_count} items in working directory")
    
    def _get_cleanup_patterns(self, test_name: str) -> List[str]:
        """获取特定测试的清理模式"""
        base_patterns = self.DEFAULT_PATTERNS.copy()
        
        # 特定测试的额外模式
        test_specific = {
            "fio": ["*.fio", "fio_*"],
            "unixbench": ["ubench_*", "Run*", "pgms/*"],
            "stream": ["stream_*"],
            "mlc": ["mlc_*"],
        }
        
        if test_name in test_specific:
            base_patterns.extend(test_specific[test_name])
        
        return base_patterns
    
    def _kill_residual_processes(self, test_name: str):
        """杀死残留进程"""
        process_names = self.PROCESS_NAMES.get(test_name, [])
        
        killed_count = 0
        current_pid = os.getpid()
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # 跳过当前进程
                if proc.info['pid'] == current_pid:
                    continue
                
                # 检查进程名或命令行
                proc_name = proc.info['name'] or ''
                cmdline = proc.info['cmdline'] or []

                if self._matches_residual_process(proc_name, cmdline, process_names):
                    logger.warning(f"Killing residual process: PID={proc.info['pid']}, name={proc_name}")
                    proc.kill()
                    killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if killed_count > 0:
            logger.info(f"Killed {killed_count} residual processes")

    def _matches_residual_process(self, proc_name: str, cmdline: List[str], process_names: List[str]) -> bool:
        """
        判断进程是否是目标测试的残留进程。

        只匹配真实可执行名，避免把请求参数中包含测试名的客户端进程
        （例如 curl ... '{"test_name":"stream"}'）误杀。
        """
        candidates = set()

        if proc_name:
            candidates.add(proc_name.lower())
            candidates.add(Path(proc_name).name.lower())

        if cmdline:
            executable = cmdline[0]
            if executable:
                candidates.add(executable.lower())
                candidates.add(Path(executable).name.lower())

        for name in process_names:
            lowered = name.lower()
            if lowered in candidates:
                return True

        return False
    
    def _check_disk_space(self, path: str) -> bool:
        """检查磁盘空间"""
        try:
            stat = os.statvfs(path)
            # 可用空间（GB）
            available_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            
            if available_gb < self.min_disk_space_gb:
                logger.warning(f"Low disk space: {available_gb:.2f}GB available, "
                             f"{self.min_disk_space_gb}GB required")
                return False
            
            logger.info(f"Disk space check passed: {available_gb:.2f}GB available")
            return True
            
        except Exception as e:
            logger.error(f"Failed to check disk space: {e}")
            return True  # 检查失败时不阻止执行
    
    def kill_process_tree(self, pid: int):
        """
        杀死进程树（包括子进程）
        
        Args:
            pid: 进程ID
        """
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # 先发送 SIGTERM
            for child in children:
                try:
                    child.terminate()
                except psutil.NoSuchProcess:
                    pass
            
            # 等待子进程结束
            gone, alive = psutil.wait_procs(children, timeout=5)
            
            # 强制杀死仍在运行的进程
            for proc in alive:
                try:
                    proc.kill()
                except psutil.NoSuchProcess:
                    pass
            
            # 最后杀死父进程
            try:
                parent.terminate()
                parent.wait(timeout=5)
            except psutil.TimeoutExpired:
                parent.kill()
            except psutil.NoSuchProcess:
                pass
                
            logger.info(f"Killed process tree: PID={pid}")
            
        except psutil.NoSuchProcess:
            logger.debug(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Failed to kill process tree {pid}: {e}")
    
    def clean_patterns(self, patterns: List[str], base_dir: str) -> int:
        """
        按模式清理文件
        
        Args:
            patterns: 文件模式列表
            base_dir: 基础目录
        
        Returns:
            清理的文件数量
        """
        base_path = Path(base_dir)
        if not base_path.exists():
            return 0
        
        cleaned_count = 0
        for pattern in patterns:
            for file_path in base_path.glob(pattern):
                try:
                    if file_path.is_dir():
                        shutil.rmtree(file_path)
                    else:
                        file_path.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean {file_path}: {e}")
        
        return cleaned_count
