
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QLabel,
    QSpinBox, QPushButton, QHBoxLayout, QGroupBox, QMessageBox
)
from PyQt5.QtCore import QTimer, Qt
import json
import time
import threading
import logging
import os
from alert_manager import AlertManager


class StatsBotTab(QWidget):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.alert_manager = AlertManager(self.config_manager)

        self.stats_keys = [
            "ping", "precommit", "commit", "prepare", "create", "eth_balance"
        ]

        self.metric_abbreviations = {
            "precommit": "PC",
            "commit": "CO",
            "prepare": "PP",
            "create": "CR",
            "eth_balance": "eth",
            "ping": "ping"
        }

        self.timer = QTimer()
        self.timer.timeout.connect(self.send_stats_to_telegram)

        self.init_ui()
        self.restore_settings()

        if self.enable_checkbox.isChecked():
            self.start_timer()

    def init_ui(self):
        layout = QVBoxLayout()

        self.checkboxes = {}
        group = QGroupBox("Select metrics to send:")
        group_layout = QVBoxLayout()
        for key in self.stats_keys:
            cb = QCheckBox(key)
            group_layout.addWidget(cb)
            self.checkboxes[key] = cb
        group.setLayout(group_layout)
        layout.addWidget(group)

        self.include_header_checkbox = QCheckBox("Include miner address header")
        layout.addWidget(self.include_header_checkbox)

        self.include_timestamp_checkbox = QCheckBox("Include timestamp at top of message")
        layout.addWidget(self.include_timestamp_checkbox)

        self.compare_checkbox = QCheckBox("Compare over time")
        layout.addWidget(self.compare_checkbox)

        freq_layout = QHBoxLayout()
        freq_label = QLabel("Send Interval (hours):")
        self.freq_input = QSpinBox()
        self.freq_input.setMinimum(1)
        self.freq_input.setMaximum(24)
        self.freq_input.valueChanged.connect(self.update_timer_interval)

        self.next_send_label = QLabel("Next send: N/A")
        freq_layout.addWidget(freq_label)
        freq_layout.addWidget(self.freq_input)
        freq_layout.addWidget(self.next_send_label)
        layout.addLayout(freq_layout)

        self.enable_checkbox = QCheckBox("Enable Stats Bot")
        self.enable_checkbox.stateChanged.connect(self.toggle_timer)
        layout.addWidget(self.enable_checkbox)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save Settings")
        self.send_now_button = QPushButton("Send Now")
        self.save_button.clicked.connect(self.save_settings)
        self.send_now_button.clicked.connect(self.send_stats_to_telegram)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.send_now_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_timer_interval(self):
        if self.timer.isActive():
            self.start_timer()

    def toggle_timer(self):
        if self.enable_checkbox.isChecked():
            self.start_timer()
        else:
            self.timer.stop()
            self.next_send_label.setText("Next send: N/A")

    def start_timer(self):
        interval_hours = self.freq_input.value()
        interval_ms = interval_hours * 3600 * 1000
        self.timer.start(interval_ms)
        self.update_next_send_label(interval_ms)

    def update_next_send_label(self, interval_ms):
        next_time = time.time() + (interval_ms / 1000)
        next_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(next_time))
        self.next_send_label.setText(f"Next send: {next_str}")

    def get_selected_metrics(self):
        return [k for k, cb in self.checkboxes.items() if cb.isChecked()]

    def set_selected_metrics(self, metrics):
        for key, cb in self.checkboxes.items():
            cb.setChecked(key in metrics)

    def save_settings(self):
        settings = {
            "enabled": self.enable_checkbox.isChecked(),
            "interval_hours": self.freq_input.value(),
            "metrics": self.get_selected_metrics(),
            "include_header": self.include_header_checkbox.isChecked(),
            "include_timestamp": self.include_timestamp_checkbox.isChecked(),
            "compare_over_time": self.compare_checkbox.isChecked()
        }
        self.config_manager.set("stats_bot", settings)
        self.config_manager.save_config()
        self.show_message("Stats Bot", "Settings saved.")
        if settings["enabled"]:
            self.start_timer()

    def restore_settings(self):
        settings = self.config_manager.get("stats_bot", {})
        self.set_selected_metrics(settings.get("metrics", []))
        self.include_header_checkbox.setChecked(settings.get("include_header", True))
        self.include_timestamp_checkbox.setChecked(settings.get("include_timestamp", False))
        self.compare_checkbox.setChecked(settings.get("compare_over_time", False))
        self.freq_input.setValue(settings.get("interval_hours", 1))
        self.enable_checkbox.setChecked(settings.get("enabled", False))

    def show_message(self, title, message, icon=QMessageBox.Information):
        QTimer.singleShot(0, lambda: QMessageBox(icon, title, message, parent=self).exec_())

    def send_stats_to_telegram(self):
        selected_keys = self.get_selected_metrics()
        compare_enabled = self.compare_checkbox.isChecked()

        if not selected_keys:
            self.show_message("Stats Bot", "No metrics selected.", QMessageBox.Warning)
            return

        try:
            with open("stats.json", "r") as f:
                stats = json.load(f)
        except Exception as e:
            self.show_message("Stats Bot", "Failed to read stats.json.", QMessageBox.Critical)
            return

        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {"timestamp": timestamp, "data": stats}
        bot_stats = []

        if os.path.exists("bot_stats.json"):
            try:
                with open("bot_stats.json", "r") as f:
                    bot_stats = json.load(f)
            except:
                bot_stats = []

        bot_stats.append(entry)
        try:
            with open("bot_stats.json", "w") as f:
                json.dump(bot_stats, f, indent=2)
        except:
            pass

        previous_data = bot_stats[-2]["data"] if compare_enabled and len(bot_stats) >= 2 else {}

        lines = []

        if self.include_timestamp_checkbox.isChecked():
            lines.append(f"📅 {timestamp}")

        for addr, data in stats.items():
            if addr == "__rpc_meta__" or not isinstance(data, dict):
                continue

            line = []
            if self.include_header_checkbox.isChecked():
                line.append(f"...{addr[-5:]}:")

            for key in selected_keys:
                val = data.get(key, "N/A")
                label = self.metric_abbreviations.get(key, key)

                val_str = str(val)
                delta_str = ""

                if isinstance(val, dict):
                    point = val.get("point", 0)
                    counter = val.get("counter", 1)
                    percent = round((point / counter) * 100, 1) if counter else 0.0
                    val_str = f"{point}/{counter} ({percent}%)"

                    if compare_enabled:
                        prev_val = previous_data.get(addr, {}).get(key, {})
                        prev_point = prev_val.get("point", 0)
                        prev_counter = prev_val.get("counter", 1)
                        prev_percent = round((prev_point / prev_counter) * 100, 1) if prev_counter else 0.0
                        diff = round(percent - prev_percent, 1)
                        delta_str = f" 🟢▲{diff}%" if diff > 0 else f" 🔴▼{abs(diff)}%" if diff < 0 else " ➖0.0%"

                elif isinstance(val, (int, float)) and compare_enabled:
                    prev_val = previous_data.get(addr, {}).get(key)
                    if isinstance(prev_val, (int, float)):
                        diff = round(val - prev_val, 1)
                        delta_str = f" 🟢▲{diff}" if diff > 0 else f" 🔴▼{abs(diff)}" if diff < 0 else " ➖0.0"

                line.append(f"{label}: {val_str}{delta_str}")

            if line:
                lines.append(" | ".join(line))

        message = "\n\n".join(lines) if lines else "Stats Bot Test: No real data matched. Test message."

        def send():
            try:
                self.alert_manager.alert_settings = self.alert_manager.config_manager.get_alert_settings()
                print("DEBUG alert_settings:", self.alert_manager.alert_settings)                
                self.alert_manager.send_telegram_alert(message, skip_duplicate_check=True)
                self.show_message("Stats Bot", "Message sent successfully.")
                if self.timer.isActive():
                    self.update_next_send_label(self.freq_input.value() * 3600 * 1000)
            except Exception as e:
                self.show_message("Stats Bot", f"Failed to send message: {e}", QMessageBox.Critical)

        threading.Thread(target=send, daemon=True).start()
