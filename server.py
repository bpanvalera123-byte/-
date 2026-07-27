# -import socket
import json
import threading
import os

HOST = '0.0.0.0'
PORT = 50000
FILES_DIR = 'server_files'

os.makedirs(FILES_DIR, exist_ok=True)

class LocalChatServer:
    def __init__(self):
        self.clients = {}  # ip: socket
        self.users_info = {}  # ip: {username, status, avatar}
        
    def start(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((HOST, PORT))
        server.listen()
        print(f" Сервер запущен на {HOST}:{PORT}")

        while True:
            conn, addr = server.accept()
            ip = addr[0]
            self.clients[ip] = conn
            self.users_info[ip] = {"username": f"User_{ip}", "status": "online"}
            
            # Уведомляем всех об изменении статуса
            self.broadcast_status(ip, "online")
            
            thread = threading.Thread(target=self.handle_client, args=(conn, ip))
            thread.start()

    def broadcast_status(self, ip, status):
        self.users_info[ip]["status"] = status
        data = json.dumps({
            "type": "status_update",
            "ip": ip,
            "status": status
        })
        self.broadcast(data)

    def broadcast(self, message):
        for conn in list(self.clients.values()):
            try:
                conn.sendall(message.encode('utf-8'))
            except:
                pass

    def handle_client(self, conn, ip):
        while True:
            try:
                msg = conn.recv(1024 * 1024).decode('utf-8')
                if not msg:
                    break
                data = json.loads(msg)
                
                # Обработка типов сообщений
                if data["type"] in ["chat_msg", "edit_msg", "delete_msg", "reaction"]:
                    self.route_message(data, ip)
            except Exception as e:
                break
        
        # Пользователь отключился (Закрыл приложение -> Статус "Отошёл")
        conn.close()
        if ip in self.clients:
            del self.clients[ip]
        self.broadcast_status(ip, "offline")

    def route_message(self, data, sender_ip):
        data["sender"] = sender_ip
        payload = json.dumps(data)
        
        target = data.get("target") # IP пользователя или ID группы
        if target and target in self.clients:
            # Личный чат
            self.clients[target].sendall(payload.encode('utf-8'))
        else:
            # Групповой / Общий чат
            self.broadcast(payload)

if __name__ == "__main__":
    LocalChatServer().start()
