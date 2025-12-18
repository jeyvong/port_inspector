# port_inspector
Скрипт для инвентаризации портов,  который обогащает вывод sh int status на коммутаторах доступа

1. Скрипт работает только с Cisco CLI
2. В работу берутся все порты из вывода sh int status в состояние enabled. Это значит что аплинк-порты тоже попадают в обработку.
3. Значение вланов забирается из вывода show mac address-table interface <port> каждого порта
4. Из sh int desc забирается Port Description
5. Для каждого порта запрашивается sh lldp nei <port> detail, sh lldp nei <port> detail забирается MAC, IP, System name
6. Если для порта вывод lldp и cdp пустой, то запрашивается мак адрес из вывода  show mac address-table interface <port>,
затем скрипт заходит по ssh на ядро (роутер), в общем где есть таблица ARP (адрес ядра указываете в конфиге) и запрашивает команду show ip arp | <[mac_address]> что бы узнать ip хоста на порту.


В файл настроек \port_inspector\config\switch_config.json 
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
  "excluded_ports": ["Po1","Te1/1/1","Te2/1/1"]
}

"access_switch" - целевой коммутатор доступа, роутеры не подходят.
"core_switch" - ядро (роутер), в общем где есть таблица ARP

"excluded_ports"
В настройки можно внести порт исключения, это нужно для, того что бы не запрашивать ip для каждого мак адреса за портом, если это порт аплинка и за ним в таблице mac сотни адресов.
Хотя иногда бывает полезно посмотреть что там, если нет доступа до устройства за аплинком.
В исключение нужно вносить имя порта из вывода sh int status, так и имя port channel порта в котором он учавствует.


В файл аккаунта \port_inspector\config\credentials.json 
{
  "device_type": "cisco_ios",
  "username": "admin"
}

логин используется для доступа по ssh как к access_switch так и к core_switch, введение разныл логинов не предусмотрено.

Пароль запрашивается при запуске скрипта в командной строке по структуре запуска
(venv) PS D:\...\port_inspector> python.exe main.py

