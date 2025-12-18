from netmiko import ConnectHandler
from src.parsers import parse_device_info
import re

def gather_port_data(cfg, creds):
    access_ip = cfg["access_switch"]
    core_ip = cfg["core_switch"]
    excluded_ports = cfg.get("excluded_ports", [])  # Получаем список исключенных портов, по умолчанию пустой
    conn = ConnectHandler(host=access_ip, **creds)
    #conn.enable()

    result = []

    # Получаем список портов со статусом "connected"
    int_status_output = conn.send_command("show interfaces status | include connected")
    ports = re.findall(r"^(\S+)", int_status_output, re.MULTILINE)

    # Фильтруем порты, исключая те, что указаны в excluded_ports
    ports = [port for port in ports if port not in excluded_ports]

    for port in ports:
        print(f"🔍 Обрабатываем порт {port}...")
        devices = parse_device_info(conn, port, core_ip, creds)

        for device_info in devices:
            row = {
                "VLAN": device_info.get("vlans", "-"),
                "Port": port,
                "System Name": device_info["system_name"],
                "IP Address": device_info["ip_address"],
                "MAC Address": device_info["mac_address"],
                "Port Description": device_info["port_description"]
            }
            result.append(row)

    conn.disconnect()
    return result