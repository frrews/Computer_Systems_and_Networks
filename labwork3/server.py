import socket
import threading
from datetime import datetime
import re
import sys

clients = []
nicknames = {}
connected_ips = set()
clients_lock = threading.Lock()
SERVER_IP = ""

def get_time():
    return datetime.now().strftime("%H:%M:%S")

def validate_ip(ip):
    if ip.lower() == 'localhost':
        return True
    pattern = r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$"
    return re.match(pattern, ip) is not None


def validate_port(port_str):
    try:
        port = int(port_str)
        return port if 1024 <= port <= 65535 else None
    except ValueError:
        return None

def broadcast(message, sender_socket=None):
    with clients_lock:
        disconnected_clients = []
        for client in clients:
            if client != sender_socket:
                try:
                    client.send(message.encode('utf-8'))
                except (socket.error, BrokenPipeError):
                    disconnected_clients.append(client)
        for client in disconnected_clients:
            remove_client(client)

def remove_client(client_socket):
    name = None
    with clients_lock:
        if client_socket in clients:
            clients.remove(client_socket)

            try:
                ip = client_socket.getpeername()[0]
                if ip in connected_ips:
                    connected_ips.remove(ip)
            except:
                pass

            if client_socket in nicknames:
                name = nicknames[client_socket]
                del nicknames[client_socket]

            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                client_socket.close()
            except:
                pass

    if name:
        print(f"[{get_time()}][СЕРВЕР] {name} отключен.")
        broadcast(f"\n[СЕРВЕР] {name} покинул чат.")

def handle_client(client_socket, addr):
    client_ip = addr[0]
    nickname = "Неизвестный"

    try:
        with clients_lock:
            if client_ip == SERVER_IP or client_ip == '127.0.0.1' or client_ip in connected_ips:
                if client_ip == SERVER_IP or client_ip == '127.0.0.1':
                    error_msg = "ERROR: Ваше IP совпадает с IP сервера."
                else:
                    error_msg = "ERROR: Пользователь с таким IP уже в чате."

                try:
                    client_socket.sendall(error_msg.encode('utf-8') + b'\n')
                    client_socket.shutdown(socket.SHUT_WR)
                    import time
                    time.sleep(0.2)
                except:
                    pass
                finally:
                    try:
                        client_socket.close()
                    except:
                        pass
                return

            connected_ips.add(client_ip)

        client_socket.settimeout(60)
        nickname = client_socket.recv(1024).decode('utf-8', errors='replace').strip()

        if not nickname:
            remove_client(client_socket)
            return

        with clients_lock:
            nicknames[client_socket] = nickname

        join_msg = f"[СЕРВЕР] {nickname} ({client_ip}) вошел в чат!"
        print(f"[{get_time()}] {join_msg}")
        broadcast(join_msg)

        client_socket.settimeout(None)

        while True:
            data = client_socket.recv(4096)
            if not data:
                break
            message = data.decode('utf-8', errors='replace')
            full_message = f"{nickname}: {message}"
            print(f"[{get_time()}][{client_ip}] {full_message}")
            broadcast(full_message, client_socket)

    except (ConnectionResetError, socket.timeout, BrokenPipeError):
        pass
    except Exception as e:
        print(f"[ОШИБКА] Сбой при работе с {nickname}: {e}")
    finally:
        remove_client(client_socket)


def server_console(server_socket):
    while True:
        cmd = input()
        if cmd.strip().lower() == "/shutdown":
            print("[СЕРВЕР] Инициирована остановка сервера...")

            with clients_lock:
                for client in list(clients):
                    try:
                        client.send("[СЕРВЕР] Сервер закрывается.".encode('utf-8'))
                        client.shutdown(socket.SHUT_RDWR)
                    except:
                        pass


            server_socket.close()
            print("[СЕРВЕР] Выход.")
            sys.exit(0)


def start_server():
    global SERVER_IP
    print("\n=== СЕРВЕР ===\n")
    server = None

    while True:
        ip = input("Введите IP сервера (например 127.0.0.1): ").strip()
        if validate_ip(ip):
            SERVER_IP = ip
            break
        print("Ошибка: Неверный формат IP.")

    while True:
        port_input = input("Введите порт для сервера (1024-65535): ").strip()
        port = validate_port(port_input)

        if not port:
            print("Ошибка: Введите корректное число от 1024 до 65535.")
            continue

        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((SERVER_IP, port))
            server.listen(10)
            break

        except OSError as e:
            print(f"Ошибка: Не удалось занять порт {port}. Возможно, он уже используется.")
            if server:
                server.close()
            print("Попробуйте ввести другой порт или освободите текущий.\n")

    try:
        console_thread = threading.Thread(target=server_console, args=(server,), daemon=True)
        console_thread.start()

        print(f"\n[{get_time()}][ЗАПУСК] Сервер успешно запущен на {SERVER_IP}:{port}...")

        while True:
            try:
                client_sock, addr = server.accept()
                with clients_lock:
                    clients.append(client_sock)
                thread = threading.Thread(target=handle_client, args=(client_sock, addr))
                thread.daemon = True
                thread.start()
            except OSError:
                break
    finally:
        if server:
            server.close()
        print(f"[{get_time()}][СЕРВЕР] Завершение работы.")

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
        sys.exit(0)