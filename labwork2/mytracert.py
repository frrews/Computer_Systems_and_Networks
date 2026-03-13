import socket
import struct
import time
import os
import sys
import ctypes

ICMP_ECHO_REQUEST = 8
TRIES = 3
TIMEOUT = 2
MAX_HOPS = 30



def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    python_path = f'"{sys.executable}"'
    script_path = f'"{" ".join(sys.argv)}"'
    ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        "cmd.exe",
        f'/K ""{sys.executable}" {" ".join(sys.argv)}""',
        None,
        1
    )
    sys.exit()


def checksum(data):
    total = 0
    i = 0

    while i < len(data) - 1:
        word = data[i] * 256 + data[i + 1]
        total += word
        i += 2


    if len(data) % 2:
        total += data[-1] * 256

    while total > 0xffff:
        total = (total & 0xffff) + (total >> 16)

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

    # проверяем, является ли ввод IP
    try:
        socket.inet_aton(dest_name)
        is_ip = True
    except socket.error:
        is_ip = False

    if resolve_names:
        try:
            hostname = socket.gethostbyaddr(dest_addr)[0]
        except socket.herror:
            hostname = dest_name
        print(f"\nТрассировка маршрута к {hostname} ({dest_addr})")

    else:
        if is_ip:
            print(f"\nТрассировка маршрута к {dest_addr}")
        else:
            print(f"\nТрассировка маршрута к {dest_name} ({dest_addr})")

    print(f"Максимальное количество прыжков: {MAX_HOPS}\n")

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
                times.append(f"{round(rtt)} ms")

            except socket.timeout:
                times.append("*")

            recv_socket.close()
            send_socket.close()
            seq += 1

        if hop_ip:
            try:
                hostname = socket.gethostbyaddr(hop_ip)[0] if resolve_names else hop_ip
                host_display = f"{hostname} ({hop_ip})" if resolve_names else hop_ip
            except socket.herror:
                host_display = hop_ip
        else:
            host_display = "Превышен интервал ожидания для запроса"

        times_str = "   ".join(f"{t:>8}" for t in times)
        print(f"{ttl:>2}  {times_str}   {host_display}")

        if hop_ip == dest_addr:
            break

    print(f"\nТрассировка завершена.\n")


if __name__ == "__main__":

    if len(sys.argv) < 2:
        sys.exit()

    resolve_names = False

    if sys.argv[1] == "-d":
        if len(sys.argv) < 3:
            print("Ошибка: не указан хост")
            sys.exit()
        resolve_names = True
        target = sys.argv[2]
    else:
        target = sys.argv[1]

    try:
        traceroute(target, resolve_names)

    except socket.gaierror:
        print("Ошибка: Не удаётся разрешить имя хоста")

    except PermissionError:
        print("Ошибка: Требуются права администратора")

    except KeyboardInterrupt:
        print("\nПрервано")

    except Exception as e:
        print(f"Ошибка: {e}")

