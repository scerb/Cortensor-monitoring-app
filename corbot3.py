import sys
import json
import threading
from datetime import datetime
import requests
from web3 import Web3

# Global RPC call counter
rpc_call_count = 0

# Connect to Arbitrum Sepolia RPC
web3 = Web3(Web3.HTTPProvider("https://sepolia-rollup.arbitrum.io/rpc"))
if not web3.is_connected():
    print("Failed to connect to Arbitrum Sepolia RPC")
else:
    print("Connected to Arbitrum Sepolia RPC")

def load_miners():
    try:
        with open("miners.json", "r") as f:
            data = json.load(f)
            if isinstance(data, list):  # Old format: just a list
                corrected = {"miners": data}
                save_miners(data)  # Save in new format
                print("Converted old miners.json format to new format.")
                return data
            elif isinstance(data, dict) and "miners" in data:
                return data["miners"]
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return []

def save_miners(miners):
    with open("miners.json", "w") as f:
        json.dump({"miners": miners}, f, indent=4)

def fetch_all_miner_data():
    try:
        resp = requests.get("https://lb-be-4.cortensor.network/leaderboard")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print("Fetch error:", e)
    return []

def is_valid_eth_address(addr):
    return addr.startswith("0x") and len(addr) == 42 and web3.is_address(addr)

def convert_last_active(timestamp):
    if not timestamp:
        return "Unknown"
    now = datetime.now()
    last_time = datetime.fromtimestamp(timestamp)
    delta = now - last_time
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds} sec ago"
    elif seconds < 3600:
        return f"{seconds // 60} min {seconds % 60} sec ago"
    elif seconds < 86400:
        return f"{seconds // 3600} hr {(seconds % 3600) // 60} min ago"
    else:
        return f"{seconds // 86400} days ago"

def fetch_balances(miner_ids):
    balances = {}

    def get_balance(miner_id):
        global rpc_call_count
        try:
            if not is_valid_eth_address(miner_id):
                return
            balance_wei = web3.eth.get_balance(miner_id)
            rpc_call_count += 1  # Count the RPC call
            balance_eth = web3.from_wei(balance_wei, 'ether')
            balances[miner_id] = float(round(balance_eth, 4))
        except Exception as e:
            print(f"Balance error for {miner_id}:", e)

    threads = []
    for m in miner_ids:
        t = threading.Thread(target=get_balance, args=(m,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return balances

def collect_stats():
    miners = load_miners()
    raw_data = fetch_all_miner_data()
    data = [m for m in raw_data if m.get("miner") in miners]
    balances = fetch_balances(miners)

    stats = {}
    for miner in data:
        full_id = miner.get("miner", "")
        last_active_ts = miner.get("last_active", 0)

        stats[full_id] = {
            "ping": miner.get("ping_counter", 0),
            "precommit": {
                "point": miner.get("precommitPoint", 0),
                "counter": miner.get("precommitCounter", 1)
            },
            "commit": {
                "point": miner.get("commitPoint", 0),
                "counter": miner.get("commitCounter", 1)
            },
            "prepare": {
                "point": miner.get("preparePoint", 0),
                "counter": miner.get("prepareCounter", 1)
            },
            "create": {
                "point": miner.get("createPoint", 0),
                "counter": miner.get("createCounter", 1)
            },
            "last_active": convert_last_active(last_active_ts),
            "last_active_timestamp": last_active_ts,
            "eth_balance": balances.get(full_id, 'N/A')
        }

    # Add RPC call metadata
    stats["__rpc_meta__"] = {
        "rpc_call_count": rpc_call_count,
        "timestamp": int(datetime.now().timestamp())
    }

    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=4)

if __name__ == '__main__':
    collect_stats()
    print("Stats written to stats.json")
