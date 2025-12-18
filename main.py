import json
import getpass
import logging
from datetime import datetime
from netmiko import ConnectHandler
from src.gather_info import gather_port_data
from src.display import print_table

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('port_inspector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("Запуск скрипта PortInspector")

        # Загружаем конфигурацию
        logger.info("Чтение switch_config.json")
        with open("config/switch_config.json", encoding='utf-8') as f:
            switch_cfg = json.load(f)
        logger.info(f"Конфигурация загружена: {switch_cfg}")

        # Загружаем учетные данные
        logger.info("Чтение credentials.json")
        with open("config/credentials.json", encoding='utf-8') as f:
            creds = json.load(f)
        logger.info(f"Учетные данные загружены: {creds}")

        # Запрашиваем пароль и secret
        logger.info(f"Запрос пароля для пользователя {creds['username']}")
        creds['password'] = getpass.getpass(f"Введите пароль для пользователя {creds['username']}: ")
        logger.info("Пароль успешно введен")
        logger.info(f"Запрос enable secret для пользователя {creds['username']}")
        creds['secret'] = getpass.getpass(f"Введите enable secret для пользователя {creds['username']}: ")
        logger.info("Enable secret успешно введен")

        # Собираем данные
        logger.info("Запуск gather_port_data")
        result = gather_port_data(switch_cfg, creds)
        logger.info("gather_port_data завершен")

        # Формируем timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        logger.info(f"Timestamp: {timestamp}")

        # Получаем hostname через парсинг промпта (без enable)
        logger.info(f"Подключение к {switch_cfg['access_switch']} для получения hostname")
        device = {
            "device_type": creds["device_type"],
            "host": switch_cfg["access_switch"],
            "username": creds["username"],
            "password": creds["password"],
            "secret": creds["secret"],
            "port": 22
        }
        conn = ConnectHandler(**device)
        logger.info("Подключение установлено")
        prompt = conn.find_prompt()
        hostname = prompt.rstrip('#').rstrip('>').strip()  # Удаляем # или > и пробелы
        conn.disconnect()
        logger.info("Подключение закрыто")
        if not hostname:
            hostname = switch_cfg.get("access_switch", "unknown_switch")
        logger.info(f"Hostname получен: {hostname}")

        # Печать таблицы и сохранение в CSV
        logger.info("Вывод таблицы и сохранение в CSV")
        print_table(result, hostname, timestamp)
        logger.info("Скрипт PortInspector завершен")

    except FileNotFoundError as e:
        logger.error(f"Ошибка: Файл не найден - {e}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка: Неверный формат JSON - {e}")
        raise
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    main()