# states.py
from aiogram.fsm.state import State, StatesGroup

class Replenishment(StatesGroup):
    awaiting_amount = State()
    awaiting_confirmation = State()
    awaiting_screenshot = State()

# НОВЫЕ СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ
class AdminStates(StatesGroup):
    # Управление балансом
    awaiting_user_id_for_balance = State()
    awaiting_balance_amount = State()
    
    # Редактирование тарифа
    awaiting_tariff_name = State()
    awaiting_tariff_price = State()
    awaiting_tariff_cpu = State()
    awaiting_tariff_memory = State()