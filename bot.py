# bot.py
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Важно: импортируем наш новый модуль и вызываем инициализацию
from utils import database

from config_loader import BOT_TOKEN, OWNER_ID, PAYMENT
from handlers import user_handlers, admin_handlers, management_handlers
from middlewares.block_middleware import BlockMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    # --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
    database.init_db()
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.update.outer_middleware(BlockMiddleware())

    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    dp.include_router(management_handlers.router)

    if not PAYMENT.get("sbp_phone") and not PAYMENT.get("card_number"):
        try:
            await bot.send_message(
                OWNER_ID,
                "⚠️ **Внимание:** Реквизиты для оплаты не настроены.",
                parse_mode="Markdown",
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить предупреждение владельцу: {e}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")