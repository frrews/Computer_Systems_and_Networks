import socket
import threading
import sys
import re

stop_event = threading.Event()

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

def is_port_free(port, ip):
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.bind((ip, port))
        test_socket.close()
        return True
    except OSError:
        return False

def is_ip_valid_local(ip):
    try:
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.bind((ip, 0))
        test_socket.close()
        return True
    except OSError:
        return False

def receive_messages(client_socket):
    while not stop_event.is_set():
        try:
            data = client_socket.recv(1024)
            if not data:
                if not stop_event.is_set():
                    print("\n[СИСТЕМА] Соединение закрыто сервером.")
                    stop_event.set()
                try:
                    client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                client_socket.close()
                break

            message = data.decode('utf-8', errors='replace')
            sys.stdout.write("\r" + " " * 60 + "\r")
            print(message)
            sys.stdout.write("Вы: ")
            sys.stdout.flush()

        except socket.error:
            if not stop_event.is_set():
                print("\n[ОШИБКА] Потеря связи с сервером.")
                stop_event.set()
            break

def start_client():
    print("\n=== КЛИЕНТ ===\n")

    while True:
        server_ip = input("Введите IP сервера: ").strip()
        if validate_ip(server_ip): break
        print("Ошибка: Неверный формат IP.")

    while True:
        port_input = input("Введите порт сервера: ").strip()
        server_port = validate_port(port_input)
        if server_port: break
        print("Ошибка: Порт должен быть числом 1024-65535.")

    while True:
        nickname = input("Введите ваш ник: ").strip()
        if nickname: break
        print("Ник не может быть пустым.")

    while True:
        stop_event.clear()
        client_socket = None

        print("\n--- Настройка локального адреса ---")
        while True:
            local_ip = input("Введите ВАШ локальный IP: ").strip()
            if not validate_ip(local_ip):
                print("Ошибка: Неверный формат IP.")
                continue
            if not is_ip_valid_local(local_ip):
                print("Ошибка: Этот IP не принадлежит вашей машине.")
                continue
            break

        while True:
            local_port_input = input("Введите ВАШ локальный порт: ").strip()
            local_port = validate_port(local_port_input)
            if not local_port:
                print("Ошибка: Порт должен быть числом 1024-65535.")
                continue
            if not is_port_free(local_port, local_ip):
                print("Ошибка: Этот порт уже занят.")
                continue
            break

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            client_socket.bind((local_ip, local_port))
            client_socket.settimeout(5)
            client_socket.connect((server_ip, server_port))

            client_socket.send(nickname.encode('utf-8'))

            response_data = b''
            while True:
                try:
                    chunk = client_socket.recv(1024)
                    if not chunk:
                        break
                    response_data += chunk

                    if b"ERROR:" in response_data:
                        break
                except socket.timeout:
                    break

            if not response_data:
                print("[ОШИБКА] Сервер закрыл соединение без ответа.")
                client_socket.close()
                continue

            response = response_data.decode('utf-8', errors='replace').strip()

            if response.startswith("ERROR:"):
                print(f"\n[ОТКАЗ СЕРВЕРА] {response}")
                try:
                    client_socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                client_socket.close()
                continue

            print(response)
            client_socket.settimeout(None)

            thread = threading.Thread(target=receive_messages, args=(client_socket,))
            thread.daemon = True
            thread.start()
            print("\n--- Вы успешно вошли в чат. Для выхода введите /exit ---\n")

            while not stop_event.is_set():
                sys.stdout.write("Вы: ")
                sys.stdout.flush()
                try:
                    msg = input("")
                    if msg.strip().lower() == "/exit":
                        stop_event.set()
                        break
                    if stop_event.is_set():
                        break
                    if msg.strip():
                        client_socket.send(msg.encode('utf-8'))
                except EOFError:
                    stop_event.set()
                    break

            print("\nВыход из чата...")
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
                client_socket.close()
            except:
                pass
            return

        except socket.timeout:
            print("Ошибка: Время ожидания подключения истекло.")
        except Exception as e:
            print(f"Ошибка: {e}")

        if client_socket:
            try:
                client_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            client_socket.close()

        choice = input("\nПопробовать снова с другим локальным IP/портом? (y/n): ")
        if choice.lower() != 'y':
            break


if __name__ == "__main__":
    try:
        start_client()
    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
        sys.exit(0)