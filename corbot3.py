import sys
import json
import threading
import time
from datetime import datetime
import requests
from web3 import Web3

# Global RPC call counter
rpc_call_count = 0

# ETH on Arbitrum Sepolia
web3_eth = Web3(Web3.HTTPProvider("https://sepolia-rollup.arbitrum.io/rpc"))
if not web3_eth.is_connected():
    print("Failed to connect to Arbitrum Sepolia RPC")
else:
    print("Connected to Arbitrum Sepolia RPC")

# Cortensor token on Ethereum mainnet via PublicNode
web3_token = Web3(Web3.HTTPProvider("https://ethereum-rpc.publicnode.com"))
if not web3_token.is_connected():
    print("Failed to connect to Ethereum mainnet via publicnode")
else:
    print("Connected to Ethereum mainnet via publicnode")

# Minimal ERC20 ABI
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

# Cortensor token address
CORTENSOR_TOKEN_ADDRESS = Web3.to_checksum_address("0x8e0EeF788350f40255D86DFE8D91ec0AD3a4547F")
cortensor_token = web3_token.eth.contract(address=CORTENSOR_TOKEN_ADDRESS, abi=ERC20_ABI)

# Staking contract
STAKING_CONTRACT_ADDRESS = Web3.to_checksum_address("0x634DAEeCF243c844263D206e1DcF68F310e6BB19")
STAKING_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "shares",
        "outputs": [
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "uint256", "name": "stakedTime", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]
staking_contract = web3_token.eth.contract(address=STAKING_CONTRACT_ADDRESS, abi=STAKING_ABI)

def load_miners():
    try:
        with open("miners.json", "r") as f:
            data = json.load(f)
            if isinstance(data, list):  # Old format
                save_miners(data)
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
    return addr.startswith("0x") and len(addr) == 42 and web3_eth.is_address(addr)

def time_ago(timestamp):
    if not timestamp or timestamp == 0:
        return "Unknown"
    now = datetime.now()
    then = datetime.fromtimestamp(timestamp)
    delta = now - then
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
    batch_size = 10

    def get_balance(miner_id):
        global rpc_call_count
        try:
            if not is_valid_eth_address(miner_id):
                return
            addr = Web3.to_checksum_address(miner_id)

            # ETH balance
            eth_wei = web3_eth.eth.get_balance(addr)
            rpc_call_count += 1
            eth_balance = web3_eth.from_wei(eth_wei, 'ether')

            # Cortensor token balance
            token_balance = cortensor_token.functions.balanceOf(addr).call()
            rpc_call_count += 1
            decimals = cortensor_token.functions.decimals().call()
            rpc_call_count += 1
            cortensor_balance = token_balance / (10 ** decimals)

            # Staked amount and time
            staked_info = staking_contract.functions.shares(addr).call()
            rpc_call_count += 1
            staked_amount = staked_info[0] / 1e18
            staked_timestamp = staked_info[1]
            staked_time_str = datetime.utcfromtimestamp(staked_timestamp).strftime('%Y-%m-%d %H:%M:%S') if staked_timestamp > 0 else "N/A"
            staked_time_ago = time_ago(staked_timestamp)

            print(f"{addr} -> ETH: {round(eth_balance, 4)} | CORTENSOR: {round(cortensor_balance, 4)} | STAKED: {round(staked_amount, 4)} at {staked_time_str} ({staked_time_ago})")

            balances[addr] = {
                "eth": float(round(eth_balance, 4)),
                "cortensor": float(round(cortensor_balance, 4)),
                "staked": float(round(staked_amount, 4)),
                "staked_time": staked_time_str,
                "staked_time_ago": staked_time_ago
            }
        except Exception as e:
            print(f"Balance error for {miner_id}:", e)

    for i in range(0, len(miner_ids), batch_size):
        batch = miner_ids[i:i + batch_size]
        threads = []
        for m in batch:
            t = threading.Thread(target=get_balance, args=(m,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        if i + batch_size < len(miner_ids):
            time.sleep(1)

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
            "last_active": time_ago(last_active_ts),
            "last_active_timestamp": last_active_ts,
            "eth_balance": balances.get(full_id, {}).get("eth", 'N/A'),
            "cortensor_balance": balances.get(full_id, {}).get("cortensor", 'N/A'),
            "staked": balances.get(full_id, {}).get("staked", 'N/A'),
            "staked_time": balances.get(full_id, {}).get("staked_time", 'N/A'),
            "staked_time_ago": balances.get(full_id, {}).get("staked_time_ago", 'N/A')
        }

    stats["__rpc_meta__"] = {
        "rpc_call_count": rpc_call_count,
        "timestamp": int(datetime.now().timestamp())
    }

    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=4)

if __name__ == '__main__':
    collect_stats()
    print("Stats written to stats.json")
