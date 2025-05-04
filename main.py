import sys
import time
import json
import corbot3
from PyQt5.QtWidgets import (
    QApplication, QWidget, QHeaderView, QVBoxLayout,
    QTabWidget, QMessageBox, QPushButton
)
from PyQt5.QtCore import Qt, QTimer
from config_manager import ConfigManager
from alert_manager import AlertManager
from miner_manager import MinerManager
from data_fetcher import DataFetcher
from table_renderer import TableRenderer
from ui_builder import UIBuilder
from stats_bot_tab import StatsBotTab


class Dashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETH Miner Dashboard")
        self.setGeometry(100, 100, 1300, 900)

        self.config_manager = ConfigManager()
        self.alert_manager = AlertManager(self.config_manager)
        self.miner_manager = MinerManager()
        self.data_fetcher = DataFetcher(self.config_manager, self.alert_manager)
        self.table_renderer = TableRenderer(self.config_manager)
        self.ui = UIBuilder(self.config_manager)

        self.tabs = QTabWidget()

        self.dashboard_ui = self.ui.create_dashboard_tab()
        self.miner_ui = self.ui.create_miner_tab()
        self.settings_ui = self.ui.create_settings_tab()
        self.alert_ui = self.ui.create_alert_tab()
        self.stats_bot_ui = StatsBotTab(self.config_manager)

        self.tabs.addTab(self.dashboard_ui["tab"], "Main Display")
        self.tabs.addTab(self.miner_ui["tab"], "Add/Remove Miner")
        self.tabs.addTab(self.settings_ui["tab"], "Settings")
        self.tabs.addTab(self.alert_ui["tab"], "Alert Bot")
        self.tabs.addTab(self.stats_bot_ui, "Stats Bot")

        self._add_clear_alerts_button()
        self._setup_connections()

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_countdown)
        self.update_timer.start(1000)

        self.stats_bot_timer = QTimer(self)
        self.stats_bot_timer.timeout.connect(self.run_stats_bot)
        self.update_stats_bot_timer()

        self.load_data()
        self.load_stats_bot_config()

    def _setup_connections(self):
        self.dashboard_ui["refresh_button"].clicked.connect(self.load_data)
        self.dashboard_ui["table"].horizontalHeader().sectionClicked.connect(self.handle_header_click)
        self.dashboard_ui["table"].horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.miner_ui["add_button"].clicked.connect(self.add_miner)
        self.miner_ui["remove_button"].clicked.connect(self.remove_miner)

        self.settings_ui["save_freq_button"].clicked.connect(self.on_save_frequency)
        self.settings_ui["save_settings_button"].clicked.connect(self.on_save_settings)

        self.alert_ui["test_button"].clicked.connect(self.test_telegram)
        self.alert_ui["save_button"].clicked.connect(self.save_alert_settings)

        self.stats_bot_ui.enable_checkbox.stateChanged.connect(self.update_stats_bot_timer)
        self.stats_bot_ui.freq_input.setMinimum(1)
        self.stats_bot_ui.freq_input.setMaximum(24)
        self.stats_bot_ui.freq_input.valueChanged.connect(self.update_stats_bot_timer)
        self.stats_bot_ui.save_button.clicked.connect(self.save_stats_bot_config)

    def _add_clear_alerts_button(self):
        clear_alerts_button = QPushButton("Clear Sent Alerts")
        clear_alerts_button.clicked.connect(self.clear_alerts)

        alert_tab_layout = self.alert_ui["tab"].layout()
        if alert_tab_layout:
            alert_tab_layout.addWidget(clear_alerts_button)

    def handle_header_click(self, index):
        self.table_renderer.handle_header_click(index, self.dashboard_ui["table"])
        self.render_table()

    def load_data(self):
        stats, alerts = self.data_fetcher.fetch_data()
        if stats:
            for alert_msg in alerts:
                self.alert_ui["alert_history"].append(
                    f"[{time.strftime('%H:%M:%S')}] {alert_msg}"
                )

        self.dashboard_ui["rpc_label"].setText(f"RPC Calls: {self.data_fetcher.rpc_call_count}")
        self.dashboard_ui["last_update_label"].setText(f"Last Update: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.dashboard_ui["refresh_movie"].stop()
        self.dashboard_ui["refresh_animation"].setVisible(False)
        self.render_table()

    def render_table(self):
        self.table_renderer.render_table(self.dashboard_ui["table"], self.data_fetcher.cached_stats)

    def update_countdown(self):
        update_freq = self.settings_ui["freq_input"].value()
        elapsed = time.time() - self.data_fetcher.last_update_time
        remaining = max(0, int(update_freq - elapsed))
        self.dashboard_ui["next_update_label"].setText(f"Next Update In: {remaining}s")

        if remaining <= 0:
            self.load_data()

    def update_stats_bot_timer(self):
        interval = self.stats_bot_ui.freq_input.value() * 3600
        if self.stats_bot_ui.enable_checkbox.isChecked():
            self.stats_bot_timer.start(interval * 1000)
        else:
            self.stats_bot_timer.stop()

    def run_stats_bot(self):
        if not self.stats_bot_ui.enable_checkbox.isChecked():
            return
        self.stats_bot_ui.send_stats_to_telegram()

    def save_stats_bot_config(self):
        config = {
            "enabled": self.stats_bot_ui.enable_checkbox.isChecked(),
            "interval": self.stats_bot_ui.freq_input.value(),
            "metrics": self.stats_bot_ui.get_selected_metrics(),
            "include_header": self.stats_bot_ui.include_header_checkbox.isChecked(),
            "include_timestamp": self.stats_bot_ui.include_timestamp_checkbox.isChecked(),
            "compare_over_time": self.stats_bot_ui.compare_checkbox.isChecked()
        }
        self.config_manager.config["stats_bot"] = config
        self.config_manager.save_config()
        QMessageBox.information(self, "Saved", "Stats Bot settings saved.")

    def load_stats_bot_config(self):
        config = self.config_manager.config.get("stats_bot", {})
        self.stats_bot_ui.enable_checkbox.setChecked(config.get("enabled", False))
        self.stats_bot_ui.freq_input.setValue(config.get("interval", 1))
        self.stats_bot_ui.set_selected_metrics(config.get("metrics", []))
        self.stats_bot_ui.include_header_checkbox.setChecked(config.get("include_header", True))
        self.stats_bot_ui.include_timestamp_checkbox.setChecked(config.get("include_timestamp", True))
        self.stats_bot_ui.compare_checkbox.setChecked(config.get("compare_over_time", False))
        self.update_stats_bot_timer()

    def on_save_frequency(self):
        try:
            self.config_manager.save_balance_thresholds(
                float(self.settings_ui["eth_low_input"].text()),
                float(self.settings_ui["eth_mid_input"].text())
            )
            QMessageBox.information(self, "Saved", "Update frequency saved successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save frequency: {e}")

    def on_save_settings(self):
        try:
            self.config_manager.save_balance_thresholds(
                float(self.settings_ui["eth_low_input"].text()),
                float(self.settings_ui["eth_mid_input"].text())
            )
            QMessageBox.information(self, "Saved", "Thresholds saved successfully.")
            self.load_data()
        except ValueError:
            QMessageBox.warning(self, "Error", "Please enter valid numbers for thresholds.")

    def add_miner(self):
        miner = self.miner_ui["miner_input"].text().strip()
        if self.miner_manager.add_miner(miner, self):
            self.miner_ui["miner_input"].clear()
            self.load_data()

    def remove_miner(self):
        miner = self.miner_ui["miner_input"].text().strip()
        if self.miner_manager.remove_miner(miner, self):
            self.miner_ui["miner_input"].clear()
            self.load_data()

    def test_telegram(self):
        self.alert_manager.test_telegram(self)

    def save_alert_settings(self):
        alert_settings = {
            "telegram_enabled": self.alert_ui["telegram_checkbox"].isChecked(),
            "bot_token": self.alert_ui["bot_token_input"].text(),
            "chat_id": self.alert_ui["chat_id_input"].text(),
            "low_balance_alert": float(self.alert_ui["low_balance_input"].text()),
            "critical_balance_alert": float(self.alert_ui["critical_balance_input"].text()),
            "miner_offline_minutes": self.alert_ui["miner_offline_input"].value()
        }
        self.config_manager.save_alert_settings(alert_settings)
        QMessageBox.information(self, "Saved", "Alert settings saved successfully.")
        self.alert_ui["alert_history"].append(f"[{time.strftime('%H:%M:%S')}] Alert settings updated")
        self.alert_manager = AlertManager(self.config_manager)

    def clear_alerts(self):
        reply = QMessageBox.question(
            self,
            "Clear Alerts",
            "Are you sure you want to clear all sent alert history?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                with open("sent_alerts.json", "w") as f:
                    json.dump([], f)
                QMessageBox.information(self, "Alerts Cleared", "All persistent alerts have been cleared.")
                self.alert_ui["alert_history"].append(f"[{time.strftime('%H:%M:%S')}] Alerts cleared manually")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to clear alerts:\n{str(e)}")

    def closeEvent(self, event):
        column_widths = {}
        table = self.dashboard_ui["table"]
        for i in range(table.columnCount()):
            column_widths[str(i)] = table.columnWidth(i)
        self.config_manager.save_column_widths(column_widths)
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Dashboard()
    window.show()
    sys.exit(app.exec_())
