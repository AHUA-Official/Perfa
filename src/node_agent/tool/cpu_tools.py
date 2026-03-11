"""
CPU压力测试工具
"""
import os
import shutil
import zipfile
import tarfile
from pathlib import Path
from typing import Dict
import logging

from .base import BaseTool, ToolStatus


logger = logging.getLogger(__name__)


class UnixBenchTool(BaseTool):
    """UnixBench CPU性能测试工具"""
    
    def __init__(self):
        super().__init__(
            name="unixbench",
            description="UnixBench - Unix系统性能测试套件",
            category="cpu"
        )
        self.tool_root = Path(__file__).parent
        self.source_dir = self.tool_root / "sources" / "cpu"
        self.build_dir = self.source_dir / "unixbench"
    
    def install(self) -> bool:
        """安装UnixBench - 解压并编译"""
        logger.info(f"Installing {self.name}...")
        
        # 检查压缩包
        zip_file = self.source_dir / "byte-unixbench-master.zip"
        if not zip_file.exists():
            for f in self.source_dir.glob("*unixbench*.tar.gz"):
                zip_file = f
                break
        
        # 解压（如果需要）
        if zip_file.exists() and not self.build_dir.exists():
            logger.info(f"Extracting {zip_file}...")
            try:
                if zip_file.suffix == ".zip":
                    with zipfile.ZipFile(zip_file, 'r') as zf:
                        zf.extractall(self.source_dir)
                else:
                    with tarfile.open(zip_file, 'r:gz') as tf:
                        tf.extractall(self.source_dir)
                
                # 重命名解压后的目录
                for d in self.source_dir.iterdir():
                    if d.is_dir() and "unixbench" in d.name.lower() and d != self.build_dir:
                        d.rename(self.build_dir)
                        break
                        
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                return False
        
        # 检查源码目录
        if not self.build_dir.exists():
            logger.error(f"Source directory not found: {self.build_dir}")
            return False
        
        # 查找 UnixBench 目录
        unixbench_dir = self.build_dir / "UnixBench"
        if not unixbench_dir.exists():
            unixbench_dir = self.build_dir
        
        run_script = unixbench_dir / "Run"
        if not run_script.exists():
            logger.error(f"Run script not found in {unixbench_dir}")
            return False
        
        # 编译
        logger.info(f"Compiling UnixBench in {unixbench_dir}...")
        returncode, stdout, stderr = self._run_command(
            ["make"],
            cwd=str(unixbench_dir),
            timeout=300
        )
        
        if returncode != 0:
            logger.error(f"Compilation failed: {stderr}")
            return False
        
        # 确保 Run 脚本有执行权限
        if run_script.exists():
            self._make_executable(run_script)
        
        # UnixBench 需要整个目录才能运行，创建启动脚本到 binaries
        binary_wrapper = self.binaries_dir / "unixbench"
        wrapper_content = f"""#!/bin/bash
# UnixBench wrapper script
cd "{unixbench_dir}"
exec ./Run "$@"
"""
        
        with open(binary_wrapper, 'w') as f:
            f.write(wrapper_content)
        
        self._make_executable(binary_wrapper)
        self.binary_path = str(binary_wrapper)
        
        logger.info(f"Successfully installed {self.name}")
        logger.info(f"Binary wrapper: {self.binary_path}")
        logger.info(f"Source directory: {unixbench_dir}")
        return True
    
    def check(self) -> Dict:
        """检查UnixBench状态"""
        # 检查 wrapper 脚本
        binary_wrapper = self.binaries_dir / "unixbench"
        
        if binary_wrapper.exists():
            self.binary_path = str(binary_wrapper)
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": "unknown",
                "message": "UnixBench is installed and ready"
            }
        
        # 检查源码
        unixbench_dir = self.build_dir / "UnixBench" if self.build_dir.exists() else None
        if not unixbench_dir or not unixbench_dir.exists():
            unixbench_dir = self.build_dir
        
        if unixbench_dir and unixbench_dir.exists():
            run_script = unixbench_dir / "Run"
            if run_script.exists():
                # 检查是否有编译产物
                pgms_dir = unixbench_dir / "pgms"
                has_binary = pgms_dir.exists() and any(
                    (pgms_dir / name).exists()
                    for name in ["dhry2reg", "whetstone.double", "execl"]
                )
                
                if has_binary:
                    return {
                        "status": ToolStatus.NOT_INSTALLED,
                        "binary_path": None,
                        "version": None,
                        "message": "UnixBench compiled but not installed to binaries"
                    }
                else:
                    return {
                        "status": ToolStatus.NOT_INSTALLED,
                        "binary_path": None,
                        "version": None,
                        "message": "UnixBench extracted, ready to compile"
                    }
        
        # 检查压缩包
        zip_file = self.source_dir / "byte-unixbench-master.zip"
        if zip_file.exists() or any(self.source_dir.glob("*unixbench*")):
            return {
                "status": ToolStatus.NOT_INSTALLED,
                "binary_path": None,
                "version": None,
                "message": "UnixBench archive found, ready to install"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "UnixBench not found"
        }
    
    def verify(self) -> bool:
        """验证 UnixBench 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查 wrapper 脚本是否存在
        if not Path(self.binary_path).exists():
            return False
        
        # 检查 Run 脚本是否存在
        run_script = self.build_dir / "UnixBench" / "Run"
        if not run_script.exists():
            return False
        
        # 快速测试：检查 Run 脚本能否输出帮助信息
        try:
            returncode, stdout, stderr = self._run_command(
                [str(run_script)],
                timeout=2
            )
            # Run 脚本即使出错也会输出 "Run:" 字样
            return "Run:" in stdout or "Run:" in stderr or "Usage" in stdout or "Usage" in stderr
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载UnixBench - 清理编译产物和 wrapper"""
        logger.info(f"Uninstalling {self.name}...")
        
        try:
            # 清理 wrapper
            binary_wrapper = self.binaries_dir / "unixbench"
            if binary_wrapper.exists():
                binary_wrapper.unlink()
            
            # 清理编译产物
            unixbench_dir = self.build_dir / "UnixBench"
            if not unixbench_dir.exists():
                unixbench_dir = self.build_dir
            
            if unixbench_dir.exists():
                self._run_command(["make", "clean"], cwd=str(unixbench_dir), timeout=30)
            
            self.binary_path = None
            logger.info(f"Successfully cleaned {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False


class SuperPiTool(BaseTool):
    """SuperPi CPU性能测试工具"""
    
    def __init__(self):
        super().__init__(
            name="superpi",
            description="SuperPi - CPU浮点计算性能测试",
            category="cpu"
        )
        self.tool_root = Path(__file__).parent
        self.source_dir = self.tool_root / "sources" / "cpu"
        self.build_dir = self.source_dir / "superpi"
    
    def install(self) -> bool:
        """安装SuperPi - 解压并复制到 binaries"""
        logger.info(f"Installing {self.name}...")
        
        # 检查压缩包
        zip_file = self.source_dir / "SuperPI-main.zip"
        if not zip_file.exists():
            for f in self.source_dir.glob("*[Ss]uper[Pp][Ii]*"):
                zip_file = f
                break
        
        # 解压（如果需要）
        if zip_file.exists() and not self.build_dir.exists():
            logger.info(f"Extracting {zip_file}...")
            try:
                with zipfile.ZipFile(zip_file, 'r') as zf:
                    zf.extractall(self.source_dir)
                
                # 重命名
                for d in self.source_dir.iterdir():
                    if d.is_dir() and "superpi" in d.name.lower() and d != self.build_dir:
                        d.rename(self.build_dir)
                        break
                        
            except Exception as e:
                logger.error(f"Extraction failed: {e}")
                return False
        
        # 检查源码目录
        if not self.build_dir.exists():
            logger.error(f"Source directory not found: {self.build_dir}")
            return False
        
        # 查找可执行文件
        possible_binaries = [
            self.build_dir / "pi_css5",
            self.build_dir / "super_pi",
            self.build_dir / "SuperPi",
            self.build_dir / "pi",
        ]
        
        src_binary = None
        for binary in possible_binaries:
            if binary.exists() and binary.is_file():
                # 检查是否是可执行文件
                if os.access(binary, os.X_OK) or not any(binary.suffix == ext for ext in [".c", ".cpp", ".h", ".o"]):
                    src_binary = binary
                    break
        
        # 如果没找到，尝试编译
        if not src_binary and (self.build_dir / "Makefile").exists():
            logger.info(f"Compiling SuperPi in {self.build_dir}...")
            returncode, stdout, stderr = self._run_command(
                ["make"],
                cwd=str(self.build_dir),
                timeout=60
            )
            
            if returncode != 0:
                logger.error(f"Compilation failed: {stderr}")
                return False
            
            # 再次查找
            for binary in possible_binaries:
                if binary.exists() and binary.is_file():
                    src_binary = binary
                    break
        
        if not src_binary:
            logger.error(f"No executable found in {self.build_dir}")
            return False
        
        # 复制到 binaries 目录
        dst_binary = self.binaries_dir / "superpi"
        logger.info(f"Copying {src_binary} to {dst_binary}...")
        shutil.copy2(src_binary, dst_binary)
        self._make_executable(dst_binary)
        
        self.binary_path = str(dst_binary)
        logger.info(f"Successfully installed {self.name}")
        logger.info(f"Binary: {self.binary_path}")
        logger.info(f"Source: {src_binary}")
        return True
    
    def check(self) -> Dict:
        """检查SuperPi状态"""
        # 检查 binaries 目录
        binary_path = self.binaries_dir / "superpi"
        
        if binary_path.exists():
            self.binary_path = str(binary_path)
            return {
                "status": ToolStatus.INSTALLED,
                "binary_path": self.binary_path,
                "version": "unknown",
                "message": "SuperPi is installed and ready"
            }
        
        # 检查源码目录
        if self.build_dir.exists():
            possible_binaries = [
                self.build_dir / "pi_css5",
                self.build_dir / "super_pi",
                self.build_dir / "SuperPi",
                self.build_dir / "pi",
            ]
            
            for binary in possible_binaries:
                if binary.exists() and binary.is_file():
                    return {
                        "status": ToolStatus.NOT_INSTALLED,
                        "binary_path": None,
                        "version": None,
                        "message": "SuperPi binary found but not installed to binaries"
                    }
        
        # 检查压缩包
        if any(self.source_dir.glob("*[Ss]uper[Pp][Ii]*")):
            return {
                "status": ToolStatus.NOT_INSTALLED,
                "binary_path": None,
                "version": None,
                "message": "SuperPi archive found, ready to install"
            }
        
        return {
            "status": ToolStatus.NOT_INSTALLED,
            "binary_path": None,
            "version": None,
            "message": "SuperPi not found"
        }
    
    def verify(self) -> bool:
        """验证 SuperPi 是否可用"""
        if not self.binary_path:
            return False
        
        # 检查二进制文件是否存在
        if not Path(self.binary_path).exists():
            return False
        
        # 快速测试：计算 1000 位 PI
        try:
            returncode, stdout, stderr = self._run_command(
                [self.binary_path, "1000"],
                timeout=3
            )
            # SuperPi 成功运行会输出 "Calculation of PI"
            return returncode == 0 and ("Calculation of PI" in stdout or "Calculation of PI" in stderr)
        except Exception:
            return False
    
    def uninstall(self) -> bool:
        """卸载SuperPi"""
        logger.info(f"Uninstalling {self.name}...")
        
        try:
            # 删除 binaries 中的文件
            binary_path = self.binaries_dir / "superpi"
            if binary_path.exists():
                binary_path.unlink()
            
            # 清理源码目录的编译产物
            if self.build_dir.exists():
                self._run_command(["make", "clean"], cwd=str(self.build_dir), timeout=30)
            
            self.binary_path = None
            logger.info(f"Successfully uninstalled {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Uninstall failed: {e}")
            return False
