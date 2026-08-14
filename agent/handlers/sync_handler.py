"""
CloudDrive Hub — 同步事件处理器
支持增量同步、双向同步、定时同步、事件触发
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("clouddrive.agent.sync")


class SyncHandler:
    """同步处理器 — 对接 rclone 同步引擎"""

    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.running = {}

    async def execute(self, workflow: dict) -> dict:
        name = workflow.get("name", "sync")
        if name in self.running and self.running[name]:
            return {"status": "skipped", "reason": "already running"}

        self.running[name] = True
        try:
            source = workflow["source"]
            target = workflow["target"]
            sync_type = workflow.get("sync_type", "oneway")
            filters = workflow.get("filters", {})

            logger.info(f"🔄 同步: {name} ({source} → {target})")

            rclone_type = {"oneway": "copy", "bidirectional": "bisync",
                          "clone": "sync"}.get(sync_type, "copy")

            ok = await self.orchestrator.run_rclone_sync(
                source, target, rclone_type, filters)

            return {"status": "ok" if ok else "fail", "workflow": name}
        except Exception as e:
            logger.error(f"同步失败 {name}: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self.running[name] = False
