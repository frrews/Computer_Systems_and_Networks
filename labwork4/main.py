import socket
import threading
import os
import time
from urllib.parse import urlparse
from http import HTTPStatus

PROXY_HOST = '127.0.0.2'
PROXY_PORT = 8080
BLACKLIST_FILE = "blocked_sites.txt"

blacklist = []
blacklist_lock = threading.Lock()
last_mtime = 0


def load_blacklist():

    global blacklist, last_mtime
    if not os.path.exists(BLACKLIST_FILE):
        return

    try:
        current_mtime = os.path.getmtime(BLACKLIST_FILE)
        if current_mtime > last_mtime:
            with blacklist_lock:
                new_list = []
                with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        site = line.strip()
                        if site:
                            new_list.append(site)
                blacklist = new_list
                last_mtime = current_mtime
                print(f"\n[SYSTEM] Черный список обновлен (загружено: {len(blacklist)} записей)")
    except Exception as e:
        print(f"Ошибка при загрузке черного списка: {e}")


def monitor_blacklist():
    while True:
        load_blacklist()
        time.sleep(2)

def send_blocked_page(client_conn, blocked_url):
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"><title>Доступ ограничен</title></head>
    <body style="text-align:center; font-family: sans-serif; padding-top: 50px;">
        <h1 style="color: red;">САЙТ ЗАБЛОКИРОВАН РОДИТЕЛЬСКИМ КОНТРОЛЕМ =(</h1>
        <p>Адрес <strong>{blocked_url}</strong> находится в черном списке.</p>
    </body>
    </html>"""

    response = (
        "HTTP/1.1 403 Forbidden\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(html_body.encode('utf-8'))}\r\n"
        "Connection: close\r\n"
        "\r\n"
        f"{html_body}"
    )
    try:
        client_conn.sendall(response.encode('utf-8'))
    except:
        pass


def forward_data(source, destination):
    try:
        while True:
            data = source.recv(8192)
            if not data:
                break
            destination.sendall(data)
    except:
        pass


def handle_client(client_conn, client_addr):
    try:
        request_data = client_conn.recv(8192)
        if not request_data:
            client_conn.close()
            return

        header_lines = request_data.split(b'\r\n')
        first_line = header_lines[0].decode('utf-8', errors='ignore')
        parts = first_line.split()

        if len(parts) < 3:
            client_conn.close()
            return

        method = parts[0]
        full_url = parts[1]
        protocol = parts[2]

        with blacklist_lock:
            for blocked_item in blacklist:
                if blocked_item in full_url:
                    print(f"[BLOCK] Доступ запрещён: {full_url}")
                    send_blocked_page(client_conn, full_url)
                    client_conn.close()
                    return

        parsed_url = urlparse(full_url)
        hostname = parsed_url.hostname
        if not hostname:
            client_conn.close()
            return

        port = parsed_url.port or 80
        path = parsed_url.path if parsed_url.path else "/"
        if parsed_url.query:
            path += "?" + parsed_url.query

        target_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_conn.settimeout(5.0)
        target_conn.connect((hostname, port))

        new_first_line = f"{method} {path} {protocol}\r\n"
        # В блоке сборки заголовков:
        modified_request = new_first_line.encode('utf-8')
        if len(header_lines) > 1:
            for line in header_lines[1:]:
                if line.lower().startswith(b'connection:'):
                    modified_request += b'Connection: close\r\n'
                else:
                    modified_request += line + b'\r\n'
            modified_request += b'\r\n'

        target_conn.sendall(modified_request)

        response_start = target_conn.recv(8192)
        status_code = "000"
        status_phrase = "Unknown"

        if response_start:
            resp_lines = response_start.split(b'\r\n')
            if len(resp_lines) > 0:
                resp_parts = resp_lines[0].decode('utf-8', errors='ignore').split()
                if len(resp_parts) > 1:
                    status_code = resp_parts[1]
                    try:
                        status_phrase = HTTPStatus(int(status_code)).phrase
                    except:
                        status_phrase = "Unknown Code"

            print(f"[LOG] {client_addr[0]} -> {full_url} | {status_code} {status_phrase}")

            client_conn.sendall(response_start)

        t1 = threading.Thread(target=forward_data, args=(client_conn, target_conn))
        t2 = threading.Thread(target=forward_data, args=(target_conn, client_conn))
        t1.start()
        t2.start()

    except Exception as e:
        # print(f"[DEBUG] Ошибка: {e}")
        pass


def main():
    monitor_thread = threading.Thread(target=monitor_blacklist, daemon=True)
    monitor_thread.start()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server.bind((PROXY_HOST, PROXY_PORT))
        server.listen(100)
        print(f"ПРОКСИ ЗАПУЩЕН НА: {PROXY_HOST}:{PROXY_PORT}")
        print(f"Для блокировки сайтов просто добавьте их в {BLACKLIST_FILE} и сохраните файл.")
    except Exception as e:
        print(f"Ошибка: {e}")
        return

    try:
        while True:
            client_sock, addr = server.accept()
            client_thread = threading.Thread(target=handle_client, args=(client_sock, addr))
            client_thread.daemon = True
            client_thread.start()
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        server.close()


if __name__ == "__main__":
    main()