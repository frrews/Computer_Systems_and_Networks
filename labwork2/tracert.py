import socket
import struct
import time
import os
import sys
import ctypes
import winreg  # добавлено для работы с реестром

ICMP_ECHO_REQUEST = 8
TRIES = 3
TIMEOUT = 2
MAX_HOPS = 30


# -------------------- Вставка в самое начало --------------------
if not ctypes.windll.shell32.IsUserAnAdmin():
    exe_path = os.path.abspath(sys.argv[0])
    # Запускаем CMD от администратора и выполняем этот exe
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        r"C:\Windows\System32\cmd.exe",
        f'/k "{exe_path}"',
        None,
        1
    )
    sys.exit()
# -------------------- Конец вставки --------------------
# -------------------- Новое: функции админ+PATH --------------------
def run_as_admin():
    """Если нет прав администратора, перезапускаем скрипт с правами админа."""
    if ctypes.windll.shell32.IsUserAnAdmin():
        return True

    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    return False

def add_to_path():
    """Добавляет текущую папку exe в системный PATH."""
    exe_path = os.path.abspath(sys.argv[0])
    exe_dir = os.path.dirname(exe_path)

    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE
        )

        current_path, _ = winreg.QueryValueEx(key, "Path")

        if exe_dir.lower() not in current_path.lower():
            new_path = current_path + ";" + exe_dir
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)
            print(f"[+] {exe_dir} добавлен в PATH.")
        winreg.CloseKey(key)
    except Exception as e:
        print(f"[!] Не удалось добавить в PATH: {e}")

# -------------------- Запуск админа и PATH --------------------
if not run_as_admin():
    sys.exit()  # перезапустится с админ правами

add_to_path()  # добавляем папку exe в системный PATH

# -------------------- Существующий код ниже без изменений --------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def checksum(data):
    total = 0
    i = 0

    # складываем по 2 байта
    while i < len(data) - 1:
        word = data[i] * 256 + data[i + 1]  # превращаем 2 байта в число
        total += word
        i += 2

    # если остался один байт
    if len(data) % 2:
        total += data[-1] * 256

    # добавляем переносы
    while total > 0xffff:
        total = (total & 0xffff) + (total >> 16)

    # инверсия
    total = ~total & 0xffff

    return total


def create_packet(seq):

    pid = os.getpid()
    pid = pid & 0xffff

    icmp_type = ICMP_ECHO_REQUEST
    code = 0
    checksum_value = 0

    header = struct.pack("!BBHHH",icmp_type, code,checksum_value,pid,seq)

    current_time = time.time()
    data = struct.pack("d", current_time)

    packet = header + data
    checksum_value = checksum(packet)

    header = struct.pack("!BBHHH",icmp_type,code,checksum_value,pid,seq)
    packet = header + data
    return packet

def traceroute(dest_name, resolve_names=False):

    dest_addr = socket.gethostbyname(dest_name)

    print(f"\nTraceroute to {dest_name} ({dest_addr})\n")

    seq = 1

    for ttl in range(1, MAX_HOPS + 1):

        times = []
        hop_ip = None

        for _ in range(TRIES):

            recv_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            send_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)

            send_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)

            recv_socket.settimeout(TIMEOUT)
            recv_socket.bind(("", 0))

            packet = create_packet(seq)

            start = time.time()
            send_socket.sendto(packet, (dest_addr, 0))

            try:
                data, addr = recv_socket.recvfrom(512)
                end = time.time()

                hop_ip = addr[0]
                rtt = (end - start) * 1000
                times.append(f"{rtt:.2f} ms")

            except socket.timeout:
                times.append("*")

            recv_socket.close()
            send_socket.close()

            seq += 1

        if hop_ip:
            if resolve_names:
                try:
                    hostname = socket.gethostbyaddr(hop_ip)[0]
                    host_display = f"{hostname} ({hop_ip})"
                except socket.herror:
                    host_display = hop_ip
            else:
                host_display = hop_ip
        else:
            host_display = "Request timed out"
        times_str = "   ".join(f"{t:>8}" for t in times)

        print(f"{ttl:>2}  {times_str}   {host_display}")

        if hop_ip == dest_addr:
            break


if __name__ == "__main__":

    print("Утилита mytracert\n")
    print("Команды:")
    print("  mytracert host      -> показывает только IP адреса")
    print("  mytracert -d host   -> показывает имена хостов и IP")
    print("Введите 'esc' для выхода\n")

    while True:
        try:
            command = input("Введите команду: ").strip()

            if command.lower() == "esc":
                print("Выход...")
                break

            if not command:
                continue

            parts = command.split()

            if parts[0] != "mytracert":
                print("Неверная команда\n")
                continue

            resolve_names = False

            if len(parts) == 2:
                target = parts[1]

            elif len(parts) == 3 and parts[1] == "-d":
                resolve_names = True
                target = parts[2]

            else:
                print("Неверный синтаксис\n")
                continue

            traceroute(target, resolve_names)

        except socket.gaierror:
            print("Ошибка: Unable to resolve hostname\n")

        except PermissionError:
            print("Ошибка: Administrator privileges required\n")

        except KeyboardInterrupt:
            print("\nInterrupted\n")

        except Exception as e:
            print(f"Ошибка: {e}\n")