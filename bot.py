# bot.py
import asyncio
import logging
import os
import sys

# --- НАЧАЛО ПРОВЕРКИ ОКРУЖЕНИЯ ---

def check_unsupported_environment():
    """
    Проверяет, запущен ли скрипт в окружении, где Docker недоступен
    (например, Termux, proot-дистрибутивы, UserLAnd).
    Если обнаружена неподдерживаемая среда, выводит ошибку и завершает работу.
    """
    is_unsupported = False
    error_message = ""

    # 1. Проверка на Termux по переменной окружения и стандартной директории
    if os.environ.get('TERMUX_VERSION') or os.path.isdir('/data/data/com.termux'):
        is_unsupported = True
        error_message = "Обнаружен Termux. Этот скрипт не может работать в Termux, так как Docker здесь недоступен."

    # 2. Общая проверка на proot (используется в UserLAnd и других эмуляторах)
    # Переменная LD_PRELOAD часто используется для работы proot.
    if 'proot' in os.environ.get('LD_PRELOAD', ''):
        is_unsupported = True
        error_message = "Обнаружена среда на базе proot (например, UserLAnd). Docker в таких средах не поддерживается."

    # 3. Общая проверка на Android по наличию системного файла
    if os.path.exists('/system/bin/app_process'):
        is_unsupported = True
        error_message = "Обнаружена среда Android. Запуск хостинга на стандартных Android-устройствах невозможен."

    if is_unsupported:
        # Используем sys.stderr для вывода ошибок
        print("="*60, file=sys.stderr)
        print("!!! КРИТИЧЕСКАЯ ОШИБКА ЗАПУСКА !!!", file=sys.stderr)
        print("\n" + error_message, file=sys.stderr)
        print("\nДля работы этого бота требуется полноценная Linux-система", file=sys.stderr)
        print("с установленным и запущенным Docker.", file=sys.stderr)
        print("Пожалуйста, используйте VPS, VDS или выделенный сервер.", file=sys.stderr)
        print("="*60, file=sys.stderr)
        sys.exit(1) # Завершение работы с кодом ошибки

# --- КОНЕЦ ПРОВЕРКИ ОКРУЖЕНИЯ ---


from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

# Важно: импортируем наш новый модуль и вызываем инициализацию
from utils import database

from config_loader import BOT_TOKEN, OWNER_ID, PAYMENT
from handlers import user_handlers, admin_handlers, management_handlers
from middlewares.block_middleware import BlockMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    # --- Вызываем проверку перед запуском основной логики ---
    check_unsupported_environment()
    
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