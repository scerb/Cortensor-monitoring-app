import time
import subprocess
import json
import sys
from miner_manager import MinerManager

class DataFetcher:
    def __init__(self, config_manager, alert_manager):
        self.config_manager = config_manager
        self.alert_manager = alert_manager
        self.rpc_call_count = 0
        self.last_update_time = time.time()
        self.cached_stats = []
        self._initialized = False

    def fetch_data(self):
        self.rpc_call_count += 1

        # Clear session-level alerts at the start of each fetch
        self.alert_manager.session_alerts_sent.clear()

        try:
            subprocess.run(["python", "corbot3.py"], check=True)
            with open("stats.json", "r") as f:
                stats = json.load(f)
        except Exception as e:
            print(f"Failed to update or load stats: {e}")
            stats = {}

        stats_list = []
        alert_settings = self.config_manager.get_alert_settings()
        offline_threshold_sec = alert_settings.get("miner_offline_minutes", 5) * 60
        known_miners = MinerManager.load_miners()
        current_time = time.time()

        for miner_id in known_miners:
            if miner_id not in stats:
                self.alert_manager.check_miner_status(miner_id, True, current_time)
                continue

            miner_data = stats.get(miner_id, {})
            last_active_ts = miner_data.get("last_active_timestamp", 0)
            seconds_ago = current_time - last_active_ts if last_active_ts else float('inf')
            is_offline = seconds_ago > offline_threshold_sec

            self.alert_manager.check_miner_status(miner_id, is_offline, current_time)

            if self._initialized:
                eth_balance = miner_data.get("eth_balance", 0.0)
                self.alert_manager.check_balance_alerts(miner_id, eth_balance)

            stats_list.append({
                "miner_id": miner_id,
                "ping": miner_data.get("ping", 0),
                "precommit": miner_data.get("precommit", {}),
                "commit": miner_data.get("commit", {}),
                "prepare": miner_data.get("prepare", {}),
                "create": miner_data.get("create", {}),
                "last_active": miner_data.get("last_active", "Unknown"),
                "eth_balance": miner_data.get("eth_balance", 0.0),
                "is_offline": is_offline
            })

        self.cached_stats = stats_list
        self.last_update_time = current_time
        self._initialized = True

        return stats_list, self.alert_manager.get_session_alerts()
