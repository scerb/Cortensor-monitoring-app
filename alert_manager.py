import requests
import json
import os
import logging
from PyQt5.QtWidgets import QMessageBox

# Enable debug logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class AlertManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.alert_settings = config_manager.get_alert_settings()

        self.sent_alerts_file = "sent_alerts.json"
        self.status_file = "miner_status.json"

        self.persistent_alerts = self._load_json_set(self.sent_alerts_file)
        self.miner_status = self._load_json_dict(self.status_file)

        self.status_changes = {}
        self.session_alerts_sent = set()

    def _load_json_set(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return set(json.load(f))
            except Exception as e:
                logging.warning(f"Failed to load {path}: {e}")
        return set()

    def _load_json_dict(self, path):
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logging.warning(f"Failed to load {path}: {e}")
        return {}

    def _save_json_set(self, path, data_set):
        try:
            with open(path, "w") as f:
                json.dump(list(data_set), f)
        except Exception as e:
            logging.error(f"Failed to save {path}: {e}")

    def _save_json_dict(self, path, data_dict):
        try:
            with open(path, "w") as f:
                json.dump(data_dict, f)
        except Exception as e:
            logging.error(f"Failed to save {path}: {e}")

    def send_telegram_alert(self, message, skip_duplicate_check=False):
        if not self.alert_settings.get("telegram_enabled", False):
            logging.info("Telegram alerts are disabled.")
            return False

        bot_token = self.alert_settings.get("bot_token", "").strip()
        chat_id = self.alert_settings.get("chat_id", "").strip()

        if not bot_token or not chat_id:
            logging.warning("Telegram bot token or chat ID is missing.")
            return False

        if not skip_duplicate_check:
            self.persistent_alerts = self._load_json_set(self.sent_alerts_file)
            if message in self.persistent_alerts:
                logging.info(f"Skipping duplicate alert: {message}")
                return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {'chat_id': chat_id, 'text': message}

        try:
            response = requests.get(url, params=params, timeout=5)
            logging.debug(f"Telegram response status: {response.status_code}")
            logging.debug(f"Telegram response text: {response.text}")

            if response.status_code == 200:
                logging.info(f"Telegram alert sent: {message}")
                self.session_alerts_sent.add(message)
                if not skip_duplicate_check:
                    self.persistent_alerts.add(message)
                    self._save_json_set(self.sent_alerts_file, self.persistent_alerts)
                return True
            else:
                logging.error(f"Telegram API error {response.status_code}: {response.text}")
                return False
        except Exception as e:
            logging.exception(f"Exception sending Telegram alert: {e}")
            return False

    def _send_raw_telegram_message(self, message):
        if not self.alert_settings.get("telegram_enabled", False):
            logging.debug("Telegram disabled in settings.")
            return False

        bot_token = self.alert_settings.get("bot_token", "").strip()
        chat_id = self.alert_settings.get("chat_id", "").strip()

        if not bot_token or not chat_id:
            logging.warning("Bot token or chat ID missing.")
            return False

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        params = {'chat_id': chat_id, 'text': message}

        try:
            response = requests.get(url, params=params, timeout=5)
            logging.debug(f"Raw Telegram response status: {response.status_code}")
            logging.debug(f"Raw Telegram response text: {response.text}")
            return response.status_code == 200
        except Exception as e:
            logging.error(f"Error sending test message: {e}")
            return False

    def test_telegram(self, parent):
        success = self._send_raw_telegram_message("Test alert from ETH Miner Dashboard")
        if success:
            QMessageBox.information(parent, "Success", "Test message sent successfully!")
        else:
            QMessageBox.warning(parent, "Error", "Failed to send test message. Check your bot token, chat ID, or network connection.")

    def check_miner_status(self, miner_id, is_offline, current_time):
        current_status = "offline" if is_offline else "online"
        previous_status = self.miner_status.get(miner_id)

        logging.debug(f"Miner {miner_id[:6]}... current={current_status}, previous={previous_status}")

        if previous_status is None:
            self.miner_status[miner_id] = current_status
            self._save_json_dict(self.status_file, self.miner_status)
            return None

        if previous_status != current_status:
            self.miner_status[miner_id] = current_status
            self._save_json_dict(self.status_file, self.miner_status)

            if is_offline:
                alert_msg = f"🚨 Miner OFFLINE: {miner_id[:6]}...{miner_id[-4:]}"
            else:
                alert_msg = f"✅ Miner BACK ONLINE: {miner_id[:6]}...{miner_id[-4:]}"
            self.send_telegram_alert(alert_msg)
            return alert_msg

        return None

    def check_balance_alerts(self, miner_id, eth_balance):
        critical_threshold = self.alert_settings.get("critical_balance_alert", 0.1)
        low_threshold = self.alert_settings.get("low_balance_alert", 0.5)

        msg_prefix = f"Miner {miner_id[:6]}..."

        if eth_balance < critical_threshold:
            alert_msg = f"CRITICAL: {msg_prefix} balance {eth_balance} ETH"
            self.send_telegram_alert(alert_msg)
            return alert_msg

        elif eth_balance < low_threshold:
            alert_msg = f"WARNING: {msg_prefix} balance {eth_balance} ETH"
            self.send_telegram_alert(alert_msg)
            return alert_msg

        return None

    def get_session_alerts(self):
        return list(self.session_alerts_sent)

    def clear_all_alerts(self):
        self.persistent_alerts.clear()
        self._save_json_set(self.sent_alerts_file, self.persistent_alerts)
        logging.info("All persistent alerts cleared.")

        self.miner_status.clear()
        self._save_json_dict(self.status_file, self.miner_status)
        logging.info("Miner status history cleared.")
