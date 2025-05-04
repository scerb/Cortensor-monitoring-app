import json

CONFIG_FILE = "config.json"

class ConfigManager:
    def __init__(self):
        self.config = self.load_config()
        
    def load_config(self):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {
                "column_widths": {},
                "eth_balance_low": 1.5,
                "eth_balance_mid": 3.0,
                "alert_settings": {
                    "telegram_enabled": False,
                    "bot_token": "",
                    "chat_id": "",
                    "low_balance_alert": 0.5,
                    "critical_balance_alert": 0.1,
                    "miner_offline_minutes": 5
                }
            }

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def get_column_widths(self):
        return self.config.get("column_widths", {})

    def save_column_widths(self, widths):
        self.config["column_widths"] = widths
        self.save_config()

    def get_alert_settings(self):
        return self.config.get("alert_settings", {})

    def save_alert_settings(self, settings):
        self.config["alert_settings"] = settings
        self.save_config()

    def get_balance_thresholds(self):
        return {
            "eth_low": self.config.get("eth_balance_low", 1.5),
            "eth_mid": self.config.get("eth_balance_mid", 3.0)
        }

    def save_balance_thresholds(self, eth_low, eth_mid):
        self.config["eth_balance_low"] = eth_low
        self.config["eth_balance_mid"] = eth_mid
        self.save_config()

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()
