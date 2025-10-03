# middlewares/block_middleware.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from utils import database as db
from utils.texts import texts # <-- НОВЫЙ ИМПОРТ

class BlockMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, (Message, CallbackQuery)):
            return await handler(event, data)

        user_id = event.from_user.id
        user_data = db.get_or_create_user(user_id)

        # Администраторы не могут быть заблокированы
        if user_data.get("role") == "admin":
            return await handler(event, data)
        
        # Проверяем, заблокирован ли обычный пользователь
        if user_data.get("is_blocked", False):
            if isinstance(event, CallbackQuery):
                # ИСПОЛЬЗУЕМ ТЕКСТ ИЗ texts.json
                await event.answer(texts.get("errors.access_denied"), show_alert=True)
            return # Прерываем обработку

        # Если пользователь не заблокирован, продолжаем
        return await handler(event, data)