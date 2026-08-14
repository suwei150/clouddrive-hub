#!/usr/bin/env python3
"""
CloudDrive Hub — Operit Agent 主入口
AI 调度中枢：文件管理、同步策略、缓存管理、事件响应
"""

import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# 配置
CONFIG_PATH = "/etc/clouddrive/agent.yaml"
LOG_DIR = "/var/log/clouddrive"
MOUNT_BASE = "/mnt/cloud"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(f"{LOG_DIR}/agent.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("clouddrive.agent")


class CloudDriveAgent:
    """Operit Agent — AI 调度中枢"""

    def __init__(self, config_path: str = CONFIG_PATH):
        self.config = self._load_config(config_path)
        self.running = False
        self.workflows = {}
        self.handlers = {}
        self._init_handlers()

    def _load_config(self, path: str) -> dict:
        default = {
            "mount_base": MOUNT_BASE,
            "cache_dir": "/tmp/clouddrive/cache",
            "sync_interval": 300,
            "cleanup_interval": 3600,
            "max_cache_size": "10G",
            "providers": [],
            "workflows": [],
            "tailscale": {"enable": True, "serve_dir": MOUNT_BASE},
            "obscura": {"enable": True, "auth_refresh_interval": 3600},
        }
        if os.path.exists(path):
            with open(path) as f:
                return {**default, **yaml.safe_load(f)}
        return default

    def _init_handlers(self):
        """注册事件处理器"""
        from handlers.file_event import FileEventHandler
        from handlers.sync_event import SyncEventHandler
        from handlers.cleanup_event import CleanupEventHandler
        self.handlers = {
            "file_change": FileEventHandler(self),
            "sync": SyncEventHandler(self),
            "cleanup": CleanupEventHandler(self),
        }

    async def start(self):
        """启动 Agent"""
        self.running = True
        logger.info("=" * 50)
        logger.info("CloudDrive Hub Agent 启动中...")
        logger.info(f"挂载目录: {self.config['mount_base']}")
        logger.info(f"网盘数量: {len(self.config['providers'])}")
        logger.info(f"工作流数量: {len(self.config['workflows'])}")
        logger.info("=" * 50)

        # 启动各组件
        tasks = [
            self._monitor_mounts(),
            self._sync_loop(),
            self._cleanup_loop(),
            self._health_report_loop(),
            self._watch_workflows(),
        ]

        # 注册信号处理
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(sig, self.stop)

        await asyncio.gather(*tasks)

    def stop(self):
        """停止 Agent"""
        logger.info("Agent 正在停止...")
        self.running = False

    async def _monitor_mounts(self):
        """监控挂载点状态"""
        while self.running:
            for provider in self.config["providers"]:
                mount_point = Path(self.config["mount_base"]) / provider["name"]
                if not mount_point.is_mount():
                    logger.warning(f"⚠️ {provider['name']} 挂载点丢失，尝试重新挂载")
                    await self._remount(provider)
            await asyncio.sleep(30)

    async def _sync_loop(self):
        """同步循环 — 按配置间隔执行同步策略"""
        while self.running:
            for workflow in self.config["workflows"]:
                if workflow.get("type") == "sync":
                    await self.handlers["sync"].execute(workflow)
            await asyncio.sleep(self.config["sync_interval"])

    async def _cleanup_loop(self):
        """清理循环 — 管理缓存和过期文件"""
        while self.running:
            await self.handlers["cleanup"].execute()
            await asyncio.sleep(self.config["cleanup_interval"])

    async def _health_report_loop(self):
        """健康报告循环"""
        while self.running:
            self._print_health_report()
            await asyncio.sleep(600)

    async def _watch_workflows(self):
        """监听 Workflow 触发事件"""
        while self.running:
            # 检查 Operit Workflow 心跳
            await asyncio.sleep(60)

    async def _remount(self, provider: dict):
        """重新挂载指定网盘"""
        name = provider["name"]
        mount_point = Path(self.config["mount_base"]) / name
        mount_point.mkdir(parents=True, exist_ok=True)

        cmd = [
            "rclone", "mount",
            f"{name}:", str(mount_point),
            "--daemon",
            "--vfs-cache-mode", "writes",
            "--cache-dir", f"{self.config['cache_dir']}/{name}",
            "--allow-other",
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        if mount_point.is_mount():
            logger.info(f"✅ {name} 重新挂载成功")
        else:
            logger.error(f"❌ {name} 重新挂载失败")

    def _print_health_report(self):
        """输出健康报告"""
        mounts = []
        for p in Path(self.config["mount_base"]).iterdir():
            if p.is_dir():
                try:
                    usage = os.statvfs(str(p))
                    free_gb = usage.f_bavail * usage.f_frsize / (1024**3)
                    mounts.append(f"  📁 {p.name}: {free_gb:.1f}G 可用")
                except:
                    mounts.append(f"  📁 {p.name}: 状态未知")

        report = f"""
{'='*50}
📊 CloudDrive Hub 健康报告
   时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
   PID: {os.getpid()}
   挂载点:
{chr(10).join(mounts)}
{'='*50}"""
        logger.info(report)

    async def process_natural_language(self, command: str) -> str:
        """接收自然语言命令，调度对应操作"""
        command = command.lower()
        if "同步" in command or "sync" in command:
            target = command.replace("同步", "").replace("sync", "").strip()
            for wf in self.config["workflows"]:
                if wf.get("type") == "sync" and (not target or target in wf.get("name", "")):
                    await self.handlers["sync"].execute(wf)
                    return f"✅ 已触发同步: {wf.get('name', '默认')}"
            return "❌ 未找到匹配的同步工作流"

        if "清理" in command or "cleanup" in command:
            await self.handlers["cleanup"].execute()
            return "✅ 已触发清理"

        if "状态" in command or "status" in command or "health" in command:
            self._print_health_report()
            return "✅ 已输出健康报告，请查看日志"

        return f"❌ 无法理解命令: {command}"


async def main():
    agent = CloudDriveAgent()
    await agent.start()


if __name__ == "__main__":
    asyncio.run(main())
