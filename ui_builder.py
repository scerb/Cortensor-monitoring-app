from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QLabel, QTabWidget, QLineEdit, 
    QPushButton, QHBoxLayout, QSpinBox, QHeaderView, QGroupBox, 
    QFormLayout, QCheckBox, QTextEdit
)
from PyQt5.QtGui import QMovie
from stats_bot_tab import StatsBotTab  # <-- Add this import

class UIBuilder:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        
    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        table = QTableWidget()
        layout.addWidget(table)

        rpc_label = QLabel("RPC Calls: 0")
        last_update_label = QLabel("Last Update: --")
        next_update_label = QLabel("Next Update In: --")
        refresh_animation = QLabel()
        refresh_movie = QMovie("refresh.gif")
        refresh_animation.setMovie(refresh_movie)
        refresh_animation.setVisible(False)

        refresh_button = QPushButton("Refresh")

        info_layout = QHBoxLayout()
        info_layout.addWidget(rpc_label)
        info_layout.addStretch()
        info_layout.addWidget(last_update_label)
        info_layout.addWidget(next_update_label)
        info_layout.addWidget(refresh_button)
        info_layout.addWidget(refresh_animation)

        layout.addLayout(info_layout)
        tab.setLayout(layout)
        
        return {
            "tab": tab,
            "table": table,
            "rpc_label": rpc_label,
            "last_update_label": last_update_label,
            "next_update_label": next_update_label,
            "refresh_animation": refresh_animation,
            "refresh_movie": refresh_movie,
            "refresh_button": refresh_button
        }

    def create_miner_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        miner_input = QLineEdit()
        miner_input.setPlaceholderText("Enter Miner Address")
        add_button = QPushButton("Add Miner")
        remove_button = QPushButton("Remove Miner")

        layout.addWidget(QLabel("Manage Miners:"))
        layout.addWidget(miner_input)
        layout.addWidget(add_button)
        layout.addWidget(remove_button)

        tab.setLayout(layout)
        
        return {
            "tab": tab,
            "miner_input": miner_input,
            "add_button": add_button,
            "remove_button": remove_button
        }

    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        freq_row = QHBoxLayout()
        freq_row.addWidget(QLabel("Update Frequency (seconds):"))
        
        freq_input = QSpinBox()
        freq_input.setMinimum(10)
        freq_input.setMaximum(3600)
        freq_input.setMaximumWidth(80)
        freq_input.setValue(self.config_manager.config.get("update_frequency", 600))
        
        save_freq_button = QPushButton("Save")
        
        freq_row.addWidget(freq_input)
        freq_row.addWidget(save_freq_button)
        freq_row.addStretch()

        thresholds_row = QHBoxLayout()
        thresholds_row.addWidget(QLabel("ETH Balance Thresholds: Low:"))
        
        eth_low_input = QLineEdit(str(self.config_manager.config.get("eth_balance_low", 1.5)))
        eth_low_input.setMaximumWidth(60)
        thresholds_row.addWidget(eth_low_input)
        
        thresholds_row.addWidget(QLabel("Mid:"))
        eth_mid_input = QLineEdit(str(self.config_manager.config.get("eth_balance_mid", 3.0)))
        eth_mid_input.setMaximumWidth(60)
        thresholds_row.addWidget(eth_mid_input)
        
        save_settings_button = QPushButton("Save Thresholds")
        thresholds_row.addWidget(save_settings_button)
        thresholds_row.addStretch()

        layout.addLayout(freq_row)
        layout.addLayout(thresholds_row)
        tab.setLayout(layout)
        
        return {
            "tab": tab,
            "freq_input": freq_input,
            "save_freq_button": save_freq_button,
            "eth_low_input": eth_low_input,
            "eth_mid_input": eth_mid_input,
            "save_settings_button": save_settings_button
        }

    def create_alert_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()

        alert_settings = self.config_manager.get_alert_settings()
        
        telegram_group = QGroupBox("Telegram Alert Settings")
        telegram_layout = QFormLayout()
        
        telegram_checkbox = QCheckBox("Enable Telegram Alerts")
        bot_token_input = QLineEdit()
        bot_token_input.setPlaceholderText("Your bot token")
        chat_id_input = QLineEdit()
        chat_id_input.setPlaceholderText("Your chat ID")
        
        telegram_layout.addRow(telegram_checkbox)
        telegram_layout.addRow("Bot Token:", bot_token_input)
        telegram_layout.addRow("Chat ID:", chat_id_input)
        telegram_group.setLayout(telegram_layout)

        threshold_group = QGroupBox("Alert Thresholds")
        threshold_layout = QFormLayout()
        
        low_balance_input = QLineEdit(str(alert_settings.get("low_balance_alert", 0.5)))
        critical_balance_input = QLineEdit(str(alert_settings.get("critical_balance_alert", 0.1)))
        miner_offline_input = QSpinBox()
        miner_offline_input.setMinimum(1)
        miner_offline_input.setMaximum(60)
        miner_offline_input.setValue(alert_settings.get("miner_offline_minutes", 10))
        
        threshold_layout.addRow("Low Balance (ETH):", low_balance_input)
        threshold_layout.addRow("Critical Balance (ETH):", critical_balance_input)
        threshold_layout.addRow("Miner Offline (minutes):", miner_offline_input)
        threshold_group.setLayout(threshold_layout)

        history_group = QGroupBox("Alert History")
        history_layout = QVBoxLayout()
        alert_history = QTextEdit()
        alert_history.setReadOnly(True)
        history_layout.addWidget(alert_history)
        history_group.setLayout(history_layout)

        button_layout = QHBoxLayout()
        test_button = QPushButton("Test Telegram")
        save_button = QPushButton("Save Alert Settings")
        button_layout.addWidget(test_button)
        button_layout.addWidget(save_button)

        telegram_checkbox.setChecked(alert_settings.get("telegram_enabled", False))
        bot_token_input.setText(alert_settings.get("bot_token", ""))
        chat_id_input.setText(alert_settings.get("chat_id", ""))

        layout.addWidget(telegram_group)
        layout.addWidget(threshold_group)
        layout.addWidget(history_group)
        layout.addLayout(button_layout)

        tab.setLayout(layout)
        
        return {
            "tab": tab,
            "layout": layout,
            "telegram_checkbox": telegram_checkbox,
            "bot_token_input": bot_token_input,
            "chat_id_input": chat_id_input,
            "low_balance_input": low_balance_input,
            "critical_balance_input": critical_balance_input,
            "miner_offline_input": miner_offline_input,
            "alert_history": alert_history,
            "test_button": test_button,
            "save_button": save_button
        }

    def create_stats_bot_tab(self):
        return StatsBotTab(self.config_manager)  # <-- New method for stats bot tab
