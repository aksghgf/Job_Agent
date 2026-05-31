from telethon.sessions import StringSession
from telethon import TelegramClient
import asyncio, os
from dotenv import load_dotenv

load_dotenv()

async def main():
    client = TelegramClient(
        StringSession(),
        int(os.getenv("TELEGRAM_API_ID")),
        os.getenv("TELEGRAM_API_HASH")
    )
    await client.start(phone=os.getenv("TELEGRAM_PHONE"))
    print("\n✅ SESSION STRING (copy this):")
    print(client.session.save())
    await client.disconnect()

asyncio.run(main())