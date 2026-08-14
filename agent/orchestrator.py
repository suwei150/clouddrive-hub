"""
CloudDrive Hub — Agent 工作流编排器
整合 Alist API + rclone 管理 + 独立通道巡检
"""

import asyncio
import json
import logging
import subprocess
from datetime import datetime
from typing import Optional

logger = logging.getLogger("clouddrive.agent.orchestrator")

ALIST_API = "http://localhost:5244/api"
MOUNT_BASE = "/mnt/cloud"


class WorkflowOrchestrator:
    """工作流编排器 — 整合 Alist API + rclone + 独立通道"""

    def __init__(self, agent):
        self.agent = agent
        self.alist_token = None

    async def alist_login(self, user: str = "admin", password: str = "") -> bool:
        """登录 Alist 管理 API"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ALIST_API}/auth/login", json={
                    "username": user, "password": password
                }) as resp:
                    data = await resp.json()
                    if data.get("code") == 200:
                        self.alist_token = data["data"]["token"]
                        logger.info("✅ Alist API 登录成功")
                        return True
                    logger.warning(f"⚠️ Alist 登录失败: {data.get('message')}")
                    return False
        except Exception as e:
            logger.error(f"❌ Alist 连接失败: {e}")
            return False

    async def get_alist_storages(self) -> list:
        """获取 Alist 中所有存储驱动"""
        if not self.alist_token:
            return []
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{ALIST_API}/admin/storage/list",
                    headers={"Authorization": self.alist_token}) as resp:
                    data = await resp.json()
                    return data.get("data", {}).get("content", [])
        except Exception as e:
            logger.error(f"获取存储列表失败: {e}")
            return []

    async def add_alist_storage(self, driver: str, mount_path: str,
                                config: dict) -> bool:
        """向 Alist 添加存储驱动"""
        if not self.alist_token:
            return False
        import aiohttp
        payload = {
            "mount_path": mount_path,
            "driver": driver,
            "remark": f"clouddrive-{driver}",
            "order": 0,
            "disabled": False,
            "addition": json.dumps(config),
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{ALIST_API}/admin/storage/create",
                    headers={"Authorization": self.alist_token},
                    json=payload) as resp:
                    data = await resp.json()
                    if data.get("code") == 200:
                        logger.info(f"✅ 添加存储 {driver} → {mount_path}")
                        return True
                    logger.warning(f"添加存储失败: {data.get('message')}")
                    return False
        except Exception as e:
            logger.error(f"添加存储异常: {e}")
            return False

    async def rclone_mount(self, remote: str, mount_point: str,
                           cache_mode: str = "writes") -> bool:
        """通过 rclone 挂载网盘"""
        cmd = [
            "rclone", "mount",
            f"{remote}:", mount_point,
            "--daemon",
            "--vfs-cache-mode", cache_mode,
            "--allow-other",
            "--dir-cache-time", "5m",
            "--log-file", f"/var/log/clouddrive/mount_{remote}.log",
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()

        # 验证挂载
        import os
        if os.path.ismount(mount_point):
            logger.info(f"✅ 挂载成功: {remote} → {mount_point}")
            return True
        logger.error(f"❌ 挂载失败: {remote}")
        return False

    async def rclone_unmount(self, mount_point: str) -> bool:
        """卸载网盘"""
        cmd = ["fusermount", "-u", mount_point]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        logger.info(f"卸载: {mount_point}")
        return True

    async def run_rclone_sync(self, source: str, target: str,
                              sync_type: str = "copy",
                              filters: dict = None) -> bool:
        """执行 rclone 同步"""
        cmd = ["rclone", sync_type, source, target,
               "--progress", "--verbose", "--stats", "30s",
               "--transfers", "4", "--checkers", "8"]

        if filters:
            for p in filters.get("exclude", []):
                cmd.extend(["--exclude", p])
            for p in filters.get("include", []):
                cmd.extend(["--include", p])
            if filters.get("bwlimit"):
                cmd.extend(["--bwlimit", filters["bwlimit"]])

        log_file = f"/var/log/clouddrive/sync_{datetime.now():%Y%m%d_%H%M%S}.log"
        with open(log_file, "w") as f:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=f, stderr=asyncio.subprocess.STDOUT)
            await proc.wait()

        if proc.returncode == 0:
            logger.info(f"✅ 同步完成: {source} → {target}")
            return True
        logger.error(f"❌ 同步失败 (exit={proc.returncode}): {source} → {target}")
        return False

    async def check_mounts(self) -> list:
        """检查所有挂载点状态"""
        import os
        results = []
        if not os.path.exists(MOUNT_BASE):
            return results
        for item in os.listdir(MOUNT_BASE):
            path = os.path.join(MOUNT_BASE, item)
            try:
                is_mount = os.path.ismount(path)
                st = os.statvfs(path)
                free_gb = st.f_bavail * st.f_frsize / (1024**3)
                results.append({
                    "name": item,
                    "path": path,
                    "mounted": is_mount,
                    "free_gb": round(free_gb, 1),
                })
            except:
                results.append({"name": item, "path": path, "mounted": False})
        return results

    async def patrol_independent_channel(self) -> dict:
        """通过独立 ADB 通道巡检系统状态"""
        result = {}
        adb_shell = "/opt/clouddrive-hub/tools/adb_server_shell"
        import os
        if os.path.exists(adb_shell):
            proc = await asyncio.create_subprocess_exec(
                adb_shell, stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE)
            stdout, _ = await proc.communicate(timeout=10)
            result["adb_channel"] = "ok" if proc.returncode == 0 else "fail"
            result["adb_output"] = stdout.decode()[:500]
        else:
            result["adb_channel"] = "unavailable"
        return result
