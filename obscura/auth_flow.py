"""
CloudDrive Hub — Obscura 自动化登录流程
处理 OAuth、Cookie 刷新、验证码、反爬绕过
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("clouddrive.obscura.auth")

SESSION_DIR = "/etc/clouddrive/sessions"


class AuthFlow:
    """自动化登录流程 — 通过 Obscura 反检测浏览器处理"""

    def __init__(self, obscura_url: str = "http://localhost:9000"):
        self.obscura_url = obscura_url
        Path(SESSION_DIR).mkdir(parents=True, exist_ok=True)

    async def login_oauth(self, provider: str, auth_url: str,
                          callback_pattern: str) -> Optional[dict]:
        """通过 Obscura 自动化 OAuth 登录"""
        import aiohttp
        payload = {
            "url": auth_url,
            "wait_for": callback_pattern,
            "timeout": 120,
            "headless": False,
            "stealth": True,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.obscura_url}/api/browser/navigate",
                    json=payload, timeout=130
                ) as resp:
                    data = await resp.json()
                    if data.get("success"):
                        cookies = data.get("cookies", {})
                        self._save_session(provider, cookies)
                        logger.info(f"✅ {provider} OAuth 登录成功")
                        return cookies
                    logger.error(f"❌ {provider} 登录失败: {data.get('error')}")
                    return None
        except Exception as e:
            logger.error(f"❌ {provider} 登录异常: {e}")
            return None

    async def refresh_cookies(self, provider: str) -> bool:
        """刷新 Cookie 会话"""
        session = self._load_session(provider)
        if not session:
            return False
        import aiohttp
        payload = {
            "url": session.get("refresh_url", session.get("home_url")),
            "cookies": session.get("cookies", {}),
            "stealth": True,
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.obscura_url}/api/browser/refresh",
                    json=payload, timeout=60
                ) as resp:
                    data = await resp.json()
                    if data.get("success"):
                        new_cookies = data.get("cookies", {})
                        session["cookies"] = new_cookies
                        session["last_refresh"] = time.time()
                        self._save_session(provider, session)
                        logger.info(f"✅ {provider} Cookie 刷新成功")
                        return True
                    return False
        except Exception as e:
            logger.error(f"❌ {provider} Cookie 刷新失败: {e}")
            return False

    async def solve_captcha(self, image_url: str) -> Optional[str]:
        """通过 Obscura 处理验证码"""
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.obscura_url}/api/captcha/solve",
                    json={"image_url": image_url, "engine": "auto"},
                    timeout=30
                ) as resp:
                    data = await resp.json()
                    return data.get("code") if data.get("success") else None
        except Exception as e:
            logger.error(f"验证码识别失败: {e}")
            return None

    def _save_session(self, provider: str, data: dict):
        path = Path(SESSION_DIR) / f"{provider}.json"
        path.write_text(json.dumps(data, indent=2))

    def _load_session(self, provider: str) -> Optional[dict]:
        path = Path(SESSION_DIR) / f"{provider}.json"
        if path.exists():
            return json.loads(path.read_text())
        return None
