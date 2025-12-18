# Port Inspector

Скрипт для инвентаризации портов на коммутаторах доступа Cisco, который обогащает вывод команды `show interfaces status` дополнительными данными о подключенных устройствах. Инструмент автоматизирует сбор информации о VLAN, MAC-адресах, IP-адресах, System Name и Port Description, используя протоколы LLDP/CDP и ARP-таблицу на core-устройстве.

## Требования
- Скрипт работает только с Cisco CLI (IOS/IOS-XE).
- Поддерживает порты в состоянии "enabled" (connected) из вывода `show interfaces status`. Это включает как порты доступа, так и аплинки (если не исключены в конфиге).
- Для работы требуется Python 3.x с библиотеками: `netmiko`, `prettytable`.
- Учетные данные и конфигурация хранятся в JSON-файлах (см. ниже).

## Как работает скрипт
1. **Сбор портов**: Берутся все порты в состоянии "connected" из вывода `show interfaces status`. Апплинки тоже обрабатываются, если не исключены.
2. **VLAN**: Значение VLAN забирается из вывода `show mac address-table interface <port>` для каждого порта.
3. **Port Description**: Извлекается из `show interfaces description`.
4. **LLDP/CDP**: Для каждого порта запрашивается `show lldp neighbors <port> detail` или `show cdp neighbors <port> detail`. Из них извлекаются MAC, IP и System Name.
5. **Fallback на MAC и ARP**: Если LLDP/CDP пустые, извлекается MAC из `show mac address-table interface <port>`. Затем скрипт подключается по SSH к core-устройству (ядро/роутер с ARP-таблицей) и запрашивает `show ip arp | include <mac_address>` для получения IP хоста по каждому MAC адресу на порте.
6. **Исключения**: В конфиге можно указать порты для исключения (например, аплинки с сотнями MAC), чтобы избежать лишних запросов. Укажите имя порта из `show interfaces status` или имя PortChannel.

## Конфигурация
### switch_config.json
Файл с настройками устройства и исключениями:
```json
{
  "access_switch": "192.168.1.10",
  "core_switch": "192.168.1.1",
  "hostname": "-",
  "commands": [
    "show mac address-table",
    "show lldp neighbors detail",
    "show cdp neighbors detail",
    "show interfaces status",
    "show interfaces description"
  ],
  "excluded_ports": ["Po1", "Te1/1/1", "Te2/1/1"]
}
```
- `access_switch`: IP целевого коммутатора доступа (не роутер).
- `core_switch`: IP ядра/роутера с ARP-таблицей.
- `excluded_ports`: Список портов для исключения (имена из `show interfaces status`, включая PortChannel, если применимо). Полезно для аплинков с большим количеством MAC.

### credentials.json
Файл с учетными данными (пароль и secret запрашиваются при запуске):
```json
{
  "device_type": "cisco_ios",
  "username": "admin"
}
```
- Логин используется для SSH-доступа как к `access_switch`, так и к `core_switch`. Разные логины не поддерживаются.

## Запуск
1. Установите зависимости: `pip install -r requirements.txt`.
2. Запустите скрипт: `python main.py`.
3. Введите пароль и enable secret при запросе.
4. Результат: Таблица в консоли + CSV-файл с именем `<hostname>_<date_time>.csv`.

Пример запуска:
```
(venv) PS D:\...\port_inspector> python.exe main.py
```

## Возможные проблемы и советы
- Если MAC-таблица пустая, скрипт повторяет запрос до 100 раз (с задержкой) для учета задержек ASIC.
- Для аплинков с сотнями MAC используйте `excluded_ports`, чтобы избежать нагрузки.
- Логи сохраняются в `port_inspector.log` для отладки.

## Разработка и улучшения
Проект открыт для доработок: добавление фильтров по VLAN, интеграция с системами мониторинга или расширение на другие вендоры. Контакт: [ТГ @ev01123].
