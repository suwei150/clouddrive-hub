"""
CloudDrive Hub — 同步事件处理器
智能调度引擎：支持增量同步、双向同步、定时同步
"""

import asyncio
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("clouddrive.agent.sync")


class SyncEventHandler:
    """同步事件处理器"""

    def __init__(self, agent):
        self.agent = agent
        self.running_syncs = {}

    async def execute(self, workflow: dict):
        """执行同步工作流"""
        name = workflow.get("name", "unnamed")
        source = workflow.get("source", "")
        target = workflow.get("target", "")
        sync_type = workflow.get("sync_type", "oneway")  # oneway / bidirectional
        filters = workflow.get("filters", {})
        schedule = workflow.get("schedule", {})

        # 检查是否正在运行
        if name in self.running_syncs and self.running_syncs[name]:
            logger.debug(f"⏭️ {name} 同步已在运行，跳过")
            return

        # 检查调度时间
        if schedule.get("type") == "interval":
            # 由主循环控制间隔
            pass

        logger.info(f"🔄 开始同步: {name} ({source} → {target})")
        self.running_syncs[name] = True

        try:
            if sync_type == "oneway":
                await self._sync_oneway(name, source, target, filters)
            elif sync_type == "bidirectional":
                await self._sync_bidirectional(name, source, target, filters)
            elif sync_type == "clone":
                await self._sync_clone(name, source, target, filters)
            else:
                logger.warning(f"❌ 未知同步类型: {sync_type}")
        except Exception as e:
            logger.error(f"❌ 同步 {name} 失败: {e}")
        finally:
            self.running_syncs[name] = False
            logger.info(f"✅ 同步完成: {name}")

    async def _sync_oneway(self, name: str, source: str, target: str, filters: dict):
        """单向同步 — rclone copy"""
        cmd = self._build_rclone_cmd("copy", source, target, filters)
        await self._run_rclone(name, cmd)

    async def _sync_bidirectional(self, name: str, source: str, target: str, filters: dict):
        """双向同步 — rclone bisync"""
        cmd = self._build_rclone_cmd("bisync", source, target, filters)
        cmd.extend(["--resync"])
        await self._run_rclone(name, cmd)

    async def _sync_clone(self, name: str, source: str, target: str, filters: dict):
        """完整克隆 — rclone sync"""
        cmd = self._build_rclone_cmd("sync", source, target, filters)
        await self._run_rclone(name, cmd)

    def _build_rclone_cmd(self, operation: str, source: str, target: str, filters: dict) -> list:
        """构建 rclone 命令"""
        cmd = ["rclone", operation, source, target,
               "--progress",
               "--verbose",
               "--stats", "30s",
               "--transfers", "4",
               "--checkers", "8",
               "--retries", "3",
               "--low-level-retries", "3",
               "--timeout", "60s",
               "--contimeout", "30s"]

        # 文件过滤器
        if filters.get("include"):
            for pattern in filters["include"]:
                cmd.extend(["--include", pattern])
        if filters.get("exclude"):
            for pattern in filters["exclude"]:
                cmd.extend(["--exclude", pattern])
        if filters.get("max_size"):
            cmd.extend(["--max-size", filters["max_size"]])
        if filters.get("min_size"):
            cmd.extend(["--min-size", filters["min_size"]])
        if filters.get("max_age"):
            cmd.extend(["--max-age", filters["max_age"]])
        if filters.get("min_age"):
            cmd.extend(["--min-age", filters["min_age"]])

        # 带宽限制
        bw = filters.get("bwlimit")
        if bw:
            cmd.extend(["--bwlimit", bw])

        # 删除目标多余文件
        if filters.get("delete_excess", True):
            if operation in ("copy", "sync"):
                cmd.append("--delete-excluded")

        return cmd

    async def _run_rclone(self, name: str, cmd: list):
        """执行 rclone 命令并记录日志"""
        log_file = f"/var/log/clouddrive/sync_{name}.log"
        cmd_str = " ".join(cmd)
        logger.debug(f"运行: {cmd_str}")

        with open(log_file, "a") as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(f"CMD: {cmd_str}\n")

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        async for line in proc.stdout:
            line = line.decode().strip()
            if line:
                with open(log_file, "a") as f:
                    f.write(f"{line}\n")

        await proc.wait()
        if proc.returncode != 0:
            logger.warning(f"⚠️ {name} 返回码: {proc.returncode}")
