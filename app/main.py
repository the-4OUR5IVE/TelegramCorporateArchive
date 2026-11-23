import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

load_dotenv() 

from app.admin.handlers import router as admin_router
from app.collector.handlers import router as collector_router
from app.db.db import init_db

logging.basicConfig(level=logging.INFO)


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN не задан в .env")

    init_db()

    bot = Bot(token=token)
    dp = Dispatcher()
    dp.include_router(collector_router)
    dp.include_router(admin_router)

    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())