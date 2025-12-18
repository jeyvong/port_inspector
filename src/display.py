from prettytable import PrettyTable
import csv
import os


def save_to_csv(data, hostname, timestamp):
    # Формируем имя файла
    filename = f"{hostname}_{timestamp}.csv"

    # Поля для CSV
    fieldnames = ["VLAN", "Port", "System Name", "IP Address", "MAC Address", "Port Description"]

    # Сохраняем данные в CSV
    with open(filename, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow({
                "VLAN": row["VLAN"],
                "Port": row["Port"],
                "System Name": row["System Name"],
                "IP Address": row["IP Address"],
                "MAC Address": row["MAC Address"],
                "Port Description": row["Port Description"]
            })
    print(f"📄 Таблица сохранена в файл: {filename}")


def print_table(data, hostname="unknown_switch", timestamp=None):
    table = PrettyTable()
    table.field_names = ["VLAN", "Port", "System Name", "IP Address", "MAC Address", "Port Description"]

    for row in data:
        table.add_row([
            row["VLAN"],
            row["Port"],
            row["System Name"],
            row["IP Address"],
            row["MAC Address"],
            row["Port Description"]
        ])

    print(f"\n🎯 Результат опроса портов (хост: {hostname}):\n")
    print(table)

    # Сохраняем в CSV, если передан timestamp
    if timestamp:
        save_to_csv(data, hostname, timestamp)