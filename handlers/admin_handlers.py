# handlers/admin_handlers.py
from aiogram import Router, F, Bot
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio
import contextlib

from config_loader import SERVERS
from keyboards import inline
from states import AdminStates
from utils import database as db
from services import docker_manager
from utils.texts import texts
from utils.message_utils import send_or_edit_message_with_banner

# --- ФИЛЬТР ДЛЯ ПРОВЕРКИ РОЛИ АДМИНИСТРАТОРА ---
class AdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user = db.get_or_create_user(event.from_user.id)
        return user.get('role') == 'admin'

router = Router()
# Применяем фильтр ко всему роутеру
router.message.filter(AdminFilter())
router.callback_query.filter(AdminFilter())

async def delete_message_after_delay(message: Message, delay: int):
    """Асинхронно ждет delay секунд и удаляет сообщение."""
    await asyncio.sleep(delay)
    with contextlib.suppress(Exception):
        await message.delete()

# --- ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ ---

@router.message(F.text == "/admin")
async def admin_panel_handler(message: Message):
    await send_or_edit_message_with_banner(message, texts.get("admin.welcome"), inline.admin_main_keyboard())

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(query: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_or_edit_message_with_banner(query, texts.get("admin.welcome"), inline.admin_main_keyboard())

# --- УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ---

@router.callback_query(F.data.startswith("admin_users"))
async def admin_show_users(query: CallbackQuery):
    page = int(query.data.split("_")[-1]) if query.data.startswith("admin_users_page") else 0
    all_users = db.get_all_users_info()
    if not all_users:
        await query.answer(texts.get("admin.no_users"), show_alert=True)
        return
    await send_or_edit_message_with_banner(
        event=query,
        text=texts.get("admin.users_list_title", page=page+1),
        reply_markup=inline.admin_users_list_keyboard(all_users, page)
    )

@router.callback_query(F.data.startswith("admin_user_manage_"))
async def admin_manage_user(query: CallbackQuery):
    user_id = int(query.data.split("_")[-1])
    user_data = db.get_or_create_user(user_id)
    text = texts.get("admin.user_manage_title",
                     user_id=user_id, balance=user_data['balance'],
                     is_blocked='Да' if user_data.get('is_blocked') else 'Нет')
    await send_or_edit_message_with_banner(
        event=query,
        text=text,
        reply_markup=inline.admin_user_manage_keyboard(user_id, user_data.get('is_blocked'))
    )

@router.callback_query(F.data.startswith("admin_user_block_"))
async def admin_block_user(query: CallbackQuery):
    user_id = int(query.data.split("_")[-1])
    user_data = db.get_or_create_user(user_id)
    new_status = not user_data.get('is_blocked', False)
    db.set_user_blocked_status(user_id, new_status)
    status_text = 'заблокирован' if new_status else 'разблокирован'
    await query.answer(texts.get("admin.user_block_status_changed", status=status_text), show_alert=True)
    await admin_manage_user(query)

@router.callback_query(F.data.startswith("admin_user_balance_"))
async def admin_change_balance_start(query: CallbackQuery, state: FSMContext):
    user_id = int(query.data.split("_")[-1])
    await state.update_data(target_user_id=user_id)
    await state.set_state(AdminStates.awaiting_balance_amount)
    # Здесь мы редактируем подпись к фото, а не текст
    await query.message.edit_caption(caption=texts.get("admin.enter_new_balance", user_id=user_id))
    await query.answer()
    
@router.message(AdminStates.awaiting_balance_amount)
async def admin_change_balance_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = int(message.text)
    except ValueError:
        await message.answer(texts.get("admin.invalid_number"))
        return
    data = await state.get_data()
    user_id = data.get("target_user_id")
    db.set_user_balance(user_id, amount)
    await state.clear()
    
    # После ввода данных возвращаем меню с баннером
    await send_or_edit_message_with_banner(message, 
        texts.get("admin.balance_changed_success", user_id=user_id, amount=amount),
        inline.back_to_admin_panel())
    
    try:
        await bot.send_message(user_id, texts.get("admin.balance_update_notification", amount=amount))
    except Exception as e:
        print(f"Не удалось уведомить {user_id}: {e}")

# --- УПРАВЛЕНИЕ КОНТЕЙНЕРАМИ ---

@router.callback_query(F.data.startswith("admin_containers"))
async def admin_show_containers(query: CallbackQuery):
    page = int(query.data.split("_")[-1]) if query.data.startswith("admin_containers_page") else 0
    all_containers = db.get_all_containers_info()
    if not all_containers:
        await query.answer(texts.get("admin.no_containers"), show_alert=True)
        return
    await send_or_edit_message_with_banner(
        event=query,
        text=texts.get("admin.containers_list_title", page=page+1),
        reply_markup=inline.admin_containers_list_keyboard(all_containers, page)
    )

@router.callback_query(F.data.startswith("admin_manage_container_"))
async def admin_manage_container(query: CallbackQuery):
    container_db_id = int(query.data.split("_")[-1])
    container = db.get_container_by_db_id(container_db_id)
    if not container:
        await query.answer(texts.get("management.container_not_found"), show_alert=True)
        return
    server = SERVERS[container['server_index']]
    status = await docker_manager.get_container_status(container, server)
    text = texts.get("admin.container_manage_title", container_name=container['name'],
                     user_id=container['user_id'], status=status)
    await send_or_edit_message_with_banner(
        event=query,
        text=text,
        reply_markup=inline.management_keyboard(container, container['id'])
    )

# --- НАСТРОЙКИ БОТА (ТАРИФЫ) ---

@router.callback_query(F.data == "admin_settings")
async def admin_settings(query: CallbackQuery):
    await send_or_edit_message_with_banner(query, texts.get("admin.settings_menu"), inline.admin_settings_keyboard())

@router.callback_query(F.data == "admin_tariffs")
async def admin_manage_tariffs(query: CallbackQuery, state: FSMContext):
    await state.clear()
    tariffs = db.get_tariffs()
    await send_or_edit_message_with_banner(query, texts.get("admin.tariffs_menu"), inline.admin_tariffs_keyboard(tariffs))

@router.callback_query(F.data.startswith("admin_delete_tariff_"))
async def admin_delete_tariff(query: CallbackQuery, state: FSMContext):
    tariff_id = int(query.data.split("_")[-1])
    db.delete_tariff_by_id(tariff_id)
    await query.answer(texts.get("admin.tariff_deleted"), show_alert=True)
    await admin_manage_tariffs(query, state)

@router.callback_query(F.data == "admin_add_tariff")
async def admin_add_tariff_start(query: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.awaiting_tariff_name)
    await query.message.edit_caption(caption=texts.get("admin.enter_tariff_name"))
    await query.answer()

@router.message(AdminStates.awaiting_tariff_name)
async def admin_add_tariff_name(message: Message, state: FSMContext):
    if len(message.text) > 50:
        await message.answer(texts.get("admin.tariff_name_too_long"))
        return
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.awaiting_tariff_price)
    await message.answer(texts.get("admin.enter_tariff_price"))

@router.message(AdminStates.awaiting_tariff_price)
async def admin_add_tariff_price(message: Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            await message.answer(texts.get("admin.price_must_be_positive"))
            return
        await state.update_data(price=price)
        await state.set_state(AdminStates.awaiting_tariff_cpu)
        await message.answer(texts.get("admin.enter_tariff_cpu"))
    except ValueError:
        await message.answer(texts.get("admin.invalid_price_format"))

@router.message(AdminStates.awaiting_tariff_cpu)
async def admin_add_tariff_cpu(message: Message, state: FSMContext):
    try:
        cpu_limit = float(message.text.replace(',', '.'))
        if cpu_limit <= 0.0:
            await message.answer(texts.get("admin.cpu_must_be_positive"))
            return
        await state.update_data(cpu_limit=str(cpu_limit))
        await state.set_state(AdminStates.awaiting_tariff_memory)
        await message.answer(texts.get("admin.enter_tariff_ram"))
    except ValueError:
        await message.answer(texts.get("admin.invalid_cpu_format"))

@router.message(AdminStates.awaiting_tariff_memory)
async def admin_add_tariff_memory(message: Message, state: FSMContext):
    memory_limit = message.text.lower()
    if not (memory_limit.endswith('m') or memory_limit.endswith('g')):
        await message.answer(texts.get("admin.invalid_ram_format"), parse_mode="Markdown")
        return
    try:
        value = int(memory_limit[:-1])
        if value <= 0:
            await message.answer(texts.get("admin.ram_must_be_positive"))
            return
    except ValueError:
        await message.answer(texts.get("admin.invalid_ram_value"))
        return
    await state.update_data(memory_limit=memory_limit)
    data = await state.get_data()
    db.add_tariff(data)
    await state.clear()
    await send_or_edit_message_with_banner(
        event=message,
        text=texts.get("admin.tariff_added_success", name=data['name']),
        reply_markup=inline.back_to_admin_panel()
    )

# --- ОБРАБОТЧИКИ ПОДТВЕРЖДЕНИЯ ОПЛАТЫ (Остаются без изменений) ---

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment_handler(query: CallbackQuery, bot: Bot):
    _, user_id_str, amount_str = query.data.split("_")
    user_id, amount = int(user_id_str), int(amount_str)
    db.get_or_create_user(user_id)
    db.update_user_balance(user_id, amount)
    new_balance = db.get_or_create_user(user_id)['balance']
    await bot.send_message(user_id, texts.get("admin.payment_approved_notification",
                                               amount=amount, new_balance=new_balance))
    await query.message.edit_caption(caption=query.message.caption + texts.get("admin.payment_approved_log"), reply_markup=None)
    await query.answer(texts.get("admin.payment_approved_log").strip())

@router.callback_query(F.data.startswith("decline_"))
async def decline_payment_handler(query: CallbackQuery, bot: Bot):
    _, user_id_str, amount_str = query.data.split("_")
    user_id, amount = int(user_id_str), int(amount_str)
    await bot.send_message(user_id, texts.get("admin.payment_declined_notification", amount=amount))
    await query.message.edit_caption(caption=query.message.caption + texts.get("admin.payment_declined_log"), reply_markup=None)
    await query.answer(texts.get("admin.payment_declined_log").strip())