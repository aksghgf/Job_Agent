"""
Telegram Reader - Uses Telethon to read your group messages
Get API credentials from: https://my.telegram.org/apps
"""

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.sessions import StringSession
load_dotenv()

log = logging.getLogger("TelegramReader")

IS_CI = os.getenv("CI", "false").lower() == "true"


class TelegramReader:
    def __init__(self, config: dict):
        self.api_id   = os.getenv("TELEGRAM_API_ID")
        self.api_hash = os.getenv("TELEGRAM_API_HASH")
        self.phone    = os.getenv("TELEGRAM_PHONE")
        self.groups   = config["group_usernames"]
        self.queue    = asyncio.Queue()

        if IS_CI:
            # Use string session in CI
            session = StringSession(os.getenv("TELEGRAM_SESSION"))
        else:
            # Use file session locally
            session = "job_agent_session"

        self.client = TelegramClient(
            session,
            int(self.api_id),
            self.api_hash
        )

    async def connect(self):
        """Connect and authenticate with Telegram"""
        if IS_CI:
            # In CI — StringSession from TELEGRAM_SESSION secret, no phone prompt
            await self.client.connect()
        else:
            await self.client.start(phone=self.phone)

        me = await self.client.get_me()
        log.info(f"Logged in as: {me.first_name} (@{me.username})")

        # ── Force cache all groups so private/paid ones work ──
        log.info("Caching all group entities...")
        async for dialog in self.client.iter_dialogs():
            if dialog.id in self.groups:
                log.info(f"✅ Cached: {dialog.name}")

        # ── Register live listener (only in local mode) ───────
        if not IS_CI:
            @self.client.on(events.NewMessage(chats=self.groups))
            async def handler(event: events.NewMessage.Event):
                if event.message.text:
                    await self.queue.put({
                        "chat": str(event.chat_id),
                        "text": event.message.text,
                        "message_id": event.message.id,
                        "date": str(event.message.date)
                    })

    async def notify(self, message: str):
        """Send notification to your own Saved Messages"""
        try:
            await self.client.send_message("me", message)
        except Exception as e:
            log.warning(f"Notification failed: {e}")

    async def listen_groups(self):
        """
        Local mode:
        Phase 1 — today's messages (catch-up)
        Phase 2 — live new messages
        """
        today = datetime.now(timezone.utc).date()

        # ── Phase 1: today's messages only ──────────────────────
        for group in self.groups:
            try:
                log.info(f"Scanning today's messages in: {group}")
                async for msg in self.client.iter_messages(group, limit=200):
                    if not msg.text:
                        continue
                    msg_date = msg.date.replace(tzinfo=timezone.utc)
                    if msg_date.date() < today:
                        break
                    yield {
                        "chat": group,
                        "text": msg.text,
                        "message_id": msg.id,
                        "date": str(msg.date)
                    }
            except Exception as e:
                log.warning(f"Could not read group '{group}': {e}")

        # ── Phase 2: live new messages ───────────────────────────
        log.info("✅ Catch-up done. Listening for new messages live...")

        while True:
            try:
                if not self.client.is_connected():
                    log.info("Reconnecting to Telegram...")
                    await self.client.connect()
                message = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                yield message
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                log.warning(f"Connection issue: {e}, reconnecting in 5s...")
                await asyncio.sleep(5)
                continue

    async def listen_groups_once(self, hours_back: int = 1):
        """
        CI/Scheduled mode — reads messages from last N hours then exits
        No live loop, just one scan and done
        """
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)

        for group in self.groups:
            try:
                log.info(f"CI scan: last {hours_back}h messages in {group}")
                async for msg in self.client.iter_messages(group, limit=100):
                    if not msg.text:
                        continue
                    msg_date = msg.date.replace(tzinfo=timezone.utc)
                    if msg_date < cutoff:
                        break
                    yield {
                        "chat": group,
                        "text": msg.text,
                        "message_id": msg.id,
                        "date": str(msg.date)
                    }
            except Exception as e:
                log.warning(f"Could not read group '{group}': {e}")

    async def disconnect(self):
        await self.client.disconnect()