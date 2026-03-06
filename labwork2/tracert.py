import socket
import struct
import time
import os
import sys
import ctypes

ICMP_ECHO_REQUEST = 8
MAX_HOPS = 30
TRIES = 3
TIMEOUT = 2


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit()


def checksum(data):
    s = 0
    n = len(data)

    for i in range(0, n - n % 2, 2):
        s += (data[i] << 8) + data[i + 1]

    if n % 2:
        s += data[-1] << 8

    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)

    return ~s & 0xffff


def create_packet(seq):
    pid = os.getpid() & 0xffff

    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, 0, pid, seq)
    data = struct.pack("d", time.time())

    chksum = checksum(header + data)

    header = struct.pack("!BBHHH", ICMP_ECHO_REQUEST, 0, chksum, pid, seq)

    return header + data


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
                print("Invalid syntax\n")
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