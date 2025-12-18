import re
from netmiko import ConnectHandler
import time


def normalize_name(name):
    return re.sub(r'\s+', '', name)


def parse_mac_address_table(output):
    # Парсим MAC-адреса и VLAN из show mac address-table
    mac_matches = re.findall(r"^\s*(\d+)\s+([0-9a-fA-F:.]{12,17})\s+\S+\s+\S+", output, re.MULTILINE)
    if not mac_matches:
        return {"mac_addresses": [], "vlans": "-"}
    # Собираем все VLAN для всех MAC
    vlans = sorted(set(match[0] for match in mac_matches))
    mac_addresses = [match[1] for match in mac_matches]
    return {"mac_addresses": mac_addresses, "vlans": ",".join(vlans) if vlans else "-"}


def parse_arp_table(output):
    # Парсим IP из show ip arp | include <mac>
    ip_match = re.search(r"Internet\s+(\d+\.\d+\.\d+\.\d+)\s+\d+\s+[0-9a-fA-F:.]{12,17}\s+ARPA", output)
    return ip_match.group(1) if ip_match else "-"


def parse_lldp_detail(output):
    # Регулярное выражение для MAC-адреса из Port id (для Avaya) и Chassis id (для других)
    port_id = re.search(r"Port id:\s+([0-9a-fA-F:.]{12,17})", output, re.IGNORECASE)
    chassis_id = re.search(r"Chassis id:\s+([0-9a-fA-F:.]{12,17})", output, re.IGNORECASE)
    ip_match = re.search(r"IP:\s+(\d+\.\d+\.\d+\.\d+)", output)
    name_match = re.search(r"System Name:\s+([^\n\r]+)", output)

    ip = ip_match.group(1) if ip_match else "-"
    sys_name = name_match.group(1).strip() if name_match else None
    manuf_match = re.search(r"Manufacturer:\s+([^\n\r]+)", output)
    is_avaya = manuf_match and manuf_match.group(1).strip().lower() == "avaya" or (
                sys_name and sys_name.startswith("AVX"))

    # Для Avaya используем Port id, для других — Chassis id
    mac = port_id.group(1) if port_id and is_avaya else chassis_id.group(1) if chassis_id else "-"

    # Формируем System Name
    if sys_name and is_avaya:
        model_match = re.search(r"Model:\s+([^\n\r]+)", output)
        sys_name = normalize_name(manuf_match.group(1) + model_match.group(1)) if manuf_match and model_match else "-"
    elif sys_name:
        sys_name = sys_name
    else:
        manuf_match = re.search(r"Manufacturer:\s+([^\n\r]+)", output)
        model_match = re.search(r"Model:\s+([^\n\r]+)", output)
        sys_name = normalize_name(manuf_match.group(1) + model_match.group(1)) if manuf_match and model_match else "-"

    return {
        "mac_address": mac,
        "ip_address": ip,
        "system_name": sys_name
    }


def parse_cdp_detail(output):
    ip_match = re.search(r"IP address: (\d+\.\d+\.\d+\.\d+)", output)
    name_match = re.search(r"Device ID: ([^\n\r]+)", output)
    chassis_id = re.search(r"Platform: .+,  Capabilities: .+\n.+Address:\s+([0-9a-fA-F:.]{12,17})", output,
                           re.IGNORECASE)

    ip = ip_match.group(1) if ip_match else "-"
    name = name_match.group(1).strip() if name_match else "-"
    mac = chassis_id.group(1) if chassis_id else "-"

    return {
        "mac_address": mac,
        "ip_address": ip,
        "system_name": name
    }


def parse_port_description(output):
    # Парсим Port Description из show interfaces description | include <port>
    # Ожидаемый формат: Gi1/0/41                       up             up       912_SKUD
    # Или с заголовком: Interface                      Status         Protocol Description
    #                   Gi1/0/41                       up             up       912_SKUD
    output = output.strip()
    # Удаляем промпт и пустые строки
    lines = [line.strip() for line in output.splitlines() if line.strip() and not line.startswith("#")]

    # Если есть заголовок, пропускаем его
    if lines and "Interface" in lines[0]:
        data_lines = lines[1:]
    else:
        data_lines = lines

    # Берем первую строку данных
    if data_lines:
        data_line = data_lines[0]
        # Разделяем по нескольким пробелам
        parts = re.split(r'\s{2,}', data_line)
        if len(parts) >= 4:
            # Описание - последняя часть
            return parts[3].strip()
        elif len(parts) == 3:
            # Если нет Protocol, возможно Status up Description
            return parts[2].strip()
    return "-"


def parse_device_info(connection, port, core_switch_ip, creds):
    # Шаг 1: Получаем MAC и VLAN из show mac address-table
    max_attempts = 100
    attempt = 0
    mac_output = ""
    while attempt < max_attempts:
        mac_output = connection.send_command(f"show mac address-table interface {port}", use_textfsm=False)
        print(f"📜 MAC address-table output for port {port} (attempt {attempt + 1}):\n{mac_output}\n")
        mac_info = parse_mac_address_table(mac_output)
        if mac_info["mac_addresses"]:
            break
        attempt += 1
        time.sleep(0.1)  # Небольшая задержка, чтобы не перегружать коммутатор

    if attempt == max_attempts:
        print(f"❌ Не удалось получить MAC-адреса для порта {port} после {max_attempts} попыток\n")
        mac_info = {"mac_addresses": [], "vlans": "-"}

    # Создаем список для хранения информации по каждому MAC
    devices = []

    # Обрабатываем каждый MAC-адрес
    for mac_address in mac_info["mac_addresses"]:
        device_info = {
            "mac_address": mac_address,
            "ip_address": "-",
            "system_name": "-",
            "vlans": mac_info["vlans"],
            "port_description": "-"
        }

        # Получаем IP из ARP на ядре, если MAC есть
        if mac_address != "-" and core_switch_ip and creds:
            try:
                core_conn = ConnectHandler(host=core_switch_ip, **creds)
                core_conn.enable()
                arp_output = core_conn.send_command(f"show ip arp | include {mac_address}", use_textfsm=False)
                print(f"📜 ARP output for MAC {mac_address}:\n{arp_output}\n")
                device_info["ip_address"] = parse_arp_table(arp_output)
                core_conn.disconnect()
            except Exception as e:
                print(f"❌ Не удалось получить ARP для MAC {mac_address} на порту {port}: {e}\n")

        # Шаг 2: Если System Name отсутствует, проверяем LLDP
        try:
            output = connection.send_command(f"show lldp neighbors {port} detail", use_textfsm=False)
            print(f"📜 LLDP output for port {port}:\n{output}\n")
            if "Total entries displayed: 0" not in output:
                lldp_info = parse_lldp_detail(output)
                device_info["system_name"] = lldp_info["system_name"]
                device_info["mac_address"] = lldp_info["mac_address"] if lldp_info["mac_address"] != "-" else \
                device_info["mac_address"]
                device_info["ip_address"] = lldp_info["ip_address"] if lldp_info["ip_address"] != "-" else device_info[
                    "ip_address"]
        except Exception as e:
            print(f"❌ LLDP ошибка для порта {port}: {e}\n")

        # Шаг 3: Если System Name все еще отсутствует, проверяем CDP
        if device_info["system_name"] == "-":
            try:
                output = connection.send_command(f"show cdp neighbors {port} detail", use_textfsm=False)
                print(f"📜 CDP output for port {port}:\n{output}\n")
                if "Total entries displayed: 0" not in output:
                    cdp_info = parse_cdp_detail(output)
                    device_info["system_name"] = cdp_info["system_name"]
                    device_info["mac_address"] = cdp_info["mac_address"] if cdp_info["mac_address"] != "-" else \
                    device_info["mac_address"]
                    device_info["ip_address"] = cdp_info["ip_address"] if cdp_info["ip_address"] != "-" else \
                    device_info["ip_address"]
            except Exception as e:
                print(f"❌ CDP ошибка для порта {port}: {e}\n")

        # Получаем Port Description
        try:
            desc_output = connection.send_command(f"show interfaces description | include {port}", use_textfsm=False)
            device_info["port_description"] = parse_port_description(desc_output)
        except Exception:
            device_info["port_description"] = "-"

        devices.append(device_info)

    # Если MAC-адресов нет, добавляем пустую запись
    if not devices:
        devices.append({
            "mac_address": "-",
            "ip_address": "-",
            "system_name": "-",
            "vlans": mac_info["vlans"],
            "port_description": "-"
        })

    return devices