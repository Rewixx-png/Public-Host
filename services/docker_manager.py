# services/docker_manager.py
import asyncssh
import random
import string
from config_loader import DOCKER_IMAGE

def generate_random_string(length=4):
    letters = string.ascii_uppercase
    return ''.join(random.choice(letters) for i in range(length))

async def create_container(user_id, server, tariff):
    """Создает и запускает Docker контейнер на удаленном сервере с учетом лимитов."""
    # ГАРАНТИРОВАННОЕ ИСПРАВЛЕНИЕ: Импортируем SERVERS прямо здесь.
    # Это решает все проблемы с порядком загрузки модулей.
    from config_loader import SERVERS

    host_port = random.randint(10000, 65535)
    random_part = generate_random_string()
    container_name = f"Public{random_part}-Host-{user_id}"
    
    try:
        cpu_limit_val = float(tariff.get("cpu_limit", "0.5"))
        cpu_limit = "0.5" if cpu_limit_val <= 0 else str(cpu_limit_val)
    except (ValueError, TypeError):
        cpu_limit = "0.5"

    memory_limit_val = tariff.get("memory_limit", "256m")
    memory_limit = memory_limit_val if isinstance(memory_limit_val, str) and (memory_limit_val.endswith('m') or memory_limit_val.endswith('g')) else "256m"

    command = (
        f"docker run -d --name {container_name} "
        f"--hostname PublicHost "
        f"--cpus=\"{cpu_limit}\" "
        f"-m=\"{memory_limit}\" "
        f"-p {host_port}:8080 {DOCKER_IMAGE}"
    )
    print(f"Executing Docker command: {command}")

    try:
        async with asyncssh.connect(
            server["ip"], port=server["port"], username=server["user"],
            password=server["pass"], known_hosts=None
        ) as conn:
            check_command = f"docker ps -a --filter name=^{container_name}$ --format '{{{{.Names}}}}'"
            check_result = await conn.run(check_command)
            if check_result.stdout.strip():
                return await create_container(user_id, server, tariff)

            result = await conn.run(command)
            if result.exit_status == 0:
                container_id = result.stdout.strip()
                return {
                    "id": container_id,
                    "name": container_name,
                    "server_ip": server["ip"],
                    "port": host_port,
                    "status": "running",
                    "server_index": SERVERS.index(server)
                }
            else:
                print(f"Ошибка Docker: {result.stderr}")
                return None
    except Exception as e:
        print(f"Ошибка SSH при создании контейнера: {e}")
        return None

# --- (Остальные функции файла без изменений) ---
async def get_container_status(container, server):
    container_docker_id = container.get('container_id') or container.get('id')
    command = f"docker inspect --format='{{{{.State.Status}}}}' {container_docker_id}"
    try:
        async with asyncssh.connect(
            server["ip"], port=server["port"], username=server["user"],
            password=server["pass"], known_hosts=None
        ) as conn:
            result = await conn.run(command)
            return result.stdout.strip() if result.exit_status == 0 else "unknown"
    except Exception:
        return "error"

async def stop_container(container, server):
    container_docker_id = container.get('container_id') or container.get('id')
    command = f"docker stop {container_docker_id}"
    try:
        async with asyncssh.connect(
            server["ip"], port=server["port"], username=server["user"],
            password=server["pass"], known_hosts=None
        ) as conn:
            await conn.run(command)
            return True
    except Exception:
        return False

async def start_container(container, server):
    container_docker_id = container.get('container_id') or container.get('id')
    command = f"docker start {container_docker_id}"
    try:
        async with asyncssh.connect(
            server["ip"], port=server["port"], username=server["user"],
            password=server["pass"], known_hosts=None
        ) as conn:
            await conn.run(command)
            return True
    except Exception:
        return False

async def delete_container(container, server):
    container_docker_id = container.get('container_id') or container.get('id')
    command = f"docker rm -f {container_docker_id}"
    try:
        async with asyncssh.connect(
            server["ip"], port=server["port"], username=server["user"],
            password=server["pass"], known_hosts=None
        ) as conn:
            await conn.run(command)
            return True
    except Exception:
        return False