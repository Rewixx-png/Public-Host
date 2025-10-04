#!/bin/bash

# --- Установщик Public-Host Bot с PM2 (Глобальная установка) ---

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Добро пожаловать в установщик Public-Host Bot!${NC}"
echo "Этот скрипт настроит окружение и запустит бота как сервис."

# --- НАЧАЛО ПРОВЕРКИ ОКРУЖЕНИЯ ---
# Функция для вывода красивого сообщения об ошибке и выхода из скрипта
fail_with_error() {
    # Выводим сообщение в стандартный поток ошибок (stderr)
    echo -e "\n============================================================" >&2
    echo -e "!!! ${YELLOW}КРИТИЧЕСКАЯ ОШИБКА УСТАНОВКИ${NC} !!!" >&2
    echo "" >&2
    # Выводим конкретную причину, переданную в функцию
    echo -e "$1" >&2
    echo "" >&2
    echo -e "Для работы этого бота требуется полноценная Linux-система" >&2
    echo -e "с возможностью установки и запуска Docker." >&2
    echo -e "Пожалуйста, используйте VPS, VDS или выделенный сервер." >&2
    echo -e "============================================================" >&2
    # Выход с кодом ошибки
    exit 1
}

echo "Провожу проверку совместимости окружения..."

# 1. Проверка на Termux по переменной окружения или наличию папки
if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    fail_with_error "${YELLOW}Обнаружен Termux. Установка невозможна, так как Docker здесь недоступен.${NC}"
fi

# 2. Проверка на proot (используется в UserLAnd, PRoot Distro и т.д.)
# [[ ]] - это конструкция bash, она более надежна для сопоставления с образцом
if [[ "$LD_PRELOAD" == *proot* ]]; then
    fail_with_error "${YELLOW}Обнаружена среда на базе proot (например, UserLAnd). Установка невозможна.${NC}"
fi

# 3. Общая проверка на Android по наличию системного файла
if [ -e "/system/bin/app_process" ]; then
    fail_with_error "${YELLOW}Обнаружена среда Android. Установка на стандартных Android-устройствах невозможна.${NC}"
fi

echo -e "${GREEN}✅ Проверка окружения пройдена. Продолжаю установку...${NC}"
# --- КОНЕЦ ПРОВЕРКИ ОКРУЖЕНИЯ ---


# --- Вспомогательные функции ---
check_python() {
    # Проверяем наличие python3 и pip3
    if ! command -v python3 &> /dev/null || ! command -v pip3 &> /dev/null
    then
        echo -e "${YELLOW}Python 3 или pip не найдены. Пытаюсь установить...${NC}"
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip
        if ! command -v python3 &> /dev/null; then
            echo -e "${YELLOW}Установка Python не удалась. Пожалуйста, установите его вручную ('sudo apt install python3 python3-pip') и запустите скрипт снова.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Python 3 и pip уже установлены.${NC}"
    fi
}

check_and_install_pm2() {
    if ! command -v node &> /dev/null; then
        echo -e "${YELLOW}Node.js не найден. Устанавливаю Node.js (LTS)...${NC}"
        curl -sL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
        if ! command -v node &> /dev/null; then
            echo -e "${YELLOW}Не удалось установить Node.js. Установите вручную и повторите.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Node.js уже установлен.${NC}"
    fi

    if ! command -v pm2 &> /dev/null; then
        echo -e "${YELLOW}PM2 не найден. Устанавливаю PM2 глобально...${NC}"
        sudo npm install pm2 -g
        if ! command -v pm2 &> /dev/null; then
            echo -e "${YELLOW}Не удалось установить PM2. Установите вручную ('sudo npm install pm2 -g') и повторите.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}PM2 уже установлен.${NC}"
    fi
}

# --- Основной процесс установки ---
echo -e "\n--- ${BLUE}Шаг 1: Проверка системных зависимостей${NC} ---"
check_python
check_and_install_pm2

echo -e "\n--- ${BLUE}Шаг 2: Установка Python библиотек${NC} ---"

# Устанавливаем зависимости из requirements.txt глобально
if [ -f "requirements.txt" ]; then
    echo "📦 Устанавливаю зависимости из requirements.txt глобально..."
    # Используем pip3 и флаг --break-system-packages для совместимости с новыми версиями pip
    pip3 install -r requirements.txt --break-system-packages
else
    echo -e "${YELLOW}⚠️ Файл requirements.txt не найден! Установка зависимостей пропущена.${NC}"
    echo -e "${YELLOW}   Пожалуйста, убедитесь, что вы клонировали репозиторий полностью.${NC}"
    exit 1
fi

echo -e "${GREEN}Python-библиотеки успешно установлены.${NC}"

echo -e "\n--- ${BLUE}Шаг 3: Настройка конфигурации бота${NC} ---"

# Проверяем наличие config.py и создаем из примера, если его нет
if [ ! -f "config.py" ]; then
    if [ -f "config.py.example" ]; then
        echo "📝 Файл config.py не найден. Копирую из config.py.example..."
        cp config.py.example config.py
    else
        echo -e "${YELLOW}⚠️ Файлы config.py и config.py.example не найдены!${NC}"
        echo -e "${YELLOW}   Вам придется создать config.py вручную. Установка не может продолжаться.${NC}"
        exit 1
    fi
fi

echo -e "${YELLOW}Сейчас вам нужно отредактировать файл конфигурации.${NC}"
echo "Пожалуйста, откройте файл 'config.py' в текстовом редакторе и введите все необходимые данные:"
echo " - Токен бота"
echo " - Ваш Telegram ID (owner_id)"
echo " - Данные для подключения к серверам (IP, пароль и т.д.)"
echo " - Имя Docker-образа"
echo " - Реквизиты для оплаты"
echo ""
read -p "Нажмите [Enter], когда закончите редактирование файла config.py..."

# Создаем папку для базы данных
mkdir -p data

echo -e "${GREEN}Конфигурация завершена.${NC}"

# --- Шаг 4: Запуск бота через PM2 ---
echo -e "\n--- ${BLUE}Шаг 4: Запуск бота через PM2${NC} ---"

# Удаляем старый процесс, если он существует
echo "Останавливаю и удаляю предыдущую версию процесса 'Public-Host', если она существует..."
pm2 delete Public-Host || true

echo "Запускаю бота с именем 'Public-Host'..."
# Запускаем, используя системный python3
pm2 start bot.py --name Public-Host --interpreter python3

echo "Сохраняю список процессов PM2 для автозапуска после перезагрузки..."
pm2 save

echo -e "\n${GREEN}Установка и запуск успешно завершены!${NC}"
echo -e "Ваш бот теперь работает в фоновом режиме под управлением PM2."

echo -e "\n${YELLOW}--- Полезные команды PM2 ---${NC}"
echo -e "Просмотр статуса всех процессов: ${GREEN}pm2 list${NC}"
echo -e "Просмотр логов вашего бота:      ${GREEN}pm2 logs Public-Host${NC}"
echo -e "Перезапустить бота:              ${GREEN}pm2 restart Public-Host${NC}"
echo -e "Остановить бота:                 ${GREEN}pm2 stop Public-Host${NC}"

echo -e "\n${YELLOW}--- ВАЖНО: Автозапуск после перезагрузки сервера ---${NC}"
echo "Чтобы ваш бот автоматически запускался после перезагрузки сервера, выполните следующую команду."
echo "Скопируйте команду, которую выведет ${GREEN}pm2 startup${NC}, и выполните ее от имени суперпользователя (root)."
echo -e "\nВыполните это сейчас:"
echo -e "${GREEN}pm2 startup${NC}"
echo -e "\nПосле этого скопируйте и выполните ту команду, которую вам покажет."