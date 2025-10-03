# keyboards/inline.py
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config_loader import PAYMENT

# --- Клавиатуры пользователя ---

def main_menu_keyboard(user_role: str = 'member'):
    builder = InlineKeyboardBuilder()
    # ИЗМЕНЕНО: Кнопки "Мой кабинет" и "Мои юзерботы" теперь на одной строке
    builder.row(InlineKeyboardButton(text="🛒 Купить хостинг", callback_data="buy_hosting"))
    builder.row(
        InlineKeyboardButton(text="👤 Мой кабинет", callback_data="my_account"),
        InlineKeyboardButton(text="🤖 Мои юзерботы", callback_data="my_userbots")
    )

    if user_role == 'admin':
        builder.row(InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel"))

    return builder.as_markup()

def my_account_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="top_up_balance"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="start"))
    return builder.as_markup()

def payment_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Оплатил", callback_data="payment_confirmed"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")
    )
    return builder.as_markup()

def cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment"))
    return builder.as_markup()

def tariffs_keyboard(tariffs: list):
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        text = (
            f"{tariff['name']} - {tariff['price']} руб. "
            f"(CPU: {tariff['cpu_limit']}, RAM: {tariff['memory_limit']})"
        )
        builder.row(InlineKeyboardButton(text=text, callback_data=f"buy_tariff_{tariff['id']}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="start"))
    return builder.as_markup()

def my_userbots_keyboard(user_containers: list):
    builder = InlineKeyboardBuilder()
    for container in user_containers:
        builder.row(InlineKeyboardButton(
            text=f"⚙️ {container['name']}",
            callback_data=f"manage_container_{container['id']}" 
        ))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="start"))
    return builder.as_markup()
    
def empty_userbots_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Тут как то пустовато...", callback_data="empty_userbots_warning"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="start"))
    return builder.as_markup()

def management_keyboard(container: dict, container_db_id: int):
    builder = InlineKeyboardBuilder()
    
    # ИЗМЕНЕНО: Полностью переработанный дизайн меню управления
    # Главная кнопка действия (Вкл/Выкл) занимает всю ширину
    if container['status'] == 'running':
        builder.row(InlineKeyboardButton(text="🔴 Остановить", callback_data=f"stop_{container_db_id}"))
    else:
        builder.row(InlineKeyboardButton(text="🟢 Запустить", callback_data=f"start_{container_db_id}"))

    # Две "опасные" кнопки в одном ряду
    builder.row(
        InlineKeyboardButton(text="🔄 Переустановить", callback_data=f"reinstall_{container_db_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{container_db_id}")
    )
    # Кнопка входа и кнопка назад
    builder.row(InlineKeyboardButton(text="➡️ Войти в консоль", url=f"http://{container['server_ip']}:{container['port']}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="my_userbots"))
    return builder.as_markup()

def confirm_action_keyboard(action: str, container_db_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, я уверен", callback_data=f"confirm_{action}_{container_db_id}"),
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data=f"manage_container_{container_db_id}")
    )
    return builder.as_markup()

# --- Клавиатуры админ-панели ---

def admin_approval_keyboard(user_id: int, amount: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}_{amount}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_{user_id}_{amount}")
    )
    return builder.as_markup()

def admin_main_keyboard():
    builder = InlineKeyboardBuilder()
    # ИЗМЕНЕНО: Более компактная и логичная группировка
    builder.row(
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users"),
        InlineKeyboardButton(text="🐳 Контейнеры", callback_data="admin_containers")
    )
    builder.row(InlineKeyboardButton(text="⚙️ Настройки бота (Тарифы)", callback_data="admin_settings"))
    builder.row(InlineKeyboardButton(text="⬅️ Выйти из админки", callback_data="start"))
    return builder.as_markup()

def admin_users_list_keyboard(users_info: list, page: int = 0):
    builder = InlineKeyboardBuilder()
    per_page = 5
    start, end = page * per_page, (page + 1) * per_page
    
    for user in users_info[start:end]:
        status = "🔴" if user['is_blocked'] else "🟢"
        builder.row(InlineKeyboardButton(
            text=f"{status} ID: {user['user_id']} | 🐳: {user['container_count']}",
            callback_data=f"admin_user_manage_{user['user_id']}"
        ))
    
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_page_{page-1}"))
    if end < len(users_info):
        pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_page_{page+1}"))
    
    # Кнопки пагинации будут в одном ряду
    if pagination_buttons:
        builder.row(*pagination_buttons)

    builder.row(InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_panel"))
    return builder.as_markup()

def admin_user_manage_keyboard(user_id: int, is_blocked: bool):
    builder = InlineKeyboardBuilder()
    block_text = "✅ Разблокировать" if is_blocked else "🚫 Заблокировать"
    # ИЗМЕНЕНО: Кнопки управления сгруппированы в один ряд
    builder.row(
        InlineKeyboardButton(text="💰 Баланс", callback_data=f"admin_user_balance_{user_id}"),
        InlineKeyboardButton(text=block_text, callback_data=f"admin_user_block_{user_id}")
    )
    builder.row(InlineKeyboardButton(text="⬅️ К списку пользователей", callback_data="admin_users"))
    return builder.as_markup()

def admin_containers_list_keyboard(all_containers: list, page: int = 0):
    builder = InlineKeyboardBuilder()
    per_page = 5
    start, end = page * per_page, (page + 1) * per_page

    for container in all_containers[start:end]:
        builder.row(InlineKeyboardButton(
            text=f"🐳 {container['name']} (ID: {container['user_id']})",
            callback_data=f"admin_manage_container_{container['id']}"
        ))

    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_containers_page_{page-1}"))
    if end < len(all_containers):
        pagination_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_containers_page_{page+1}"))
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
        
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_panel"))
    return builder.as_markup()

def admin_settings_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📋 Управление тарифами", callback_data="admin_tariffs"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в админ-панель", callback_data="admin_panel"))
    return builder.as_markup()
    
def admin_tariffs_keyboard(tariffs: list):
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        # Эта раскладка уже была хорошей (две кнопки в ряду)
        builder.row(
            InlineKeyboardButton(text=f"📝 {tariff['name']}", callback_data=f"admin_edit_tariff_{tariff['id']}"),
            InlineKeyboardButton(text="🗑️", callback_data=f"admin_delete_tariff_{tariff['id']}")
        )
    builder.row(InlineKeyboardButton(text="➕ Добавить новый тариф", callback_data="admin_add_tariff"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад к настройкам", callback_data="admin_settings"))
    return builder.as_markup()

def back_to_admin_panel():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В админ-панель", callback_data="admin_panel"))
    return builder.as_markup()