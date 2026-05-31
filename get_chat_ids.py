import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty

load_dotenv()

async def main():
    client = TelegramClient(
        "job_agent_session",
        int(os.getenv("TELEGRAM_API_ID")),
        os.getenv("TELEGRAM_API_HASH")
    )

    await client.start(phone=os.getenv("TELEGRAM_PHONE"))

    print("\n📋 All your Telegram chats:\n")
    async for dialog in client.iter_dialogs(limit=50):  # ← limit to 50
        print(f"Name : {dialog.name}")
        print(f"ID   : {dialog.id}")
        print("-" * 40)

    await client.disconnect()

asyncio.run(main())