# utils/message_utils.py
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.exceptions import TelegramBadRequest
from config_loader import BANNER_LOCAL_PATH
import contextlib
import pathlib
import logging

async def send_or_edit_message_with_banner(
    event: Message | CallbackQuery,
    text: str,
    reply_markup=None,
    parse_mode: str = "HTML"
):
    """
    Отправляет или редактирует сообщение, всегда добавляя к нему баннер из локального файла.
    Использует абсолютный путь к файлу для надежности.
    """
    base_path = pathlib.Path(__file__).parent.parent
    absolute_banner_path = base_path / BANNER_LOCAL_PATH

    # Проверяем, существует ли файл. Если нет - отправляем текстовое сообщение.
    if not absolute_banner_path.is_file():
        logging.error(f"CRITICAL: Banner file not found at path: {absolute_banner_path}")
        if isinstance(event, Message):
            await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        elif isinstance(event, CallbackQuery):
            await event.answer()
            await event.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return

    banner_file = FSInputFile(absolute_banner_path)

    if isinstance(event, Message):
        try:
            await event.answer_photo(
                photo=banner_file,
                caption=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
        except Exception as e:
            logging.error(f"Failed to send photo: {e}")
            await event.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

    elif isinstance(event, CallbackQuery):
        await event.answer()
        
        try:
            await event.message.edit_media(
                media=InputMediaPhoto(
                    media=banner_file,
                    caption=text,
                    parse_mode=parse_mode
                ),
                reply_markup=reply_markup
            )
            return
        except TelegramBadRequest as e:
            logging.info(f"Couldn't edit media, falling back to sending new message. Reason: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during edit_media: {e}")

        with contextlib.suppress(TelegramBadRequest):
            await event.message.delete()
        
        await event.message.answer_photo(
            photo=banner_file,
            caption=text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )