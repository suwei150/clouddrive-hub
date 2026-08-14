"""
CloudDrive Hub — 缓存清理处理器
LRU 自动清理 + 磁盘空间预警
"""

import asyncio
import logging
import shutil
from pathlib import Path

logger = logging.getLogger("clouddrive.agent.cleanup")


class CleanupHandler:
    """缓存清理处理器"""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator

    async def execute(self, workflow: dict = None) -> dict:
        logger.info("🧹 开始缓存清理...")
        results = []

        cache_dirs = [
            Path("/tmp/clouddrive/cache"),
            Path("/root/.cache/rclone"),
            Path("/var/log/clouddrive"),
        ]

        max_cache = workflow.get("max_cache_size", "10G") if workflow else "10G"
        max_bytes = self._parse_size(max_cache)
        days_old = workflow.get("older_than", 7) if workflow else 7

        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            size = self._dir_size(cache_dir)
            if size > max_bytes:
                logger.info(f"  {cache_dir}: {self._fmt_size(size)} > 阈值 {max_cache}")
                for f in cache_dir.rglob("*"):
                    if f.is_file() and self._days_old(f) > days_old:
                        f.unlink()
                        results.append(str(f))
                new_size = self._dir_size(cache_dir)
                logger.info(f"  清理后: {self._fmt_size(new_size)}")
            else:
                logger.debug(f"  {cache_dir}: {self._fmt_size(size)} (正常)")

        return {"status": "ok", "freed": len(results)}

    def _dir_size(self, path: Path) -> int:
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

    def _fmt_size(self, bytes_: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if bytes_ < 1024:
                return f"{bytes_:.1f}{unit}"
            bytes_ /= 1024
        return f"{bytes_:.1f}TB"

    def _parse_size(self, size: str) -> int:
        size = size.upper().strip()
        units = {"K": 1024, "KB": 1024, "M": 1024**2, "MB": 1024**2,
                 "G": 1024**3, "GB": 1024**3, "T": 1024**4, "TB": 1024**4}
        for unit, multiplier in units.items():
            if size.endswith(unit):
                return int(float(size[:-len(unit)]) * multiplier)
        return int(float(size))

    def _days_old(self, path: Path) -> float:
        import time
        age = time.time() - path.stat().st_mtime
        return age / 86400
