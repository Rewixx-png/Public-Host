# handlers/management_handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery

from keyboards.inline import management_keyboard, confirm_action_keyboard, my_userbots_keyboard
from services import docker_manager
from utils import database as db
from config_loader import SERVERS
from utils.texts import texts # <-- НОВЫЙ ИМПОРТ

router = Router()

@router.callback_query(F.data.startswith("manage_container_"))
async def manage_container_handler(query: CallbackQuery):
    try:
        container_db_id = int(query.data.split("_")[2])
    except (ValueError, IndexError):
        await query.answer("Ошибка: неверные данные.", show_alert=True)
        return

    user_id = query.from_user.id
    container = db.get_container_by_db_id(container_db_id)

    if not container or container['user_id'] != user_id:
        await query.answer(texts.get("management.container_not_found"), show_alert=True)
        user_containers = db.get_user_containers(user_id)
        await query.message.edit_text(
            texts.get("main_menu.my_userbots_title"), parse_mode="HTML",
            reply_markup=my_userbots_keyboard(user_containers)
        )
        return

    server = SERVERS[container['server_index']]
    
    await query.message.edit_text(texts.get("management.status_check"))
    
    status = await docker_manager.get_container_status(container, server)
    if status != 'error':
        db.update_container_status(container_db_id, status)
        container['status'] = status

    await query.message.edit_text(
        texts.get("management.menu_title", container_name=container['name'], status=status),
        parse_mode="HTML",
        reply_markup=management_keyboard(container, container_db_id)
    )
    await query.answer()


async def toggle_container_state(query: CallbackQuery, action: str):
    container_db_id = int(query.data.split("_")[1])
    user_id = query.from_user.id
    container = db.get_container_by_db_id(container_db_id)

    if not container or container['user_id'] != user_id:
        await query.answer(texts.get("management.container_not_found"), show_alert=True)
        return
        
    server = SERVERS[container['server_index']]
    await query.message.edit_text(texts.get("management.action_progress", action=action))

    success, new_status = False, container['status']

    if action == "stop":
        success = await docker_manager.stop_container(container, server)
        new_status = "exited" if success else "error"
    elif action == "start":
        success = await docker_manager.start_container(container, server)
        new_status = "running" if success else "error"

    if success:
        db.update_container_status(container_db_id, new_status)
        await query.answer(texts.get("management.action_success", action=action))
        query.data = f"manage_container_{container_db_id}" 
        await manage_container_handler(query)
    else:
        await query.message.edit_text(texts.get("management.action_error"))
        await query.answer("Ошибка!", show_alert=True)

@router.callback_query(F.data.startswith("stop_"))
async def stop_handler(query: CallbackQuery):
    await toggle_container_state(query, "stop")

@router.callback_query(F.data.startswith("start_"))
async def start_handler(query: CallbackQuery):
    await toggle_container_state(query, "start")

@router.callback_query(F.data.startswith(("delete_", "reinstall_")))
async def confirm_destructive_action_handler(query: CallbackQuery):
    action, container_db_id_str = query.data.split("_")
    container_db_id = int(container_db_id_str)
    
    text_key = f"management.confirm_{action}"
    text = texts.get(text_key)

    await query.message.edit_text(text, parse_mode="HTML", reply_markup=confirm_action_keyboard(action, container_db_id))
    await query.answer()

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_action_handler(query: CallbackQuery):
    _, action, container_db_id_str = query.data.split("_")
    container_db_id = int(container_db_id_str)
    user_id = query.from_user.id
    container = db.get_container_by_db_id(container_db_id)
    
    if not container or container['user_id'] != user_id:
        await query.answer(texts.get("management.container_not_found"), show_alert=True)
        return

    server = SERVERS[container['server_index']]
    tariff = {"cpu_limit": "0.5", "memory_limit": "256m"}

    if action == "delete":
        await query.message.edit_text(texts.get("management.delete_progress"))
        success = await docker_manager.delete_container(container, server)
        if success:
            db.delete_container_by_db_id(container_db_id)
            user_containers = db.get_user_containers(user_id)
            await query.message.edit_text(
                texts.get("management.delete_success"),
                reply_markup=my_userbots_keyboard(user_containers)
            )
        else:
            await query.message.edit_text(texts.get("management.delete_error"))

    elif action == "reinstall":
        await query.message.edit_text(texts.get("management.reinstall_progress"))
        deleted = await docker_manager.delete_container(container, server)
        if not deleted:
            await query.message.edit_text(texts.get("management.reinstall_delete_error"))
            return

        db.delete_container_by_db_id(container_db_id)
        new_container_info = await docker_manager.create_container(user_id, server, tariff)
        
        if new_container_info:
            db.add_container(user_id, new_container_info)
            new_containers = db.get_user_containers(user_id)
            new_db_id = next(c['id'] for c in new_containers if c['name'] == new_container_info['name'])

            await query.message.edit_text(
                texts.get("management.reinstall_success"),
                reply_markup=management_keyboard(new_container_info, new_db_id)
            )
        else:
            await query.message.edit_text(texts.get("management.reinstall_create_error"))
            
    await query.answer()