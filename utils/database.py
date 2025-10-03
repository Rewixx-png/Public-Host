# utils/database.py
import sqlite3
import json
from config_loader import OWNER_ID

DB_FILE = "data/PublicHost.db"

def init_db():
    """Инициализирует базу данных и создает таблицы, если их нет."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # --- Создание таблиц (без изменений) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER NOT NULL DEFAULT 0,
            is_blocked BOOLEAN NOT NULL DEFAULT 0,
            role TEXT NOT NULL DEFAULT 'member'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tariffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price INTEGER NOT NULL,
            cpu_limit TEXT NOT NULL,
            memory_limit TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS containers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            container_id TEXT NOT NULL,
            name TEXT NOT NULL,
            server_ip TEXT NOT NULL,
            port INTEGER NOT NULL,
            status TEXT NOT NULL,
            server_index INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)

    # --- ИЗМЕНЕНО: Новая служебная таблица для отслеживания первого запуска ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # --- ИЗМЕНЕНО: Полностью новая логика для первичной настройки ---
    cursor.execute("SELECT value FROM bot_settings WHERE key = 'initial_setup_complete'")
    setup_done = cursor.fetchone()

    # Этот блок кода выполнится ТОЛЬКО ОДИН РАЗ за всю жизнь базы данных
    if setup_done is None:
        print("Performing first-time database setup...")
        # 1. Добавляем тариф по умолчанию
        cursor.execute("""
            INSERT INTO tariffs (name, price, cpu_limit, memory_limit)
            VALUES (?, ?, ?, ?)
        """, ('Test', 10, '0.5', '256m'))
        print("Default tariff added.")

        # 2. Устанавливаем флаг, что настройка завершена
        cursor.execute("INSERT INTO bot_settings (key, value) VALUES (?, ?)", ('initial_setup_complete', '1'))
        print("Initial setup flag set.")

    # Эта логика будет выполняться при каждом запуске (на случай, если OWNER_ID сменится)
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (OWNER_ID,))
    cursor.execute("UPDATE users SET role = 'admin' WHERE user_id = ?", (OWNER_ID,))
    
    conn.commit()
    conn.close()

# --- (Остальная часть файла остается без изменений) ---
def get_or_create_user(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user is None:
        cursor.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return dict(user)

def update_user_balance(user_id: int, amount_change: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount_change, user_id))
    conn.commit()
    conn.close()

def set_user_balance(user_id: int, new_balance: int):
    get_or_create_user(user_id)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()

def set_user_blocked_status(user_id: int, is_blocked: bool):
    get_or_create_user(user_id)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (is_blocked, user_id))
    conn.commit()
    conn.close()

def get_all_users_info():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.user_id, u.balance, u.is_blocked, COUNT(c.id) as container_count
        FROM users u
        LEFT JOIN containers c ON u.user_id = c.user_id
        GROUP BY u.user_id
    """)
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def add_container(user_id: int, container_data: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO containers (user_id, container_id, name, server_ip, port, status, server_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, container_data['id'], container_data['name'],
        container_data['server_ip'], container_data['port'],
        container_data['status'], container_data['server_index']
    ))
    conn.commit()
    conn.close()

def get_user_containers(user_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM containers WHERE user_id = ?", (user_id,))
    containers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return containers

def get_container_by_db_id(db_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM containers WHERE id = ?", (db_id,))
    container = cursor.fetchone()
    conn.close()
    return dict(container) if container else None
    
def delete_container_by_db_id(db_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM containers WHERE id = ?", (db_id,))
    conn.commit()
    conn.close()

def update_container_status(db_id: int, new_status: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE containers SET status = ? WHERE id = ?", (new_status, db_id))
    conn.commit()
    conn.close()

def get_all_containers_info():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM containers")
    containers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return containers

def get_tariffs():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs ORDER BY price")
    tariffs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tariffs

def get_tariff_by_id(tariff_id: int):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tariffs WHERE id = ?", (tariff_id,))
    tariff = cursor.fetchone()
    conn.close()
    return dict(tariff) if tariff else None

def add_tariff(data: dict):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tariffs (name, price, cpu_limit, memory_limit) VALUES (?, ?, ?, ?)", (data['name'], data['price'], data['cpu_limit'], data['memory_limit']))
    conn.commit()
    conn.close()

def delete_tariff_by_id(tariff_id: int):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tariffs WHERE id = ?", (tariff_id,))
    conn.commit()
    conn.close()