from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
)
from PyQt5.QtCore import QCoreApplication
import os


class ServerForm(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filename = os.path.join(os.path.dirname(__file__), "server_list.txt")
        self.servers = []
        self.new_entry_mode = False
        self.init_ui()
        self.load_servers()

    def init_ui(self):
        layout = QVBoxLayout()

        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self.on_combo_changed)
        layout.addWidget(QLabel(self.tr("Select server to edit:")))
        layout.addWidget(self.combo)

        self.server = QLineEdit()
        self.layman_server = QLineEdit()
        self.client_id = QLineEdit()
        self.client_secret = QLineEdit()
        self.cfg_id = QLineEdit()
        self.alias = QLineEdit()

        layout.addWidget(QLabel(self.tr("Server")))
        layout.addWidget(self.server)
        layout.addWidget(QLabel(self.tr("Layman Server")))
        layout.addWidget(self.layman_server)
        layout.addWidget(QLabel(self.tr("Client ID")))
        layout.addWidget(self.client_id)
        layout.addWidget(QLabel(self.tr("Client Secret")))
        layout.addWidget(self.client_secret)
        layout.addWidget(QLabel(self.tr("Cfg ID")))
        layout.addWidget(self.cfg_id)
        layout.addWidget(QLabel(self.tr("Alias")))
        layout.addWidget(self.alias)

        self.add_button = QPushButton(self.tr("Add New"))
        self.add_button.clicked.connect(self.add_new)
        layout.addWidget(self.add_button)

        self.save_button = QPushButton(self.tr("Save"))
        self.save_button.clicked.connect(self.save_server)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def load_servers(self):
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if len(parts) == 6:
                        self.servers.append(parts)
                        self.combo.addItem(parts[-1])  # alias
        except FileNotFoundError:
            pass

    def on_combo_changed(self):
        if self.new_entry_mode:
            self.new_entry_mode = False
        self.fill_form()

    def fill_form(self):
        idx = self.combo.currentIndex()
        if idx >= 0 and idx < len(self.servers):
            data = self.servers[idx]
            self.server.setText(data[0])
            self.layman_server.setText(data[1])
            self.client_id.setText(data[2])
            self.client_secret.setText(data[3])
            self.cfg_id.setText(data[4])
            self.alias.setText(data[5])

    def add_new(self):
        self.server.clear()
        self.layman_server.clear()
        self.client_id.clear()
        self.client_secret.clear()
        self.cfg_id.clear()
        self.alias.clear()
        self.combo.setCurrentIndex(-1)
        self.new_entry_mode = True

    def save_server(self):
        if len(self.cfg_id.text()) != 7:
            QMessageBox.warning(
                self,
                self.tr("Invalid Cfg ID"),
                self.tr("Cfg ID must be exactly 7 characters long."),
            )
            return

        new_data = [
            self.server.text(),
            self.layman_server.text(),
            self.client_id.text(),
            self.client_secret.text(),
            self.cfg_id.text(),
            self.alias.text(),
        ]

        if self.new_entry_mode or self.combo.currentIndex() == -1:
            self.servers.append(new_data)
            self.combo.addItem(new_data[-1])
            self.combo.setCurrentIndex(self.combo.count() - 1)
            self.new_entry_mode = False
        else:
            idx = self.combo.currentIndex()
            if idx >= 0 and idx < len(self.servers):
                self.servers[idx] = new_data
                self.combo.setItemText(idx, new_data[-1])

        try:
            with open(self.filename, "w") as f:
                for server in self.servers:
                    f.write(",".join(server) + "\n")
            QMessageBox.information(
                self, self.tr("Saved"), self.tr("Server list saved successfully.")
            )
        except Exception as e:
            QMessageBox.critical(self, self.tr("Error"), str(e))
