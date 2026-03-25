"""
内存压力测试工具
"""
import shutil
import tarfile
from pathlib import Path
from typing import Dict
import logging

from .base import BaseTool, ToolStatus


logger = logging.getLogger(__name__)


class StreamTool(BaseTool):
    """STREAM 内存带宽测试工具"""
    
    def __init__(self):
        super().__init__(
            name="stream",
            description="STREAM - 内存带宽基准测试工具",
            category="mem"
        )
        self.tool_root = Path(__file__).parent
        self.source_dir = self.tool_root / "sources" / "mem"
        self.source_file = self.source_dir / "stream.c"
        self.binary_name = "stream"
    
    def install(self) -> bool:
        """安装STREAM - 本地编译"""
        logger.info(f"Installing {self.name}...")
        
        # 检查源码文件
        if not self.source_file.exists():
            logger.error(f"Source file not found: {self.source_file}")
            return False
        
        # 编译
        binary_path = self.binaries_dir / self.binary_name
        
        logger.info(f"Compiling STREAM from {self.source_file}...")
        returncode, stdout, stderr = self._run_command([
            "gcc", "-O3", "-fopenmp", "-DSTREAM_ARRAY_SIZE=100000000",
            "-o", str(binary_path), str(self.source_file)
        ], timeout=60)
        
        if returncode != 0:
            logger.error(f"Compilation failed: {stderr}")
            return False
        
        # 验证
        if binary_path.exists() and binary_path.stat().st_size > 0:
            self._make_executable(binary_path)
            self.binary_path = str(binary_path)
            logger.info(f"Successfully installed {self.name} at {self.binary_path}")
            return True
        else:
            logger.error("Compilation produced no output")
            return False
    
    def check(self) -> Dict:
        """检查STREAM状态"""
        binary_path = self.binaries_dir / self.binary_name
        
        if binary_path.exists() and binary_path.stat().st_size > 0:
            self.binary_path = str(binary_path)
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": "unknown",
                "message": "STREAM is installed and ready"
            }
        
        if self.source_file.exists():
            return {
                "status": ToolStatus.NOT_INSTALLED,
                "binary_path": None,
                "version": None,
                "message": "STREAM source found, ready to compile"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "STREAM not found"
        }
    
    def verify(self) -> bool:
        """验证 STREAM 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查二进制文件是否存在
        if not Path(self.binary_path).exists():
            return False
        
        # 快速测试：运行 STREAM（需要较长时间，但会输出信息）
        try:
            returncode, stdout, stderr = self._run_command(
                [self.binary_path],
                timeout=10
            )
            # STREAM 会输出 "STREAM version"
            return "STREAM version" in stdout or "STREAM version" in stderr
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载STREAM"""
        logger.info(f"Uninstalling {self.name}...")
        
        try:
            binary_path = self.binaries_dir / self.binary_name
            if binary_path.exists():
                binary_path.unlink()
            
            self.binary_path = None
            logger.info(f"Successfully uninstalled {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False


class MLCTool(BaseTool):
    """Intel MLC (Memory Latency Checker) 工具"""
    
    def __init__(self):
        super().__init__(
            name="mlc",
            description="Intel MLC - 内存延迟和带宽测试工具",
            category="mem"
        )
        self.tool_root = Path(__file__).parent
        self.source_dir = self.tool_root / "sources" / "mem"
        self.build_dir = self.source_dir / "mlc"
    
    def install(self) -> bool:
        """安装MLC - 解压并复制二进制"""
        logger.info(f"Installing {self.name}...")
        
        # 检查压缩包
        tar_file = self.source_dir / "mlc_v3.12.tgz"
        if not tar_file.exists():
            for f in self.source_dir.glob("mlc*.tgz"):
                tar_file = f
                break
        
        # 解压（如果需要）
        if tar_file.exists() and not self.build_dir.exists():
            logger.info(f"Extracting {tar_file}...")
            try:
                with tarfile.open(tar_file, 'r:gz') as tf:
                    tf.extractall(self.source_dir)
                
                # 重命名解压后的目录
                for d in self.source_dir.iterdir():
                    if d.is_dir() and "mlc" in d.name.lower() and d != self.build_dir:
                        d.rename(self.build_dir)
                        break
                        
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                return False
        
        # 查找二进制文件
        possible_binaries = [
            self.source_dir / "Linux" / "mlc",  # 直接解压到 sources/mem/Linux/
            self.build_dir / "Linux" / "mlc",
            self.build_dir / "mlc",
            self.source_dir / "mlc",
        ]
        
        for src_binary in possible_binaries:
            if src_binary.exists() and src_binary.is_file():
                # 复制到 binaries 目录
                dst_binary = self.binaries_dir / "mlc"
                shutil.copy2(src_binary, dst_binary)
                self._make_executable(dst_binary)
                self.binary_path = str(dst_binary)
                logger.info(f"Successfully installed {self.name} from {src_binary}")
                return True
        
        logger.error(f"MLC binary not found in {self.build_dir}")
        return False
    
    def check(self) -> Dict:
        """检查MLC状态"""
        binary_path = self.binaries_dir / "mlc"
        
        if binary_path.exists():
            self.binary_path = str(binary_path)
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": "unknown",
                "message": "MLC is installed and ready"
            }
        
        # 检查系统PATH
        if self._check_command_exists("mlc"):
            self.binary_path = shutil.which("mlc")
            return {
                "status": ToolStatus.AVAILABLE,
                "binary_path": self.binary_path,
                "version": "unknown",
                "message": "MLC is available in system PATH"
            }
        
        # 检查压缩包
        if any(self.source_dir.glob("mlc*.tgz")):
            return {
                "status": ToolStatus.NOT_INSTALLED,
                "binary_path": None,
                "version": None,
                "message": "MLC archive found, ready to install"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "MLC not found"
        }
    
    def verify(self) -> bool:
        """验证 MLC 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查二进制文件是否存在
        if not Path(self.binary_path).exists():
            return False
        
        # 快速测试：检查 MLC 帮助信息
        try:
            returncode, stdout, stderr = self._run_command(
                [self.binary_path, "--help"],
                timeout=2
            )
            # MLC 会输出 "Memory Latency Checker"
            return "Memory Latency Checker" in stdout or "Memory Latency Checker" in stderr
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载MLC"""
        logger.info(f"Uninstalling {self.name}...")
        
        try:
            binary_path = self.binaries_dir / "mlc"
            if binary_path.exists():
                binary_path.unlink()
            
            self.binary_path = None
            logger.info(f"Successfully uninstalled {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False
