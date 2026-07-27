import sys
import socket
import json
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout, 
                             QVBoxLayout, QListWidget, QListWidgetItem, QTextEdit, 
                             QPushButton, QLabel, QFileDialog, QMenu, QInputDialog)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap

# Сетевой поток для приема данных
class NetworkWorker(QThread):
    message_received = Signal(dict)
    
    def __init__(self, host_ip):
        super().__init__()
        self.host_ip = host_ip
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def run(self):
        try:
            self.socket.connect((self.host_ip, 50000))
            while True:
                data = self.socket.recv(1024 * 1024).decode('utf-8')
                if data:
                    self.message_received.emit(json.loads(data))
        except Exception as e:
            print(f"Ошибка сети: {e}")

    def send(self, data):
        self.socket.sendall(json.dumps(data).encode('utf-8'))

class ChatApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.custom_names = {}  # Кастомные имена пользователей по IP
        self.messages = {}      # Хранение ID сообщений для ред/удал

    def init_ui(self):
        self.setWindowTitle("Локальный LAN-Чат")
        self.resize(1000, 700)
        
        # Главный виджет и векторный лейаут (Плавное масштабирование)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # Левая панель — пользователи / чаты
        left_panel = QVBoxLayout()
        self.user_list = QListWidget()
        self.user_list.itemDoubleClicked.connect(self.rename_user)
        
        add_ip_btn = QPushButton("+ Добавить по IP")
        add_ip_btn.clicked.connect(self.add_user_by_ip)
        
        left_panel.addWidget(QLabel("Контакты и Чат:"))
        left_panel.addWidget(self.user_list)
        left_panel.addWidget(add_ip_btn)

        # Правая панель — область чата
        right_panel = QVBoxLayout()
        
        self.chat_history = QListWidget()
        self.chat_history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_history.customContextMenuRequested.connect(self.open_message_menu)
        
        # Поле ввода
        input_layout = QHBoxLayout()
        self.msg_input = QTextEdit()
        self.msg_input.setMaximumHeight(80)
        
        send_btn = QPushButton("Отправить")
        send_btn.clicked.connect(self.send_message)
        
        file_btn = QPushButton("📎 Файл")
        file_btn.clicked.connect(self.send_file)

        input_layout.addWidget(self.msg_input)
        input_layout.addWidget(file_btn)
        input_layout.addWidget(send_btn)

        right_panel.addWidget(self.chat_history)
        right_panel.addLayout(input_layout)

        # Добавляем в основной layout с пропорциями
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 3)

        # Подключение к серверу
        self.network = NetworkWorker("127.0.0.1")  # Укажите IP сервера
        self.network.message_received.connect(self.on_message_received)
        self.network.start()

    # Всплывающее меню для редактирования, удаления и реакций
    def open_message_menu(self, position):
        item = self.chat_history.itemAt(position)
        if not item:
            return
            
        menu = QMenu()
        edit_action = menu.addAction("✏️ Редактировать")
        delete_action = menu.addAction("🗑️ Удалить для всех")
        react_action = menu.addAction("👍 Поставить реакцию")
        
        action = menu.exec_(self.chat_history.mapToGlobal(position))
        
        if action == edit_action:
            new_text, ok = QInputDialog.getText(self, "Редактирование", "Новый текст:")
            if ok:
                item.setText(f"[Изменено] {new_text}")
                # Отправка команды на сервер...
        elif action == delete_action:
            row = self.chat_history.row(item)
            self.chat_history.takeItem(row)
            # Отправка команды удаления на сервер...

    def add_user_by_ip(self):
        ip, ok = QInputDialog.getText(self, "Добавить IP", "Введите IP адрес устройства:")
        if ok and ip:
            item = QListWidgetItem(f"🔴 {ip} (Отошёл)")
            item.setData(Qt.UserRole, ip)
            self.user_list.addItem(item)

    def rename_user(self, item):
        ip = item.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(self, "Переименовать", "Введите имя/заметку:")
        if ok and new_name:
            self.custom_names[ip] = new_name
            item.setText(f"🟢 {new_name} [{ip}]")

    def send_message(self):
        text = self.msg_input.toPlainText()
        if text.strip():
            msg_data = {
                "type": "chat_msg",
                "content": text,
                "target": "all"
            }
            self.network.send(msg_data)
            self.chat_history.addItem(f"Вы: {text}")
            self.msg_input.clear()

    def send_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл (до 100МБ)")
        if file_path:
            # Логика бинарной передачи файла кусочками по TCP
            pass

    def on_message_received(self, data):
        msg_type = data.get("type")
        if msg_type == "status_update":
            ip = data["ip"]
            status = "🟢 В сети" if data["status"] == "online" else "🔴 Отошёл"
            name = self.custom_names.get(ip, ip)
            
            # Обновляем статус в списке
            for i in range(self.user_list.count()):
                item = self.user_list.item(i)
                if item.data(Qt.UserRole) == ip:
                    item.setText(f"{status} - {name}")
                    
        elif msg_type == "chat_msg":
            sender = self.custom_names.get(data["sender"], data["sender"])
            self.chat_history.addItem(f"{sender}: {data['content']}")

if __name__ == "__main__":

