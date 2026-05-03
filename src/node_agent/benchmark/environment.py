"""
Benchmark environment snapshot collector.

The snapshot is collected immediately before a benchmark process starts so the
report can explain result differences caused by node-local state such as block
schedulers, page cache pressure, CPU governors, and filesystem context.
"""
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class EnvironmentSnapshotCollector:
    """Collects low-cost, read-only evidence about the benchmark host."""

    COMMAND_TIMEOUT_SECONDS = 3

    def collect(self, working_dir: Optional[str] = None) -> Dict[str, Any]:
        return {
            "collected_at": datetime.now().isoformat(),
            "hostname": platform.node(),
            "kernel": f"{platform.system()} {platform.release()}",
            "working_dir": working_dir,
            "loadavg": self._loadavg(),
            "memory": self._memory_snapshot(),
            "vm": self._vm_snapshot(),
            "block_devices": self._block_device_snapshot(),
            "cpu": self._cpu_snapshot(),
            "filesystem": self._filesystem_snapshot(working_dir),
            "commands": self._command_snapshot(),
        }

    def _loadavg(self) -> Dict[str, Any]:
        try:
            one, five, fifteen = os.getloadavg()
            return {"1m": one, "5m": five, "15m": fifteen}
        except OSError as exc:
            return {"error": str(exc)}

    def _memory_snapshot(self) -> Dict[str, Any]:
        keys = {
            "MemTotal",
            "MemFree",
            "MemAvailable",
            "Buffers",
            "Cached",
            "SwapCached",
            "Dirty",
            "Writeback",
            "SwapTotal",
            "SwapFree",
            "Slab",
            "SReclaimable",
        }
        values: Dict[str, int] = {}
        try:
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    key, _, rest = line.partition(":")
                    if key in keys:
                        values[f"{key}_kb"] = int(rest.strip().split()[0])
        except Exception as exc:
            values["error"] = str(exc)
        return values

    def _vm_snapshot(self) -> Dict[str, Any]:
        paths = {
            "swappiness": "/proc/sys/vm/swappiness",
            "dirty_ratio": "/proc/sys/vm/dirty_ratio",
            "dirty_background_ratio": "/proc/sys/vm/dirty_background_ratio",
            "dirty_expire_centisecs": "/proc/sys/vm/dirty_expire_centisecs",
            "dirty_writeback_centisecs": "/proc/sys/vm/dirty_writeback_centisecs",
            "vfs_cache_pressure": "/proc/sys/vm/vfs_cache_pressure",
            "overcommit_memory": "/proc/sys/vm/overcommit_memory",
            "zone_reclaim_mode": "/proc/sys/vm/zone_reclaim_mode",
            "transparent_hugepage_enabled": "/sys/kernel/mm/transparent_hugepage/enabled",
            "transparent_hugepage_defrag": "/sys/kernel/mm/transparent_hugepage/defrag",
        }
        return {name: self._read_text(path) for name, path in paths.items() if Path(path).exists()}

    def _block_device_snapshot(self) -> List[Dict[str, Any]]:
        devices: List[Dict[str, Any]] = []
        sys_block = Path("/sys/block")
        if not sys_block.exists():
            return devices

        for device in sorted(sys_block.iterdir()):
            if not device.is_dir() or device.name.startswith(("loop", "ram")):
                continue
            queue = device / "queue"
            scheduler_raw = self._read_text(queue / "scheduler")
            devices.append({
                "name": device.name,
                "scheduler": self._parse_scheduler(scheduler_raw),
                "scheduler_raw": scheduler_raw,
                "rotational": self._read_text(queue / "rotational"),
                "read_ahead_kb": self._read_text(queue / "read_ahead_kb"),
                "nr_requests": self._read_text(queue / "nr_requests"),
                "logical_block_size": self._read_text(queue / "logical_block_size"),
                "physical_block_size": self._read_text(queue / "physical_block_size"),
            })
        return devices

    def _cpu_snapshot(self) -> Dict[str, Any]:
        cpufreq = Path("/sys/devices/system/cpu")
        governors: Dict[str, int] = {}
        current_freqs: List[int] = []

        for governor_path in sorted(cpufreq.glob("cpu[0-9]*/cpufreq/scaling_governor")):
            governor = self._read_text(governor_path)
            if governor:
                governors[governor] = governors.get(governor, 0) + 1
            freq = self._read_text(governor_path.parent / "scaling_cur_freq")
            if freq and freq.isdigit():
                current_freqs.append(int(freq))

        snapshot: Dict[str, Any] = {"cpu_count": os.cpu_count(), "governors": governors}
        if current_freqs:
            snapshot["scaling_cur_freq_khz_min"] = min(current_freqs)
            snapshot["scaling_cur_freq_khz_max"] = max(current_freqs)
        return snapshot

    def _filesystem_snapshot(self, working_dir: Optional[str]) -> Dict[str, Any]:
        target = Path(working_dir or ".")
        try:
            target.mkdir(parents=True, exist_ok=True)
            stat = os.statvfs(str(target))
            return {
                "path": str(target),
                "free_bytes": stat.f_bavail * stat.f_frsize,
                "total_bytes": stat.f_blocks * stat.f_frsize,
                "mount": self._find_mount(str(target.resolve())),
            }
        except Exception as exc:
            return {"path": str(target), "error": str(exc)}

    def _command_snapshot(self) -> Dict[str, Dict[str, Any]]:
        commands = {
            "uname": ["uname", "-a"],
            "uptime": ["uptime"],
            "df": ["df", "-T", "-P"],
            "lsblk": ["lsblk", "-o", "NAME,TYPE,SIZE,ROTA,SCHED,MOUNTPOINT"],
        }
        return {name: self._run_command(cmd) for name, cmd in commands.items()}

    def _run_command(self, cmd: List[str]) -> Dict[str, Any]:
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
            return {
                "command": cmd,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip()[:4000],
                "stderr": completed.stderr.strip()[:1000],
            }
        except FileNotFoundError:
            return {"command": cmd, "error": "command not found"}
        except subprocess.TimeoutExpired:
            return {"command": cmd, "error": "timeout"}
        except Exception as exc:
            return {"command": cmd, "error": str(exc)}

    def _find_mount(self, target: str) -> Optional[Dict[str, str]]:
        best: Optional[Dict[str, str]] = None
        try:
            with open("/proc/mounts", encoding="utf-8") as f:
                for line in f:
                    device, mountpoint, fstype, options, *_ = line.split()
                    if target == mountpoint or target.startswith(mountpoint.rstrip("/") + "/"):
                        if not best or len(mountpoint) > len(best["mountpoint"]):
                            best = {
                                "device": device,
                                "mountpoint": mountpoint,
                                "fstype": fstype,
                                "options": options,
                            }
        except Exception as exc:
            return {"error": str(exc)}
        return best

    def _read_text(self, path: Any) -> Optional[str]:
        try:
            return Path(path).read_text(encoding="utf-8").strip()
        except Exception:
            return None

    def _parse_scheduler(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        for part in value.split():
            if part.startswith("[") and part.endswith("]"):
                return part.strip("[]")
        return value.split()[0] if value.split() else None
