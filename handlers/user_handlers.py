# handlers/user_handlers.py
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import random
import html
import asyncio
import contextlib

from keyboards import inline
from config_loader import PAYMENT, SERVERS, OWNER_ID
from utils import database as db
from services.docker_manager import create_container
from states import Replenishment
from utils.texts import texts # <-- НОВЫЙ ИМПОРТ

router = Router()

async def delete_message_after_delay(message: Message, delay: int):
    await asyncio.sleep(delay)
    with contextlib.suppress(Exception):
        await message.delete()

@router.message(F.text == "/start")
async def start_handler(message: Message):
    user = db.get_or_create_user(message.from_user.id)
    await message.answer(
        texts.get("main_menu.welcome"),
        reply_markup=inline.main_menu_keyboard(user_role=user.get('role'))
    )

@router.callback_query(F.data == "start")
async def start_callback_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    user = db.get_or_create_user(query.from_user.id)
    await query.message.edit_text(
        texts.get("main_menu.welcome"),
        reply_markup=inline.main_menu_keyboard(user_role=user.get('role'))
    )
    await query.answer()

@router.callback_query(F.data == "buy_hosting")
async def buy_hosting_handler(query: CallbackQuery):
    tariffs = db.get_tariffs()
    await query.message.edit_text(texts.get("purchase.select_tariff"), reply_markup=inline.tariffs_keyboard(tariffs))
    await query.answer()

@router.callback_query(F.data.startswith("buy_tariff_"))
async def buy_tariff_handler(query: CallbackQuery):
    tariff_id = int(query.data.split("_")[2])
    tariff = db.get_tariff_by_id(tariff_id)
    if not tariff:
        await query.answer(texts.get("purchase.tariff_not_found"), show_alert=True)
        return
    user_id = query.from_user.id
    user = db.get_or_create_user(user_id)
    if user['balance'] < tariff["price"]:
        await query.answer(texts.get("purchase.insufficient_funds"), show_alert=True)
        return
    db.update_user_balance(user_id, -tariff["price"])
    server = random.choice(SERVERS)
    await query.message.edit_text(texts.get("purchase.creating_container"))
    new_container_info = await create_container(user_id, server, tariff)
    if new_container_info:
        db.add_container(user_id, new_container_info)
        await query.message.edit_text(
            texts.get("purchase.creation_success", server_ip=new_container_info['server_ip'], port=new_container_info['port']),
            reply_markup=inline.main_menu_keyboard(user_role=user.get('role'))
        )
    else:
        db.update_user_balance(user_id, tariff["price"])
        await query.message.edit_text(texts.get("purchase.creation_error"))
    await query.answer()

@router.callback_query(F.data == "my_account")
async def my_account_handler(query: CallbackQuery):
    user_id = query.from_user.id
    user = db.get_or_create_user(user_id)
    text = texts.get("account.title", user_id=user_id, balance=user['balance'])
    await query.message.edit_text(text, parse_mode="HTML", reply_markup=inline.my_account_keyboard())
    await query.answer()

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment_handler(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await my_account_handler(query)

@router.callback_query(F.data == "top_up_balance")
async def top_up_balance_start(query: CallbackQuery, state: FSMContext):
    await state.set_state(Replenishment.awaiting_amount)
    sent_message = await query.message.edit_text(
        texts.get("account.top_up_prompt"),
        reply_markup=inline.cancel_keyboard()
    )
    await state.update_data(prompt_message_id=sent_message.message_id)
    await query.answer()

@router.message(Replenishment.awaiting_amount)
async def top_up_amount_received(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer(texts.get("account.invalid_amount"))
        return
    data = await state.get_data()
    prompt_message_id = data.get("prompt_message_id")
    await message.delete()
    if prompt_message_id:
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
    await state.update_data(amount=amount)
    await state.set_state(Replenishment.awaiting_confirmation)
    text = texts.get("account.top_up_instruction", amount=amount, sbp_phone=PAYMENT['sbp_phone'])
    await message.answer(text, parse_mode="HTML", reply_markup=inline.payment_confirmation_keyboard())

@router.callback_query(F.data == "payment_confirmed", Replenishment.awaiting_confirmation)
async def payment_confirmed_handler(query: CallbackQuery, state: FSMContext):
    await state.set_state(Replenishment.awaiting_screenshot)
    await state.update_data(screenshot_prompt_id=query.message.message_id)
    await query.message.edit_text(texts.get("account.awaiting_screenshot"), reply_markup=inline.cancel_keyboard())
    await query.answer()

@router.message(F.photo, Replenishment.awaiting_screenshot)
async def screenshot_received_handler(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    amount = data.get("amount")
    user = message.from_user
    full_name = html.escape(user.full_name)
    username = f"@{html.escape(user.username)}" if user.username else "Нет"
    admin_caption = (f"<b>❗️ Новая заявка на пополнение!</b>\n\n"
                     f"<b>Пользователь:</b> {full_name} ({username})\n"
                     f"<b>ID:</b> <code>{user.id}</code>\n"
                     f"<b>Сумма:</b> <code>{amount}</code> руб.")
    await bot.send_photo(
        chat_id=OWNER_ID, photo=message.photo[-1].file_id,
        caption=admin_caption, parse_mode="HTML",
        reply_markup=inline.admin_approval_keyboard(user.id, amount)
    )
    await message.delete()
    screenshot_prompt_id = data.get("screenshot_prompt_id")
    if screenshot_prompt_id:
        with contextlib.suppress(Exception):
            await bot.delete_message(chat_id=message.chat.id, message_id=screenshot_prompt_id)
    sent_message = await bot.send_message(
        chat_id=user.id, text=texts.get("account.request_sent")
    )
    asyncio.create_task(delete_message_after_delay(sent_message, 60))
    await state.clear()

@router.callback_query(F.data == "my_userbots")
async def my_userbots_handler(query: CallbackQuery):
    user_id = query.from_user.id
    containers = db.get_user_containers(user_id)
    if not containers:
        await query.message.edit_text(
            texts.get("main_menu.my_userbots_empty"), parse_mode="HTML",
            reply_markup=inline.empty_userbots_keyboard()
        )
    else:
        await query.message.edit_text(
            texts.get("main_menu.my_userbots_title"), parse_mode="HTML",
            reply_markup=inline.my_userbots_keyboard(containers)
        )
    await query.answer()

@router.callback_query(F.data == "empty_userbots_warning")
async def empty_userbots_warning_handler(query: CallbackQuery):
    await query.answer(texts.get("main_menu.empty_userbots_alert"), show_alert=True)